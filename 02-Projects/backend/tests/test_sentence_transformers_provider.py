"""Optional integration tests for SentenceTransformersProvider."""

import os

import pytest

from app.services.embedding.providers.sentence_transformers import (
    CANONICAL_MODEL_NAME,
    SentenceTransformersProvider,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_EMBEDDING_INTEGRATION") != "1",
    reason="Set RUN_EMBEDDING_INTEGRATION=1 to run sentence-transformers integration tests.",
)


def test_sentence_transformers_provider_embeds_text_with_expected_dimensions() -> None:
    provider = SentenceTransformersProvider()

    assert provider.model_name == CANONICAL_MODEL_NAME
    assert provider.dimensions == 384

    vector = provider.embed_text("integration test sentence")

    assert len(vector) == 384
    assert all(isinstance(value, float) for value in vector)


def test_sentence_transformers_provider_embeds_batch() -> None:
    provider = SentenceTransformersProvider()
    texts = ["first integration sentence", "second integration sentence"]

    vectors = provider.embed_texts(texts)

    assert len(vectors) == 2
    assert all(len(vector) == provider.dimensions for vector in vectors)
