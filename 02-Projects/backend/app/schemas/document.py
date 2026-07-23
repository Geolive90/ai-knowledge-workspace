from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    uploaded_at: datetime
    indexing_status: str
    indexed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IndexingRetryInfo(BaseModel):
    method: str
    path: str


class IndexingOutcomeResponse(BaseModel):
    indexing_status: str
    chunk_count: int
    vectors_indexed: int
    indexed_at: Optional[datetime] = None
    indexing_error: Optional[str] = None
    retry: Optional[IndexingRetryInfo] = None