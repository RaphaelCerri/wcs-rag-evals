import pytest

from wcs_rag_evals.rrf import reciprocal_rank_fusion


def test_rrf_rewards_documents_supported_by_both_retrievers() -> None:
    fused = reciprocal_rank_fusion(
        {
            "bm25": ["lexical-only", "shared"],
            "dense": ["dense-only", "shared"],
        },
        rank_constant=60,
    )

    assert fused[0].document_id == "shared"
    assert fused[0].ranks == {"bm25": 2, "dense": 2}
    assert fused[0].score == pytest.approx(2 / 62)


def test_rrf_weights_can_prioritize_one_retriever() -> None:
    fused = reciprocal_rank_fusion(
        {"bm25": ["lexical"], "dense": ["semantic"]},
        weights={"bm25": 1.0, "dense": 2.0},
        rank_constant=10,
    )

    assert [item.document_id for item in fused] == ["semantic", "lexical"]


@pytest.mark.parametrize(
    ("rankings", "weights", "rank_constant", "limit", "message"),
    [
        ({"bm25": ["a"]}, {"dense": 1.0}, 60, 10, "weights must match"),
        ({"bm25": ["a"]}, {"bm25": 0.0}, 60, 10, "weights must be positive"),
        ({"bm25": ["a"]}, None, -1, 10, "rank_constant"),
        ({"bm25": ["a"]}, None, 60, 0, "limit"),
    ],
)
def test_rrf_rejects_invalid_configuration(
    rankings: dict[str, list[str]],
    weights: dict[str, float] | None,
    rank_constant: int,
    limit: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        reciprocal_rank_fusion(
            rankings,
            weights=weights,
            rank_constant=rank_constant,
            limit=limit,
        )
