"""Vector store layer exceptions."""


class VectorStoreError(Exception):
    """Base exception for vector store layer errors."""


class VectorStoreConfigurationError(VectorStoreError):
    """Invalid or unsupported vector store configuration."""


class VectorStoreDimensionMismatchError(VectorStoreError):
    """Vector or loaded index has unexpected dimensions."""


class VectorStoreDuplicateIdError(VectorStoreError):
    """Attempted to add a chunk_id that already exists in the index."""


class VectorStoreLoadError(VectorStoreError):
    """Failed to load a vector index from disk."""


class VectorStorePersistenceError(VectorStoreError):
    """Failed to persist a vector index to disk."""


class VectorStoreProviderError(VectorStoreError):
    """Vector store provider runtime failure."""
