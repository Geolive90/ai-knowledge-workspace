"""Embedding provider and service factory."""

from functools import lru_cache

from app.config import Settings, settings
from app.services.embedding.exceptions import EmbeddingConfigurationError
from app.services.embedding.provider import EmbeddingProvider
from app.services.embedding.providers.sentence_transformers import (
    SentenceTransformersProvider,
)
from app.services.embedding.service import EmbeddingService

SUPPORTED_PROVIDERS = frozenset({"sentence_transformers"})


def create_embedding_provider(app_settings: Settings | None = None) -> EmbeddingProvider:
    resolved_settings = app_settings or settings
    provider_name = resolved_settings.embedding_provider.strip().lower()

    if provider_name not in SUPPORTED_PROVIDERS:
        raise EmbeddingConfigurationError(
            f"Unsupported embedding provider: {resolved_settings.embedding_provider!r}. "
            f"Supported providers: {sorted(SUPPORTED_PROVIDERS)}"
        )

    if provider_name == "sentence_transformers":
        return SentenceTransformersProvider(model=resolved_settings.embedding_model)

    raise EmbeddingConfigurationError(
        f"Unsupported embedding provider: {resolved_settings.embedding_provider!r}."
    )


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    return create_embedding_provider(settings)


def create_embedding_service(
    provider: EmbeddingProvider | None = None,
    *,
    batch_size: int | None = None,
    app_settings: Settings | None = None,
) -> EmbeddingService:
    resolved_settings = app_settings or settings
    if provider is not None:
        resolved_provider = provider
    elif app_settings is not None:
        resolved_provider = create_embedding_provider(resolved_settings)
    else:
        resolved_provider = get_embedding_provider()
    resolved_batch_size = (
        batch_size
        if batch_size is not None
        else resolved_settings.embedding_batch_size
    )
    return EmbeddingService(resolved_provider, batch_size=resolved_batch_size)


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return create_embedding_service()


def clear_embedding_caches() -> None:
    """Clear cached provider/service singletons (for tests)."""
    get_embedding_provider.cache_clear()
    get_embedding_service.cache_clear()
