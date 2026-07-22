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