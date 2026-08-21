import pytest

from wcs_rag_evals.chunking import Chunk
from wcs_rag_evals.vector_store import DenseResult, aggregate_documents, vector_literal


def make_result(document_id: str, chunk_id: str, score: float) -> DenseResult:
    return DenseResult(
        chunk=Chunk(
            chunk_id=chunk_id,
            document_id=document_id,
            source_id="source",
            source_path=document_id,
            authority="source_of_truth",
            kind="markdown",
            heading="Heading",
            ordinal=0,
            text="content",
        ),
        score=score,
    )


def test_vector_literal_is_stable_and_rejects_empty_vectors() -> None:
    assert vector_literal([1.0, 0.125, -0.0]) == "[1,0.125,-0]"
    with pytest.raises(ValueError, match="vector cannot be empty"):
        vector_literal([])


def test_dense_results_are_aggregated_by_best_chunk() -> None:
    results = [
        make_result("inventory.md", "inventory::1", 0.7),
        make_result("inventory.md", "inventory::2", 0.9),
        make_result("security.md", "security::1", 0.8),
    ]

    documents = aggregate_documents(results)

    assert [document.document_id for document in documents] == [
        "inventory.md",
        "security.md",
    ]
    assert documents[0].best_chunk_id == "inventory::2"
