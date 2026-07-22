"""Embedding service — text validation, batching, and vector validation."""

from dataclasses import dataclass

from app.services.embedding.exceptions import (
    EmbeddingDimensionMismatchError,
    EmbeddingProviderError,
    InvalidEmbeddingInputError,
)
from app.services.embedding.provider import EmbeddingProvider


@dataclass(frozen=True)
class EmbeddingVector:
    vector: list[float]
    model_name: str
    dimensions: int


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider, *, batch_size: int = 32) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self._provider = provider
        self._batch_size = batch_size

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    @property
    def dimensions(self) -> int:
        return self._provider.dimensions

    def embed_text(self, text: str) -> EmbeddingVector:
        validated_text = self._validate_text(text)
        vectors = self._embed_validated_texts([validated_text])
        return vectors[0]

    def embed_texts(self, texts: list[str]) -> list[EmbeddingVector]:
        if not texts:
            return []

        validated_texts = [self._validate_text(text) for text in texts]
        return self._embed_validated_texts(validated_texts)

    def _validate_text(self, text: str) -> str:
        if text is None or not text.strip():
            raise InvalidEmbeddingInputError(
                "Embedding input text must not be empty or whitespace-only."
            )
        return text

    def _embed_validated_texts(self, texts: list[str]) -> list[EmbeddingVector]:
        vectors: list[list[float]] = []

        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            try:
                batch_vectors = self._provider.embed_texts(batch)
            except EmbeddingProviderError:
                raise
            except Exception as error:
                raise EmbeddingProviderError(
                    "Embedding provider failed while generating vectors."
                ) from error

            if len(batch_vectors) != len(batch):
                raise EmbeddingDimensionMismatchError(
                    "Embedding provider returned a different number of vectors "
                    "than input texts."
                )

            for vector in batch_vectors:
                self._validate_vector_dimensions(vector)

            vectors.extend(batch_vectors)

        return [
            EmbeddingVector(
                vector=vector,
                model_name=self._provider.model_name,
                dimensions=self._provider.dimensions,
            )
            for vector in vectors
        ]

    def _validate_vector_dimensions(self, vector: list[float]) -> None:
        if len(vector) != self._provider.dimensions:
            raise EmbeddingDimensionMismatchError(
                "Embedding provider returned a vector with unexpected dimensions."
            )
