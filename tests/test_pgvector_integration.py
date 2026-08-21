import os

import pytest

from wcs_rag_evals.build_vector_index import INDEX_ID
from wcs_rag_evals.embeddings import MODEL_REVISION

DATABASE_URL = os.environ.get("WCS_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="pgvector integration database not set")


def test_real_pgvector_index_contains_the_fixed_chunk_collection() -> None:
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as connection:
        extension_version = connection.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        index_metadata = connection.execute(
            """
            SELECT model_revision, dimensions, chunk_count
            FROM vector_indexes WHERE index_id = %s
            """,
            (INDEX_ID,),
        ).fetchone()
        stored_chunks = connection.execute(
            "SELECT count(*) FROM rag_chunks WHERE index_id = %s", (INDEX_ID,)
        ).fetchone()
        hnsw_index = connection.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'rag_chunks' AND indexdef LIKE '%USING hnsw%'
            """
        ).fetchone()

    assert extension_version == ("0.8.6",)
    assert index_metadata == (MODEL_REVISION, 384, 1458)
    assert stored_chunks == (1458,)
    assert hnsw_index == ("rag_chunks_embedding_hnsw_idx",)
