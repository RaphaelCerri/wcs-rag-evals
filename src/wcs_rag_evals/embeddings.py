"""Pinned multilingual embedding model used by the dense retrieval baseline."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "fd1525a9fd15316a2d503bf26ab031a61d056e98"
EMBEDDING_DIMENSIONS = 384


class E5Embedder:
    def __init__(self, model: Any | None = None, device: str = "cpu") -> None:
        if model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    'vector dependencies are missing; install with pip install -e ".[vector]"'
                ) from exc
            arguments = {
                "revision": MODEL_REVISION,
                "device": device,
                "trust_remote_code": False,
            }
            try:
                model = SentenceTransformer(MODEL_ID, local_files_only=True, **arguments)
            except OSError:
                model = SentenceTransformer(MODEL_ID, local_files_only=False, **arguments)
        self.model = model

    def encode_documents(
        self, texts: Sequence[str], batch_size: int = 32, show_progress: bool = True
    ) -> list[list[float]]:
        prefixed = [f"passage: {text}" for text in texts]
        embeddings = self.model.encode(
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=show_progress,
        )
        return embeddings.tolist()

    def encode_query(self, query: str) -> list[float]:
        return self.encode_queries([query])[0]

    def encode_queries(self, queries: Sequence[str], batch_size: int = 32) -> list[list[float]]:
        embeddings = self.model.encode(
            [f"query: {query}" for query in queries],
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()
