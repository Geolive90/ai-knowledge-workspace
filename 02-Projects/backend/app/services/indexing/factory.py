"""Indexing service factory."""

from functools import lru_cache

from app.config import Settings, settings
from app.services.embedding.factory import get_embedding_service
from app.services.embedding.service import EmbeddingService
from app.services.indexing.service import IndexingService
from app.services.vector_store.factory import get_vector_store
from app.services.vector_store.provider import VectorStore


def create_indexing_service(
    app_settings: Settings | None = None,
    *,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
    stale_timeout_seconds: int | None = None,
) -> IndexingService:
    resolved_settings = app_settings or settings
    return IndexingService(
        embedding_service=embedding_service or get_embedding_service(),
        vector_store=vector_store or get_vector_store(),
        stale_timeout_seconds=(
            stale_timeout_seconds
            if stale_timeout_seconds is not None
            else resolved_settings.indexing_stale_timeout_seconds
        ),
    )


@lru_cache(maxsize=1)
def get_indexing_service() -> IndexingService:
    return create_indexing_service(settings)


def clear_indexing_caches() -> None:
    """Clear cached indexing service singleton (for tests)."""
    get_indexing_service.cache_clear()
