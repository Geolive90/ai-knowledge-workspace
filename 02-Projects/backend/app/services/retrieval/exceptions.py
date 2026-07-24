"""Retrieval orchestration exceptions."""


class RetrievalError(Exception):
    """Base exception for retrieval orchestration errors."""


class RetrievalValidationError(RetrievalError):
    """Search input failed validation."""


class RetrievalNotFoundError(RetrievalError):
    """Scoped document not found, not owned, or not searchable."""


class RetrievalEmbeddingError(RetrievalError):
    """Query embedding generation failed."""


class RetrievalVectorStoreError(RetrievalError):
    """Vector store search failed."""
