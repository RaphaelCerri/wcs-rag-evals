from pathlib import Path
from typing import Any

from wcs_rag_evals.build_vector_index import embed_with_resumable_cache
from wcs_rag_evals.chunking import Chunk
from wcs_rag_evals.embeddings import E5Embedder


class FakeRow(list[float]):
    def tolist(self) -> list[float]:
        return list(self)


class FakeMatrix(list[FakeRow]):
    def tolist(self) -> list[list[float]]:
        return [row.tolist() for row in self]


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def encode(self, texts: list[str], **kwargs: Any) -> FakeMatrix:
        self.calls.append((texts, kwargs))
        return FakeMatrix(FakeRow([1.0, 0.0]) for _ in texts)


def test_e5_uses_required_asymmetric_prefixes_and_normalization() -> None:
    model = FakeModel()
    embedder = E5Embedder(model=model)

    assert embedder.encode_documents(["stock projection"], show_progress=False) == [[1.0, 0.0]]
    assert embedder.encode_query("estoque atual") == [1.0, 0.0]

    assert model.calls[0][0] == ["passage: stock projection"]
    assert model.calls[1][0] == ["query: estoque atual"]
    assert all(call[1]["normalize_embeddings"] for call in model.calls)


def test_embedding_cache_resumes_without_encoding_completed_chunks(tmp_path: Path) -> None:
    chunk = Chunk(
        chunk_id="doc::1",
        document_id="doc",
        source_id="source",
        source_path="doc.md",
        authority="source_of_truth",
        kind="markdown",
        heading="Heading",
        ordinal=0,
        text="stock projection",
    )
    model = FakeModel()
    embedder = E5Embedder(model=model)
    cache_path = tmp_path / "embeddings.jsonl"

    first = embed_with_resumable_cache([chunk], embedder, cache_path, batch_size=1)
    second = embed_with_resumable_cache([chunk], embedder, cache_path, batch_size=1)

    assert first == second == [[1.0, 0.0]]
    assert len(model.calls) == 1
