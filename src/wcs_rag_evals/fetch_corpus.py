"""Fetch an allowlisted, revision-pinned corpus with deterministic provenance."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from wcs_rag_evals.contracts import CorpusSource, SourceManifest, load_source_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _inside_project(relative_path: str) -> Path:
    candidate = (PROJECT_ROOT / relative_path).resolve()
    if candidate != PROJECT_ROOT and PROJECT_ROOT not in candidate.parents:
        raise ValueError(f"path escapes project root: {relative_path}")
    return candidate


def _run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _checkout(source: CorpusSource, destination: Path) -> None:
    _run("git", "init", "--quiet", str(destination))
    _run("git", "remote", "add", "origin", str(source.repository), cwd=destination)
    _run("git", "fetch", "--quiet", "--depth", "1", "origin", source.revision, cwd=destination)
    _run("git", "checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=destination)


def _collect_source(
    source: CorpusSource,
    config: SourceManifest,
    checkout: Path,
    output_root: Path,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    destination_root = output_root / source.id

    for path in sorted(checkout.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(checkout).as_posix()
        if not _matches(relative, source.include) or _matches(relative, source.exclude):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed in corpus: {source.id}/{relative}")
        if path.suffix.lower() not in config.allowed_extensions:
            raise ValueError(f"extension is not allowed: {source.id}/{relative}")

        content = path.read_bytes()
        if len(content) > config.max_file_bytes:
            raise ValueError(f"file exceeds max_file_bytes: {source.id}/{relative}")

        target = destination_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        collected.append(
            {
                "document_id": f"{source.id}/{relative}",
                "source_id": source.id,
                "source_path": relative,
                "revision": source.revision,
                "authority": source.authority,
                "license": source.license,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    if not collected:
        raise ValueError(f"allowlist selected zero files for source {source.id}")
    return collected


def fetch(manifest_file: Path, force: bool = False) -> dict[str, object]:
    config = load_source_manifest(manifest_file)
    output_root = _inside_project(config.output_directory)
    derived_manifest_path = _inside_project(config.manifest_path)

    if output_root.exists():
        if not force:
            raise FileExistsError(f"{output_root} exists; rerun with --force to rebuild it")
        if output_root.name != "corpus" or output_root.parent.name != ".data":
            raise ValueError("refusing to replace a directory outside .data/corpus")
        shutil.rmtree(output_root)

    documents: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="wcs-rag-corpus-") as temp:
        temp_root = Path(temp)
        for source in config.sources:
            checkout = temp_root / source.id
            checkout.mkdir()
            _checkout(source, checkout)
            documents.extend(_collect_source(source, config, checkout, output_root))

    result: dict[str, object] = {
        "schema_version": config.schema_version,
        "sources": [
            {
                "id": source.id,
                "repository": str(source.repository),
                "revision": source.revision,
                "license": source.license,
                "authority": source.authority,
            }
            for source in config.sources
        ],
        "document_count": len(documents),
        "documents": documents,
    }
    derived_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    derived_manifest_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "corpus" / "sources.yaml",
    )
    parser.add_argument("--force", action="store_true", help="replace .data/corpus safely")
    args = parser.parse_args()
    result = fetch(args.manifest.resolve(), force=args.force)
    print(f"collected {result['document_count']} documents")


if __name__ == "__main__":
    main()
