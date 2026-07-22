"""Tests for vector store factory and configuration."""

from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.services.vector_store.exceptions import VectorStoreConfigurationError
from app.services.vector_store.factory import (
    clear_vector_store_caches,
    create_vector_store,
    get_vector_store,
)
from app.services.vector_store.providers.faiss import FaissVectorStore


def _base_settings_kwargs(**overrides) -> dict:
    values = {
        "database_url": "sqlite:///:memory:",
        "secret_key": "test-secret",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "faiss_index_path": "data/faiss/test_factory_index.faiss",
    }
    values.update(overrides)
    return values


def test_unknown_provider_raises_configuration_error(tmp_path) -> None:
    app_settings = Settings(
        **_base_settings_kwargs(
            vector_store_provider="pinecone",
            faiss_index_path=str(tmp_path / "unused.faiss"),
        )
    )

    with pytest.raises(VectorStoreConfigurationError):
        create_vector_store(app_settings, dimensions=4)


@patch("app.services.vector_store.factory.FaissVectorStore", autospec=True)
def test_create_vector_store_uses_faiss(
    mock_store_class: MagicMock,
    tmp_path,
) -> None:
    mock_store_class.return_value = MagicMock(spec=FaissVectorStore)
    app_settings = Settings(
        **_base_settings_kwargs(faiss_index_path=str(tmp_path / "index.faiss"))
    )

    store = create_vector_store(app_settings, dimensions=384)

    mock_store_class.assert_called_once_with(
        dimensions=384,
        index_path=str(tmp_path / "index.faiss"),
    )
    mock_store_class.return_value.load.assert_called_once()
    assert store is mock_store_class.return_value


@patch("app.services.vector_store.factory.FaissVectorStore", autospec=True)
def test_get_vector_store_returns_cached_instance(
    mock_store_class: MagicMock,
    tmp_path,
) -> None:
    mock_store_class.return_value = MagicMock(spec=FaissVectorStore)
    clear_vector_store_caches()
    app_settings = Settings(
        **_base_settings_kwargs(faiss_index_path=str(tmp_path / "cached.faiss"))
    )

    with patch("app.services.vector_store.factory.settings", app_settings):
        first = get_vector_store()
        second = get_vector_store()

    assert first is second
    mock_store_class.assert_called_once()


@patch("app.services.embedding.factory.get_embedding_provider")
@patch("app.services.vector_store.factory.FaissVectorStore", autospec=True)
def test_create_vector_store_reads_dimensions_from_embedding_provider(
    mock_store_class: MagicMock,
    mock_get_provider: MagicMock,
    tmp_path,
) -> None:
    mock_get_provider.return_value = MagicMock(dimensions=384)
    mock_store_class.return_value = MagicMock(spec=FaissVectorStore)
    app_settings = Settings(
        **_base_settings_kwargs(faiss_index_path=str(tmp_path / "dims.faiss"))
    )

    create_vector_store(app_settings)

    mock_get_provider.assert_called_once()
    mock_store_class.assert_called_once_with(
        dimensions=384,
        index_path=str(tmp_path / "dims.faiss"),
    )


@patch("app.services.embedding.factory.get_embedding_provider")
@patch("app.services.vector_store.factory.FaissVectorStore", autospec=True)
def test_create_vector_store_explicit_dimensions_skips_embedding_provider(
    mock_store_class: MagicMock,
    mock_get_provider: MagicMock,
    tmp_path,
) -> None:
    mock_store_class.return_value = MagicMock(spec=FaissVectorStore)
    app_settings = Settings(
        **_base_settings_kwargs(faiss_index_path=str(tmp_path / "explicit.faiss"))
    )

    create_vector_store(app_settings, dimensions=8)

    mock_get_provider.assert_not_called()
    mock_store_class.assert_called_once_with(
        dimensions=8,
        index_path=str(tmp_path / "explicit.faiss"),
    )


@patch("app.services.vector_store.factory.FaissVectorStore", autospec=True)
def test_clear_vector_store_caches_returns_fresh_instance(
    mock_store_class: MagicMock,
    tmp_path,
) -> None:
    first_instance = MagicMock(spec=FaissVectorStore)
    second_instance = MagicMock(spec=FaissVectorStore)
    mock_store_class.side_effect = [first_instance, second_instance]
    clear_vector_store_caches()
    app_settings = Settings(
        **_base_settings_kwargs(faiss_index_path=str(tmp_path / "refresh.faiss"))
    )

    with patch("app.services.vector_store.factory.settings", app_settings):
        first = get_vector_store()
        clear_vector_store_caches()
        second = get_vector_store()

    assert first is first_instance
    assert second is second_instance
    assert first is not second
    assert mock_store_class.call_count == 2
