"""Weighted Reciprocal Rank Fusion for deterministic document rankings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FusedDocument:
    document_id: str
    score: float
    ranks: dict[str, int]
    contributions: dict[str, float]


def reciprocal_rank_fusion(
    rankings: dict[str, list[str]],
    *,
    weights: dict[str, float] | None = None,
    rank_constant: int = 60,
    limit: int = 10,
) -> list[FusedDocument]:
    if rank_constant < 0:
        raise ValueError("rank_constant must be non-negative")
    if limit <= 0:
        raise ValueError("limit must be positive")
    if not rankings:
        return []

    resolved_weights = weights or {name: 1.0 for name in rankings}
    if set(resolved_weights) != set(rankings):
        raise ValueError("weights must match ranking names")
    if any(weight <= 0 for weight in resolved_weights.values()):
        raise ValueError("weights must be positive")

    ranks: dict[str, dict[str, int]] = {}
    contributions: dict[str, dict[str, float]] = {}
    for name, documents in rankings.items():
        seen: set[str] = set()
        for rank, document_id in enumerate(documents, start=1):
            if document_id in seen:
                continue
            seen.add(document_id)
            ranks.setdefault(document_id, {})[name] = rank
            contributions.setdefault(document_id, {})[name] = resolved_weights[name] / (
                rank_constant + rank
            )

    fused = [
        FusedDocument(
            document_id=document_id,
            score=sum(contributions[document_id].values()),
            ranks=ranks[document_id],
            contributions=contributions[document_id],
        )
        for document_id in ranks
    ]
    fused.sort(key=lambda item: (-item.score, item.document_id))
    return fused[:limit]
