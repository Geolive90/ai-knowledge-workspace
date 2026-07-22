"""Tests for EmbeddingService."""

import pytest

from app.services.embedding.exceptions import (
    EmbeddingDimensionMismatchError,
    EmbeddingProviderError,
    InvalidEmbeddingInputError,
)
from app.services.embedding.service import EmbeddingService
from tests.conftest import (
    CountingEmbeddingProvider,
    FailingEmbeddingProvider,
    WrongCountEmbeddingProvider,
    WrongDimensionEmbeddingProvider,
)


def test_embed_text_returns_embedding_vector(fake_embedding_provider) -> None:
    service = EmbeddingService(fake_embedding_provider)

    result = service.embed_text("hello world")

    assert result.model_name == "fake/test-model"
    assert result.dimensions == 8
    assert len(result.vector) == 8


def test_embed_texts_returns_multiple_vectors(fake_embedding_provider) -> None:
    service = EmbeddingService(fake_embedding_provider)
    texts = ["first text", "second text", "third text"]

    results = service.embed_texts(texts)

    assert len(results) == 3
    assert [len(result.vector) for result in results] == [8, 8, 8]
    assert [result.model_name for result in results] == [
        "fake/test-model",
        "fake/test-model",
        "fake/test-model",
    ]


def test_embed_texts_empty_list_returns_empty(fake_embedding_provider) -> None:
    service = EmbeddingService(fake_embedding_provider)

    assert service.embed_texts([]) == []


@pytest.mark.parametrize("invalid_text", ["", "   ", "\n\t  "])
def test_blank_or_whitespace_text_raises(invalid_text, fake_embedding_provider) -> None:
    service = EmbeddingService(fake_embedding_provider)

    with pytest.raises(InvalidEmbeddingInputError):
        service.embed_text(invalid_text)


def test_embed_texts_rejects_blank_entry(fake_embedding_provider) -> None:
    service = EmbeddingService(fake_embedding_provider)

    with pytest.raises(InvalidEmbeddingInputError):
        service.embed_texts(["valid text", "   "])


def test_embed_text_is_deterministic(fake_embedding_provider) -> None:
    service = EmbeddingService(fake_embedding_provider)

    first = service.embed_text("deterministic input")
    second = service.embed_text("deterministic input")

    assert first.vector == second.vector


def test_embed_texts_preserves_order(fake_embedding_provider) -> None:
    service = EmbeddingService(fake_embedding_provider)
    texts = ["alpha", "beta", "gamma"]

    results = service.embed_texts(texts)

    assert results[0].vector != results[1].vector
    assert results[1].vector != results[2].vector
    assert service.embed_text("alpha").vector == results[0].vector
    assert service.embed_text("gamma").vector == results[2].vector


def test_embed_texts_batches_provider_calls() -> None:
    provider = CountingEmbeddingProvider()
    service = EmbeddingService(provider, batch_size=2)

    service.embed_texts(["one", "two", "three", "four", "five"])

    assert provider.call_count == 3


def test_vector_count_mismatch_raises() -> None:
    service = EmbeddingService(WrongCountEmbeddingProvider())

    with pytest.raises(EmbeddingDimensionMismatchError):
        service.embed_texts(["one", "two"])


def test_dimension_mismatch_raises() -> None:
    service = EmbeddingService(WrongDimensionEmbeddingProvider())

    with pytest.raises(EmbeddingDimensionMismatchError):
        service.embed_text("dimension mismatch")


def test_provider_failure_is_normalized() -> None:
    service = EmbeddingService(FailingEmbeddingProvider())

    with pytest.raises(EmbeddingProviderError):
        service.embed_text("trigger failure")
