from wcs_rag_evals.bm25 import BM25Index, tokenize
from wcs_rag_evals.chunking import Chunk


def make_chunk(document_id: str, text: str, ordinal: int = 0) -> Chunk:
    return Chunk(
        chunk_id=f"{document_id}::{ordinal}",
        document_id=document_id,
        source_id="source",
        source_path=document_id,
        authority="source_of_truth",
        kind="markdown",
        heading="Heading",
        ordinal=ordinal,
        text=text,
    )


def test_tokenizer_is_case_insensitive_and_unicode_aware() -> None:
    assert tokenize("Orquestração WCS, INVENTORY") == ["orquestração", "wcs", "inventory"]


def test_bm25_ranks_and_aggregates_by_best_document_chunk() -> None:
    chunks = [
        make_chunk("inventory.md", "inventory stock projection"),
        make_chunk("inventory.md", "warehouse inventory ledger", ordinal=1),
        make_chunk("security.md", "jwt security gateway"),
    ]

    results = BM25Index(chunks).search_documents("inventory stock", limit=2)

    assert [result.document_id for result in results] == ["inventory.md"]
    assert results[0].best_chunk_id == "inventory.md::0"


def test_bm25_uses_document_id_as_deterministic_tie_breaker() -> None:
    chunks = [make_chunk("b.md", "shared term"), make_chunk("a.md", "shared term")]

    results = BM25Index(chunks).search_documents("shared")

    assert [result.document_id for result in results] == ["a.md", "b.md"]
