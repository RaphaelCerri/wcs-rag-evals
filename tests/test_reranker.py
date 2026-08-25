from typing import Any

import pytest

from wcs_rag_evals.evaluate_reranker import build_candidates, nearest_rank_percentile
from wcs_rag_evals.reranker import MultilingualReranker, RerankCandidate, rerank


class FakeScores(list[float]):
    def tolist(self) -> list[float]:
        return list(self)


class FakeCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.calls: list[tuple[list[tuple[str, str]], dict[str, Any]]] = []

    def predict(self, pairs: list[tuple[str, str]], **kwargs: Any) -> FakeScores:
        self.calls.append((pairs, kwargs))
        return FakeScores(self.scores)


def test_reranker_uses_the_best_passage_for_each_document() -> None:
    fake = FakeCrossEncoder([0.2, 0.9, 0.8])
    model = MultilingualReranker(model=fake)
    candidates = [
        RerankCandidate(
            document_id="a.md",
            original_rank=1,
            passages=(("a::1", "weak"), ("a::2", "strong")),
        ),
        RerankCandidate(
            document_id="b.md",
            original_rank=2,
            passages=(("b::1", "medium"),),
        ),
    ]

    results = rerank("query", candidates, model)

    assert [result.document_id for result in results] == ["a.md", "b.md"]
    assert results[0].best_chunk_id == "a::2"
    assert fake.calls[0][0] == [
        ("query", "weak"),
        ("query", "strong"),
        ("query", "medium"),
    ]


def test_original_rank_breaks_equal_score_ties() -> None:
    model = MultilingualReranker(model=FakeCrossEncoder([0.5, 0.5]))
    candidates = [
        RerankCandidate("first.md", 1, (("first::1", "one"),)),
        RerankCandidate("second.md", 2, (("second::1", "two"),)),
    ]

    results = rerank("query", candidates, model)

    assert [result.document_id for result in results] == ["first.md", "second.md"]


def test_build_candidates_deduplicates_source_chunks() -> None:
    hybrid = {"retrieved_documents": [{"rank": 1, "document_id": "a.md"}]}
    bm25 = {"retrieved_documents": [{"rank": 1, "document_id": "a.md", "best_chunk_id": "a::1"}]}
    dense = {"retrieved_documents": [{"rank": 2, "document_id": "a.md", "best_chunk_id": "a::1"}]}

    candidates = build_candidates(hybrid, bm25, dense, {"a::1": "passage"})

    assert candidates == [RerankCandidate("a.md", 1, (("a::1", "passage"),))]


def test_nearest_rank_percentile() -> None:
    assert nearest_rank_percentile([10.0, 40.0, 20.0, 30.0], 0.95) == 40.0
    assert nearest_rank_percentile([10.0, 20.0], 0.5) == 10.0


def test_reranker_rejects_candidate_without_passage() -> None:
    model = MultilingualReranker(model=FakeCrossEncoder([]))

    with pytest.raises(ValueError, match="at least one passage"):
        rerank("query", [RerankCandidate("a.md", 1, ())], model)
