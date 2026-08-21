"""PostgreSQL and pgvector persistence for dense retrieval."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wcs_rag_evals.chunking import Chunk


@dataclass(frozen=True)
class DenseResult:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class DenseDocument:
    document_id: str
    score: float
    best_chunk_id: str


def vector_literal(values: list[float]) -> str:
    if not values:
        raise ValueError("vector cannot be empty")
    return "[" + ",".join(format(value, ".9g") for value in values) + "]"


def connect(database_url: str) -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            'vector dependencies are missing; install with pip install -e ".[vector]"'
        ) from exc
    return psycopg.connect(database_url, connect_timeout=10)


def initialize_schema(connection: Any, schema_path: Path) -> None:
    with connection.cursor() as cursor:
        cursor.execute(schema_path.read_text(encoding="utf-8"))
    connection.commit()


def replace_index(
    connection: Any,
    *,
    index_id: str,
    model_id: str,
    model_revision: str,
    dimensions: int,
    corpus_manifest_sha256: str,
    configuration: dict[str, object],
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("every chunk must have one embedding")
    if any(len(embedding) != dimensions for embedding in embeddings):
        raise ValueError(f"all embeddings must have {dimensions} dimensions")

    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute("DELETE FROM vector_indexes WHERE index_id = %s", (index_id,))
        cursor.execute(
            """
            INSERT INTO vector_indexes (
                index_id, model_id, model_revision, dimensions,
                corpus_manifest_sha256, chunk_count, configuration
            ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                index_id,
                model_id,
                model_revision,
                dimensions,
                corpus_manifest_sha256,
                len(chunks),
                json.dumps(configuration, sort_keys=True),
            ),
        )
        cursor.executemany(
            """
            INSERT INTO rag_chunks (
                index_id, chunk_id, document_id, source_id, source_path,
                authority, kind, heading, ordinal, content, embedding
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
            """,
            [
                (
                    index_id,
                    chunk.chunk_id,
                    chunk.document_id,
                    chunk.source_id,
                    chunk.source_path,
                    chunk.authority,
                    chunk.kind,
                    chunk.heading,
                    chunk.ordinal,
                    chunk.text,
                    vector_literal(embedding),
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ],
        )
        cursor.execute("ANALYZE rag_chunks")


def search_chunks(
    connection: Any, index_id: str, query_embedding: list[float], limit: int = 50
) -> list[DenseResult]:
    literal = vector_literal(query_embedding)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT chunk_id, document_id, source_id, source_path, authority,
                   kind, heading, ordinal, content,
                   1 - (embedding <=> %s::vector) AS score
            FROM rag_chunks
            WHERE index_id = %s
            ORDER BY embedding <=> %s::vector, chunk_id
            LIMIT %s
            """,
            (literal, index_id, literal, limit),
        )
        rows = cursor.fetchall()
    return [
        DenseResult(
            chunk=Chunk(
                chunk_id=row[0],
                document_id=row[1],
                source_id=row[2],
                source_path=row[3],
                authority=row[4],
                kind=row[5],
                heading=row[6],
                ordinal=row[7],
                text=row[8],
            ),
            score=float(row[9]),
        )
        for row in rows
    ]


def aggregate_documents(results: list[DenseResult], limit: int = 10) -> list[DenseDocument]:
    best: dict[str, DenseDocument] = {}
    for result in results:
        candidate = DenseDocument(
            document_id=result.chunk.document_id,
            score=result.score,
            best_chunk_id=result.chunk.chunk_id,
        )
        current = best.get(candidate.document_id)
        if current is None or candidate.score > current.score:
            best[candidate.document_id] = candidate
    return sorted(best.values(), key=lambda item: (-item.score, item.document_id))[:limit]
