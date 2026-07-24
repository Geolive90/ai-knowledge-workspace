"""Retrieval service factory."""

from functools import lru_cache

from app.config import Settings, settings
from app.services.embedding.factory import get_embedding_service
from app.services.embedding.service import EmbeddingService
from app.services.retrieval.service import RetrievalService
from app.services.vector_store.factory import get_vector_store
from app.services.vector_store.provider import VectorStore


def create_retrieval_service(
    app_settings: Settings | None = None,
    *,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
) -> RetrievalService:
    resolved_settings = app_settings or settings
    return RetrievalService(
        embedding_service=embedding_service or get_embedding_service(),
        vector_store=vector_store or get_vector_store(),
        default_top_k=resolved_settings.search_default_top_k,
        max_top_k=resolved_settings.search_max_top_k,
        over_fetch_multiplier=resolved_settings.search_over_fetch_multiplier,
        over_fetch_min_buffer=resolved_settings.search_over_fetch_min_buffer,
        max_fetch_k=resolved_settings.search_max_fetch_k,
        max_query_length=resolved_settings.search_max_query_length,
    )


@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    return create_retrieval_service(settings)


def clear_retrieval_caches() -> None:
    """Clear cached retrieval service singleton (for tests)."""
    get_retrieval_service.cache_clear()
