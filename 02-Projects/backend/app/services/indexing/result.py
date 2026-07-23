"""Indexing orchestration result types."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IndexingResult:
    document_id: int
    indexing_status: str
    chunk_count: int
    vectors_indexed: int
    indexed_at: datetime | None
    indexing_error: str | None
    skipped: bool


@dataclass(frozen=True)
class PurgeResult:
    chunk_ids_considered: int
    vectors_removed: int
    metadata_rows_deleted: int
