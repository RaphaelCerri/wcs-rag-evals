"""Build the deterministic chunk collection consumed by the BM25 baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from wcs_rag_evals.chunking import chunk_document

INDEX_ID = "bm25-v0.1"
DEFAULT_MAX_WORDS = 220
DEFAULT_OVERLAP_WORDS = 40


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_index(
    manifest_path: Path,
    corpus_directory: Path,
    output_path: Path,
    max_words: int = DEFAULT_MAX_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = manifest["documents"]
    chunks = []

    for metadata in documents:
        document_path = corpus_directory / str(metadata["document_id"])
        if not document_path.is_file():
            raise FileNotFoundError(f"corpus document is missing: {document_path}")
        actual_hash = sha256_file(document_path)
        if actual_hash != metadata["sha256"]:
            raise ValueError(f"corpus document hash mismatch: {metadata['document_id']}")
        chunks.extend(
            chunk_document(
                metadata,
                document_path,
                max_words=max_words,
                overlap_words=overlap_words,
            )
        )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "index_id": INDEX_ID,
        "retriever": {"name": "bm25", "k1": 1.5, "b": 0.75},
        "chunking": {
            "strategy": "heading-aware-word-window",
            "max_words": max_words,
            "overlap_words": overlap_words,
        },
        "corpus": {
            "manifest_sha256": sha256_file(manifest_path),
            "document_count": len(documents),
            "sources": manifest["sources"],
        },
        "chunk_count": len(chunks),
        "chunks": [chunk.to_dict() for chunk in chunks],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(".data/corpus-manifest.json"))
    parser.add_argument("--corpus", type=Path, default=Path(".data/corpus"))
    parser.add_argument("--output", type=Path, default=Path(f".data/index/{INDEX_ID}.json"))
    parser.add_argument("--max-words", type=int, default=DEFAULT_MAX_WORDS)
    parser.add_argument("--overlap-words", type=int, default=DEFAULT_OVERLAP_WORDS)
    args = parser.parse_args()
    payload = build_index(
        args.manifest,
        args.corpus,
        args.output,
        args.max_words,
        args.overlap_words,
    )
    print(
        f"Built {payload['index_id']}: "
        f"{payload['corpus']['document_count']} documents, {payload['chunk_count']} chunks"
    )


if __name__ == "__main__":
    main()
