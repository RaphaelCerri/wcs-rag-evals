import pytest

from wcs_rag_evals.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


def test_binary_relevance_metrics() -> None:
    retrieved = ["irrelevant", "relevant-a", "relevant-b"]
    relevant = {"relevant-a", "relevant-b"}

    assert recall_at_k(retrieved, relevant, 2) == 0.5
    assert precision_at_k(retrieved, relevant, 2) == 0.5
    assert reciprocal_rank(retrieved, relevant) == 0.5
    assert ndcg_at_k(retrieved, relevant, 3) == pytest.approx(0.693426, abs=1e-6)


def test_precision_rejects_non_positive_k() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        precision_at_k([], set(), 0)
