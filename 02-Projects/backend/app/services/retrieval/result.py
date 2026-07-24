"""Retrieval orchestration result types."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    document_id: int
    document_filename: str
    chunk_index: int
    chunk_text: str
    score: float


@dataclass(frozen=True)
class SearchResult:
    query: str
    top_k: int
    results: list[SearchHit]
