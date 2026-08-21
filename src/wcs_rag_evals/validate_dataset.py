"""Validate source and golden-set contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from wcs_rag_evals.contracts import load_golden_set, load_source_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    source_manifest = load_source_manifest(PROJECT_ROOT / "corpus" / "sources.yaml")
    cases = load_golden_set(PROJECT_ROOT / "evals" / "datasets" / "golden-v0.1.jsonl")
    counts = {split: sum(case.split == split for case in cases) for split in ("dev", "test")}
    derived_path = PROJECT_ROOT / source_manifest.manifest_path
    corpus_status = "not fetched"
    if derived_path.exists():
        derived = json.loads(derived_path.read_text(encoding="utf-8"))
        documents = {item["document_id"]: item for item in derived["documents"]}
        labeled = {document for case in cases for document in case.relevant_documents}
        missing = sorted(labeled - documents.keys())
        if missing:
            raise ValueError(f"labeled documents missing from corpus: {missing}")
        malformed_hashes = sorted(
            document_id
            for document_id, item in documents.items()
            if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        )
        if malformed_hashes:
            raise ValueError(f"invalid document hashes: {malformed_hashes}")
        corpus_status = f"{derived['document_count']} collected documents"
    print(
        f"valid: {len(source_manifest.sources)} sources, {len(cases)} cases "
        f"(dev={counts['dev']}, test={counts['test']}), {corpus_status}"
    )


if __name__ == "__main__":
    main()
