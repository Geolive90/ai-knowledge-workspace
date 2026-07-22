"""Embedding provider interface."""

from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str:
        """Canonical provider/model identifier for metadata storage."""
        ...

    @property
    def dimensions(self) -> int:
        """Embedding vector length produced by this provider."""
        ...

    def embed_text(self, text: str) -> list[float]:
        """Embed a single non-empty text string."""
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple non-empty text strings.

        Preserves input order. Empty input returns [].
        """
        ...
