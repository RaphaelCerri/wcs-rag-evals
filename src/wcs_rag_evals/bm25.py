"""Small, dependency-free BM25 implementation used as the lexical baseline."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from wcs_rag_evals.chunking import Chunk

TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_PATTERN.finditer(text)]


@dataclass(frozen=True)
class RankedChunk:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class RankedDocument:
    document_id: str
    score: float
    best_chunk_id: str


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        if not chunks:
            raise ValueError("BM25 requires at least one chunk")
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokenize(chunk.text)) for chunk in chunks]
        self.lengths = [sum(frequencies.values()) for frequencies in self.term_frequencies]
        self.average_length = sum(self.lengths) / len(self.lengths)

        document_frequency: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            document_frequency.update(frequencies.keys())
        size = len(chunks)
        self.idf = {
            term: math.log(1 + (size - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search_chunks(self, query: str, limit: int = 10) -> list[RankedChunk]:
        query_terms = tokenize(query)
        ranked: list[RankedChunk] = []
        for chunk, frequencies, length in zip(
            self.chunks, self.term_frequencies, self.lengths, strict=True
        ):
            score = 0.0
            normalization = self.k1 * (1 - self.b + self.b * length / self.average_length)
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if frequency:
                    score += self.idf.get(term, 0.0) * (
                        frequency * (self.k1 + 1) / (frequency + normalization)
                    )
            if score > 0:
                ranked.append(RankedChunk(chunk=chunk, score=score))
        ranked.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
        return ranked[:limit]

    def search_documents(self, query: str, limit: int = 10) -> list[RankedDocument]:
        best: dict[str, RankedDocument] = {}
        for result in self.search_chunks(query, limit=len(self.chunks)):
            candidate = RankedDocument(
                document_id=result.chunk.document_id,
                score=result.score,
                best_chunk_id=result.chunk.chunk_id,
            )
            current = best.get(candidate.document_id)
            if current is None or candidate.score > current.score:
                best[candidate.document_id] = candidate
        return sorted(best.values(), key=lambda item: (-item.score, item.document_id))[:limit]
