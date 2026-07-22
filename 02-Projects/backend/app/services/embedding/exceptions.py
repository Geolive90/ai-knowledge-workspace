"""Embedding layer exceptions."""


class EmbeddingError(Exception):
    """Base exception for embedding layer errors."""


class EmbeddingConfigurationError(EmbeddingError):
    """Invalid or unsupported embedding configuration."""


class EmbeddingProviderError(EmbeddingError):
    """Embedding provider runtime failure."""


class InvalidEmbeddingInputError(EmbeddingError):
    """Blank or otherwise invalid embedding input text."""


class EmbeddingDimensionMismatchError(EmbeddingError):
    """Provider returned a vector with unexpected dimensions."""
