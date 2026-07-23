"""Indexing orchestration exceptions."""


class IndexingError(Exception):
    """Base exception for indexing orchestration errors."""


class IndexingNotFoundError(IndexingError):
    """Document not found or not owned by the requesting user."""


class IndexingConflictError(IndexingError):
    """Indexing cannot proceed due to active processing or a lost claim race."""


class IndexingEmbeddingError(IndexingError):
    """Embedding generation failed during indexing."""


class IndexingVectorStoreError(IndexingError):
    """Vector store operation failed during indexing."""


class IndexingPersistenceError(IndexingError):
    """Database persistence failed during indexing."""
