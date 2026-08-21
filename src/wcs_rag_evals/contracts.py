"""Typed contracts for corpus sources and evaluation cases."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, HttpUrl, model_validator

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class CorpusSource(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    repository: HttpUrl
    revision: str
    license: str
    license_url: HttpUrl
    authority: Literal["source_of_truth", "explanatory"]
    include: list[str] = Field(min_length=1)
    exclude: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def revision_must_be_immutable(self) -> CorpusSource:
        if not SHA_PATTERN.fullmatch(self.revision):
            raise ValueError("revision must be a full 40-character lowercase Git SHA")
        return self


class SourceManifest(BaseModel):
    schema_version: Literal["1.0"]
    output_directory: str
    manifest_path: str
    max_file_bytes: int = Field(gt=0, le=10 * 1024 * 1024)
    allowed_extensions: list[str] = Field(min_length=1)
    sources: list[CorpusSource] = Field(min_length=1)

    @model_validator(mode="after")
    def source_ids_must_be_unique(self) -> SourceManifest:
        ids = [source.id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("source IDs must be unique")
        return self


class GoldenCase(BaseModel):
    id: str = Field(pattern=r"^wcs-(dev|test)-[0-9]{3}$")
    split: Literal["dev", "test"]
    category: Literal[
        "architecture",
        "inventory",
        "outbound",
        "slotting",
        "equipment",
        "security",
        "reliability",
        "integration",
        "process",
        "unanswerable",
    ]
    difficulty: Literal["basic", "intermediate", "advanced", "adversarial"]
    language: Literal["en", "pt-BR"]
    answerable: bool
    question: str = Field(min_length=15)
    relevant_documents: list[str] = Field(default_factory=list)
    reference_answer: str = Field(min_length=10)
    required_facts: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def evidence_matches_answerability(self) -> GoldenCase:
        if self.answerable and not self.relevant_documents:
            raise ValueError("answerable cases require at least one relevant document")
        if self.answerable and not self.required_facts:
            raise ValueError("answerable cases require at least one required fact")
        if not self.answerable and self.relevant_documents:
            raise ValueError("unanswerable cases cannot label a relevant document")
        return self


def load_source_manifest(path: Path) -> SourceManifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SourceManifest.model_validate(raw)


def load_golden_set(path: Path) -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(GoldenCase.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid golden-set line {line_number}: {exc}") from exc

    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("golden-set IDs must be unique")
    return cases
