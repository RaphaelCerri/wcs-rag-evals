"""Pinned multilingual cross-encoder and deterministic document reranking."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

MODEL_ID = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
MODEL_REVISION = "1427fd652930e4ba29e8149678df786c240d8825"


@dataclass(frozen=True)
class RerankCandidate:
    document_id: str
    original_rank: int
    passages: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class RerankedDocument:
    document_id: str
    score: float
    original_rank: int
    best_chunk_id: str


class MultilingualReranker:
    def __init__(self, model: Any | None = None, device: str = "cpu") -> None:
        if model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    'reranker dependencies are missing; install with pip install -e ".[vector]"'
                ) from exc
            arguments = {
                "revision": MODEL_REVISION,
                "device": device,
                "trust_remote_code": False,
            }
            try:
                model = CrossEncoder(MODEL_ID, local_files_only=True, **arguments)
            except OSError:
                model = CrossEncoder(MODEL_ID, local_files_only=False, **arguments)
        self.model = model

    def score(self, pairs: Sequence[tuple[str, str]], batch_size: int = 16) -> list[float]:
        scores = self.model.predict(
            list(pairs),
            batch_size=batch_size,
            show_progress_bar=False,
        )
        values = scores.tolist() if hasattr(scores, "tolist") else list(scores)
        return [float(value) for value in values]


def rerank(
    query: str,
    candidates: list[RerankCandidate],
    model: MultilingualReranker,
    batch_size: int = 16,
) -> list[RerankedDocument]:
    if not candidates:
        return []
    if any(not candidate.passages for candidate in candidates):
        raise ValueError("every rerank candidate must contain at least one passage")

    pairs: list[tuple[str, str]] = []
    owners: list[tuple[str, str]] = []
    for candidate in candidates:
        for chunk_id, passage in candidate.passages:
            pairs.append((query, passage))
            owners.append((candidate.document_id, chunk_id))

    scores = model.score(pairs, batch_size=batch_size)
    best: dict[str, tuple[float, str]] = {}
    for (document_id, chunk_id), score in zip(owners, scores, strict=True):
        current = best.get(document_id)
        if current is None or score > current[0] or (score == current[0] and chunk_id < current[1]):
            best[document_id] = (score, chunk_id)

    reranked = [
        RerankedDocument(
            document_id=candidate.document_id,
            score=best[candidate.document_id][0],
            original_rank=candidate.original_rank,
            best_chunk_id=best[candidate.document_id][1],
        )
        for candidate in candidates
    ]
    reranked.sort(key=lambda item: (-item.score, item.original_rank, item.document_id))
    return reranked
