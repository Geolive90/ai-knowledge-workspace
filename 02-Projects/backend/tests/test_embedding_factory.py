"""Tests for embedding factory and configuration."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.services.embedding.exceptions import EmbeddingConfigurationError
from app.services.embedding.factory import (
    clear_embedding_caches,
    create_embedding_provider,
    create_embedding_service,
    get_embedding_provider,
    get_embedding_service,
)
from app.services.embedding.providers.sentence_transformers import (
    CANONICAL_MODEL_NAME,
    SentenceTransformersProvider,
)


def _base_settings_kwargs(**overrides) -> dict:
    values = {
        "database_url": "sqlite:///:memory:",
        "secret_key": "test-secret",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
    }
    values.update(overrides)
    return values


def test_unknown_provider_raises_configuration_error() -> None:
    app_settings = Settings(**_base_settings_kwargs(embedding_provider="openai"))

    with pytest.raises(EmbeddingConfigurationError):
        create_embedding_provider(app_settings)


def test_invalid_batch_size_rejected_by_settings() -> None:
    with pytest.raises(ValidationError):
        Settings(**_base_settings_kwargs(embedding_batch_size=0))


@patch(
    "app.services.embedding.factory.SentenceTransformersProvider",
    autospec=True,
)
def test_create_embedding_provider_uses_sentence_transformers(
    mock_provider_class: MagicMock,
) -> None:
    mock_provider_class.return_value = MagicMock(spec=SentenceTransformersProvider)
    app_settings = Settings(**_base_settings_kwargs())

    provider = create_embedding_provider(app_settings)

    mock_provider_class.assert_called_once_with(model=CANONICAL_MODEL_NAME)
    assert provider is mock_provider_class.return_value


@patch(
    "app.services.embedding.factory.SentenceTransformersProvider",
    autospec=True,
)
def test_get_embedding_provider_returns_cached_instance(
    mock_provider_class: MagicMock,
) -> None:
    mock_provider_class.return_value = MagicMock(spec=SentenceTransformersProvider)
    clear_embedding_caches()

    first = get_embedding_provider()
    second = get_embedding_provider()

    assert first is second
    mock_provider_class.assert_called_once()


@patch(
    "app.services.embedding.factory.create_embedding_provider",
)
def test_get_embedding_service_returns_cached_instance(
    mock_create_provider: MagicMock,
) -> None:
    mock_create_provider.return_value = MagicMock(
        model_name="fake/test-model",
        dimensions=8,
    )
    clear_embedding_caches()

    first = get_embedding_service()
    second = get_embedding_service()

    assert first is second
    mock_create_provider.assert_called_once()


def test_create_embedding_service_uses_settings_batch_size(
    fake_embedding_provider,
) -> None:
    app_settings = Settings(**_base_settings_kwargs(embedding_batch_size=16))

    service = create_embedding_service(
        fake_embedding_provider,
        app_settings=app_settings,
    )

    assert service._batch_size == 16
