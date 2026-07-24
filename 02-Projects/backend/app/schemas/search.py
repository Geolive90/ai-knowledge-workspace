from pydantic import BaseModel, Field, field_validator

from app.config import settings


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = Field(default=None, ge=1)
    document_id: int | None = Field(default=None, gt=0)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(
                "Search query must not be empty or whitespace-only."
            )
        if len(normalized) > settings.search_max_query_length:
            raise ValueError(
                "Search query must not exceed "
                f"{settings.search_max_query_length} characters."
            )
        return normalized


class SearchHitResponse(BaseModel):
    chunk_id: int
    document_id: int
    document_filename: str
    chunk_index: int
    chunk_text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SearchHitResponse]
