"""Embed the fixed chunk collection and persist it in PostgreSQL with pgvector."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from wcs_rag_evals.chunking import Chunk
from wcs_rag_evals.embeddings import (
    EMBEDDING_DIMENSIONS,
    MODEL_ID,
    MODEL_REVISION,
    E5Embedder,
)
from wcs_rag_evals.vector_store import connect, initialize_schema, replace_index

INDEX_ID = "dense-e5-small-v0.1"


def require_database_url() -> str:
    database_url = os.environ.get("WCS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("WCS_DATABASE_URL is required; copy the value from .env.example")
    return database_url


def embed_with_resumable_cache(
    chunks: list[Chunk],
    embedder: E5Embedder,
    cache_path: Path,
    batch_size: int,
) -> list[list[float]]:
    cached: dict[str, list[float]] = {}
    if cache_path.is_file():
        for line_number, line in enumerate(
            cache_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                cached[str(record["chunk_id"])] = record["embedding"]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError(f"invalid embedding cache line {line_number}") from exc

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    missing = [chunk for chunk in chunks if chunk.chunk_id not in cached]
    with cache_path.open("a", encoding="utf-8") as cache:
        for start in range(0, len(missing), batch_size):
            batch = missing[start : start + batch_size]
            vectors = embedder.encode_documents(
                [chunk.text for chunk in batch],
                batch_size=batch_size,
                show_progress=False,
            )
            for chunk, vector in zip(batch, vectors, strict=True):
                cached[chunk.chunk_id] = vector
                cache.write(
                    json.dumps(
                        {"chunk_id": chunk.chunk_id, "embedding": vector},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            cache.flush()
            completed = min(start + len(batch), len(missing))
            print(f"Embedded {completed}/{len(missing)} missing chunks")
    return [cached[chunk.chunk_id] for chunk in chunks]


def build_vector_index(
    lexical_index_path: Path,
    schema_path: Path,
    database_url: str,
    cache_path: Path,
    batch_size: int = 32,
) -> dict[str, object]:
    raw_index = json.loads(lexical_index_path.read_text(encoding="utf-8"))
    chunks = [Chunk(**raw) for raw in raw_index["chunks"]]
    embedder = E5Embedder()
    embeddings = embed_with_resumable_cache(
        chunks,
        embedder,
        cache_path,
        batch_size,
    )
    configuration: dict[str, object] = {
        "distance": "cosine",
        "search_mode": "exact",
        "ann_index_available": "HNSW",
        "document_aggregation": "maximum_chunk_score",
        "document_candidate_chunks": 100,
        "query_prefix": "query: ",
        "document_prefix": "passage: ",
        "normalized_embeddings": True,
    }
    with connect(database_url) as connection:
        initialize_schema(connection, schema_path)
        replace_index(
            connection,
            index_id=INDEX_ID,
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            dimensions=EMBEDDING_DIMENSIONS,
            corpus_manifest_sha256=raw_index["corpus"]["manifest_sha256"],
            configuration=configuration,
            chunks=chunks,
            embeddings=embeddings,
        )
    return {
        "index_id": INDEX_ID,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": EMBEDDING_DIMENSIONS,
        "chunk_count": len(chunks),
        "configuration": configuration,
        "corpus": raw_index["corpus"],
        "chunking": raw_index["chunking"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path(".data/index/bm25-v0.1.json"))
    parser.add_argument("--schema", type=Path, default=Path("infra/postgres/init.sql"))
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".data/index/dense-e5-small-v0.1.jsonl"),
    )
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    metadata = build_vector_index(
        args.index,
        args.schema,
        require_database_url(),
        args.cache,
        args.batch_size,
    )
    print(
        f"Built {metadata['index_id']}: {metadata['chunk_count']} chunks, "
        f"{metadata['dimensions']} dimensions"
    )


if __name__ == "__main__":
    main()
