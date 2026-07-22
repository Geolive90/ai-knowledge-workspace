"""Vector store provider and service factory."""

from functools import lru_cache

from app.config import Settings, settings
from app.services.vector_store.exceptions import VectorStoreConfigurationError
from app.services.vector_store.provider import VectorStore
from app.services.vector_store.providers.faiss import FaissVectorStore

SUPPORTED_PROVIDERS = frozenset({"faiss"})


def create_vector_store(
    app_settings: Settings | None = None,
    *,
    dimensions: int | None = None,
) -> VectorStore:
    resolved_settings = app_settings or settings
    provider_name = resolved_settings.vector_store_provider.strip().lower()

    if provider_name not in SUPPORTED_PROVIDERS:
        raise VectorStoreConfigurationError(
            f"Unsupported vector store provider: {resolved_settings.vector_store_provider!r}. "
            f"Supported providers: {sorted(SUPPORTED_PROVIDERS)}"
        )

    resolved_dimensions = dimensions
    if resolved_dimensions is None:
        from app.services.embedding.factory import get_embedding_provider

        resolved_dimensions = get_embedding_provider().dimensions

    if provider_name == "faiss":
        store = FaissVectorStore(
            dimensions=resolved_dimensions,
            index_path=resolved_settings.faiss_index_path,
        )
        store.load()
        return store

    raise VectorStoreConfigurationError(
        f"Unsupported vector store provider: {resolved_settings.vector_store_provider!r}."
    )


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    return create_vector_store(settings)


def clear_vector_store_caches() -> None:
    """Clear cached vector store singletons (for tests)."""
    get_vector_store.cache_clear()
