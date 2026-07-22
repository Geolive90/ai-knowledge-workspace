"""Vector store provider interface and value types."""

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class VectorAddItem:
    chunk_id: int
    vector: list[float]


@dataclass(frozen=True)
class VectorSearchResult:
    chunk_id: int
    score: float


class VectorStore(Protocol):
    @property
    def dimensions(self) -> int:
        """Expected vector length for add and search operations."""
        ...

    @property
    def count(self) -> int:
        """Number of vectors currently indexed."""
        ...

    def add(self, items: Sequence[VectorAddItem]) -> None:
        """Add vectors keyed by chunk_id. Rejects duplicate chunk_id values."""
        ...

    def search(self, query_vector: list[float], k: int) -> list[VectorSearchResult]:
        """
        Return up to k nearest neighbors ordered best-first.

        score is inner product of L2-normalized vectors (cosine similarity).
        Higher score means more similar. Empty index returns [].
        """
        ...

    def remove_by_chunk_ids(self, chunk_ids: Sequence[int]) -> int:
        """Remove vectors by chunk_id. Returns count removed; missing IDs are ignored."""
        ...

    def clear(self) -> None:
        """Remove all vectors from the index."""
        ...

    def save(self) -> None:
        """Persist the index to disk."""
        ...

    def load(self) -> None:
        """Load the index from disk. Missing file starts empty; corrupt file raises."""
        ...
