"""Deterministic, heading-aware chunking for Markdown and OpenAPI documents."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    source_id: str
    source_path: str
    authority: str
    kind: str
    heading: str
    ordinal: int
    text: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _chunk_id(document_id: str, ordinal: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"{document_id}::{ordinal:04d}::{digest}"


def _windows(text: str, max_words: int, overlap_words: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if max_words <= 0 or overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("chunk window requires max_words > overlap_words >= 0")

    windows: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        windows.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_words
    return windows


def chunk_markdown(
    document_id: str,
    source_id: str,
    source_path: str,
    authority: str,
    text: str,
    max_words: int = 220,
    overlap_words: int = 40,
) -> list[Chunk]:
    heading_stack: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_lines: list[str] = []
    current_heading = Path(source_path).stem.replace("-", " ")

    def flush() -> None:
        nonlocal current_lines
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_heading, [body]))
        current_lines = []

    for line in text.splitlines():
        match = HEADING_PATTERN.match(line)
        if not match:
            current_lines.append(line)
            continue
        flush()
        level = len(match.group(1))
        title = match.group(2).strip()
        heading_stack = heading_stack[: level - 1]
        heading_stack.append(title)
        current_heading = " > ".join(heading_stack)
    flush()

    chunks: list[Chunk] = []
    ordinal = 0
    for heading, bodies in sections:
        for body in bodies:
            for window in _windows(body, max_words, overlap_words):
                content = f"{heading}\n{window}".strip()
                chunks.append(
                    Chunk(
                        chunk_id=_chunk_id(document_id, ordinal, content),
                        document_id=document_id,
                        source_id=source_id,
                        source_path=source_path,
                        authority=authority,
                        kind="markdown",
                        heading=heading,
                        ordinal=ordinal,
                        text=content,
                    )
                )
                ordinal += 1
    return chunks


def _operation_text(method: str, path: str, operation: dict[str, Any]) -> str:
    selected = {
        key: operation[key]
        for key in (
            "summary",
            "description",
            "operationId",
            "tags",
            "parameters",
            "requestBody",
            "responses",
        )
        if key in operation
    }
    return f"{method.upper()} {path}\n" + yaml.safe_dump(
        selected, allow_unicode=True, sort_keys=True
    )


def chunk_openapi(
    document_id: str,
    source_id: str,
    source_path: str,
    authority: str,
    text: str,
    max_words: int = 220,
    overlap_words: int = 40,
) -> list[Chunk]:
    document = yaml.safe_load(text)
    if not isinstance(document, dict):
        raise ValueError(f"OpenAPI document must be a mapping: {document_id}")

    units: list[tuple[str, str]] = []
    info = document.get("info", {})
    if isinstance(info, dict):
        units.append(
            (
                "API information",
                yaml.safe_dump(info, allow_unicode=True, sort_keys=True),
            )
        )

    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        raise ValueError(f"OpenAPI paths must be a mapping: {document_id}")
    for path, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        for method, operation in sorted(path_item.items()):
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            units.append((f"{method.upper()} {path}", _operation_text(method, path, operation)))

    components = document.get("components", {})
    if isinstance(components, dict):
        for component_type, definitions in sorted(components.items()):
            if not isinstance(definitions, dict):
                continue
            for name, definition in sorted(definitions.items()):
                units.append(
                    (
                        f"components > {component_type} > {name}",
                        yaml.safe_dump(definition, allow_unicode=True, sort_keys=True),
                    )
                )

    chunks: list[Chunk] = []
    ordinal = 0
    for heading, body in units:
        for window in _windows(body, max_words, overlap_words):
            content = f"{heading}\n{window}".strip()
            chunks.append(
                Chunk(
                    chunk_id=_chunk_id(document_id, ordinal, content),
                    document_id=document_id,
                    source_id=source_id,
                    source_path=source_path,
                    authority=authority,
                    kind="openapi",
                    heading=heading,
                    ordinal=ordinal,
                    text=content,
                )
            )
            ordinal += 1
    return chunks


def chunk_document(
    metadata: dict[str, object],
    path: Path,
    max_words: int = 220,
    overlap_words: int = 40,
) -> list[Chunk]:
    values = {
        "document_id": str(metadata["document_id"]),
        "source_id": str(metadata["source_id"]),
        "source_path": str(metadata["source_path"]),
        "authority": str(metadata["authority"]),
        "text": path.read_text(encoding="utf-8"),
        "max_words": max_words,
        "overlap_words": overlap_words,
    }
    if path.suffix.lower() in {".yaml", ".yml"}:
        return chunk_openapi(**values)
    return chunk_markdown(**values)
