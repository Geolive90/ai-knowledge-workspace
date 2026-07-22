"""FAISS-backed vector store implementation."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Sequence

import faiss
import numpy as np

from app.services.vector_store.exceptions import (
    VectorStoreDimensionMismatchError,
    VectorStoreDuplicateIdError,
    VectorStoreLoadError,
    VectorStorePersistenceError,
    VectorStoreProviderError,
)
from app.services.vector_store.provider import VectorAddItem, VectorSearchResult

class FaissVectorStore:
    def __init__(self, *, dimensions: int, index_path: str | Path) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be at least 1")
        self._dimensions = dimensions
        self._index_path = Path(index_path)
        self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(dimensions))
        self._known_ids: set[int] = set()
        # Version 1 uses one RLock for all operations. This is intentionally
        # conservative because FAISS index objects are not documented as
        # thread-safe for concurrent mutation and search. Future versions may
        # split read/write synchronization if higher concurrency is needed.
        self._lock = threading.RLock()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def count(self) -> int:
        with self._lock:
            return int(self._index.ntotal)

    def add(self, items: Sequence[VectorAddItem]) -> None:
        if not items:
            return

        with self._lock:
            vectors: list[list[float]] = []
            ids: list[int] = []
            seen_in_batch: set[int] = set()

            for item in items:
                if item.chunk_id in self._known_ids or item.chunk_id in seen_in_batch:
                    raise VectorStoreDuplicateIdError(
                        f"chunk_id {item.chunk_id} already exists in the vector index."
                    )
                seen_in_batch.add(item.chunk_id)
                self._validate_vector_dimensions(item.vector)
                vectors.append(item.vector)
                ids.append(item.chunk_id)

            matrix = self._vectors_to_matrix(vectors)
            id_array = np.array(ids, dtype=np.int64)

            try:
                self._index.add_with_ids(matrix, id_array)
            except Exception as error:
                raise VectorStoreProviderError(
                    "FAISS failed while adding vectors to the index."
                ) from error

            self._known_ids.update(ids)

    def search(self, query_vector: list[float], k: int) -> list[VectorSearchResult]:
        if k <= 0:
            return []

        with self._lock:
            if self._index.ntotal == 0:
                return []

            self._validate_vector_dimensions(query_vector)
            query = self._vectors_to_matrix([query_vector])
            effective_k = min(k, self._index.ntotal)

            try:
                scores, ids = self._index.search(query, effective_k)
            except Exception as error:
                raise VectorStoreProviderError(
                    "FAISS failed while searching the index."
                ) from error

            results: list[VectorSearchResult] = []
            for score, chunk_id in zip(scores[0], ids[0]):
                if chunk_id == -1:
                    continue
                results.append(
                    VectorSearchResult(chunk_id=int(chunk_id), score=float(score))
                )
            return results

    def remove_by_chunk_ids(self, chunk_ids: Sequence[int]) -> int:
        if not chunk_ids:
            return 0

        with self._lock:
            ids_to_remove = [
                chunk_id for chunk_id in chunk_ids if chunk_id in self._known_ids
            ]
            if not ids_to_remove:
                return 0

            id_array = np.array(ids_to_remove, dtype=np.int64)
            selector = faiss.IDSelectorBatch(id_array.size, faiss.swig_ptr(id_array))

            try:
                removed = int(self._index.remove_ids(selector))
            except Exception as error:
                raise VectorStoreProviderError(
                    "FAISS failed while removing vectors from the index."
                ) from error

            for chunk_id in ids_to_remove:
                self._known_ids.discard(chunk_id)

            return removed

    def clear(self) -> None:
        with self._lock:
            self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(self._dimensions))
            self._known_ids.clear()

    def save(self) -> None:
        with self._lock:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self._index_path.with_suffix(
                self._index_path.suffix + ".tmp"
            )

            try:
                faiss.write_index(self._index, str(temp_path))
                temp_path.replace(self._index_path)
            except Exception as error:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                raise VectorStorePersistenceError(
                    "Failed to persist FAISS index to disk."
                ) from error

    def load(self) -> None:
        with self._lock:
            if not self._index_path.exists():
                self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(self._dimensions))
                self._known_ids.clear()
                return

            try:
                loaded = faiss.read_index(str(self._index_path))
            except Exception as error:
                raise VectorStoreLoadError(
                    "Failed to load FAISS index from disk."
                ) from error

            if loaded.d != self._dimensions:
                raise VectorStoreLoadError(
                    "Loaded FAISS index dimensions do not match expected dimensions."
                )

            if not isinstance(loaded, faiss.IndexIDMap2):
                raise VectorStoreLoadError(
                    "Loaded FAISS index is not an IndexIDMap2 instance."
                )

            try:
                inner_index = faiss.downcast_index(loaded.index)
            except Exception as error:
                raise VectorStoreLoadError(
                    "Loaded FAISS index inner structure is incompatible."
                ) from error

            if not isinstance(inner_index, faiss.IndexFlatIP):
                raise VectorStoreLoadError(
                    "Loaded FAISS index inner structure is not IndexFlatIP."
                )

            self._index = loaded
            self._known_ids = self._rebuild_known_ids()

    def _validate_vector_dimensions(self, vector: list[float]) -> None:
        if len(vector) != self._dimensions:
            raise VectorStoreDimensionMismatchError(
                "Vector dimensions do not match the configured index dimensions."
            )

    def _vectors_to_matrix(self, vectors: Sequence[list[float]]) -> np.ndarray:
        matrix = np.array(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[1] != self._dimensions:
            raise VectorStoreDimensionMismatchError(
                "Vector batch dimensions do not match the configured index dimensions."
            )

        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise VectorStoreProviderError(
                "Zero-norm vector cannot be indexed or searched."
            )

        return matrix / norms

    def _rebuild_known_ids(self) -> set[int]:
        if self._index.ntotal == 0:
            return set()

        try:
            id_array = faiss.vector_to_array(self._index.id_map).astype(np.int64)
        except Exception as error:
            raise VectorStoreLoadError(
                "Failed to read chunk IDs from loaded FAISS index."
            ) from error

        return set(int(chunk_id) for chunk_id in id_array.tolist())
