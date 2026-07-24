from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = Field(default=32, ge=1)

    vector_store_provider: str = "faiss"
    faiss_index_path: str = "data/faiss/chunk_index.faiss"

    indexing_stale_timeout_seconds: int = Field(default=300, ge=30)

    search_default_top_k: int = Field(default=10, ge=1)
    search_max_top_k: int = Field(default=50, ge=1)
    search_over_fetch_multiplier: int = Field(default=5, ge=1)
    search_over_fetch_min_buffer: int = Field(default=20, ge=0)
    search_max_fetch_k: int = Field(default=200, ge=1)
    search_max_query_length: int = Field(default=4000, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("embedding_provider")
    @classmethod
    def normalize_embedding_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("vector_store_provider")
    @classmethod
    def normalize_vector_store_provider(cls, value: str) -> str:
        return value.strip().lower()


settings = Settings()