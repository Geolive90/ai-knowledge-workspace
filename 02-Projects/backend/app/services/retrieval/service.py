"""Semantic retrieval orchestration service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.document_service import (
    SearchableChunkRecord,
    get_indexed_searchable_chunks_by_ids,
    get_document_for_user,
)
from app.services.embedding.exceptions import (
    EmbeddingError,
    InvalidEmbeddingInputError,
)
from app.services.embedding.service import EmbeddingService
from app.services.indexing.service import INDEXING_STATUS_INDEXED
from app.services.retrieval.exceptions import (
    RetrievalEmbeddingError,
    RetrievalNotFoundError,
    RetrievalValidationError,
    RetrievalVectorStoreError,
)
from app.services.retrieval.result import SearchHit, SearchResult
from app.services.vector_store.exceptions import VectorStoreError
from app.services.vector_store.provider import VectorStore


class RetrievalService:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        default_top_k: int = 10,
        max_top_k: int = 50,
        over_fetch_multiplier: int = 5,
        over_fetch_min_buffer: int = 20,
        max_fetch_k: int = 200,
        max_query_length: int = 4000,
    ) -> None:
        if default_top_k < 1:
            raise ValueError("default_top_k must be at least 1")
        if max_top_k < 1:
            raise ValueError("max_top_k must be at least 1")
        if over_fetch_multiplier < 1:
            raise ValueError("over_fetch_multiplier must be at least 1")
        if over_fetch_min_buffer < 0:
            raise ValueError("over_fetch_min_buffer must be at least 0")
        if max_fetch_k < 1:
            raise ValueError("max_fetch_k must be at least 1")
        if max_query_length < 1:
            raise ValueError("max_query_length must be at least 1")

        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._default_top_k = default_top_k
        self._max_top_k = max_top_k
        self._over_fetch_multiplier = over_fetch_multiplier
        self._over_fetch_min_buffer = over_fetch_min_buffer
        self._max_fetch_k = max_fetch_k
        self._max_query_length = max_query_length

    def search(
        self,
        db: Session,
        *,
        user_id: int,
        query: str,
        top_k: int | None = None,
        document_id: int | None = None,
    ) -> SearchResult:
        normalized_query = self._validate_query(query)
        resolved_top_k = self._resolve_top_k(top_k)

        if document_id is not None:
            self._validate_scoped_document(db, user_id=user_id, document_id=document_id)

        try:
            embedding = self._embedding_service.embed_text(normalized_query)
        except InvalidEmbeddingInputError as error:
            raise RetrievalValidationError(str(error)) from error
        except EmbeddingError as error:
            raise RetrievalEmbeddingError(
                "Query embedding generation failed."
            ) from error

        k_fetch = self._compute_fetch_k(resolved_top_k)
        if k_fetch == 0:
            return SearchResult(
                query=normalized_query,
                top_k=resolved_top_k,
                results=[],
            )

        try:
            raw_hits = self._vector_store.search(embedding.vector, k_fetch)
        except VectorStoreError as error:
            raise RetrievalVectorStoreError(
                "Vector store search failed."
            ) from error

        chunk_ids = [hit.chunk_id for hit in raw_hits]
        searchable_records = get_indexed_searchable_chunks_by_ids(
            db,
            user_id=user_id,
            chunk_ids=chunk_ids,
            document_id=document_id,
        )
        records_by_chunk_id = {
            record.chunk_id: record for record in searchable_records
        }

        results: list[SearchHit] = []
        for raw_hit in raw_hits:
            record = records_by_chunk_id.get(raw_hit.chunk_id)
            if record is None:
                continue
            results.append(self._to_search_hit(record, raw_hit.score))
            if len(results) >= resolved_top_k:
                break

        return SearchResult(
            query=normalized_query,
            top_k=resolved_top_k,
            results=results,
        )

    def _validate_query(self, query: str) -> str:
        if query is None:
            raise RetrievalValidationError(
                "Search query must not be empty or whitespace-only."
            )

        normalized = query.strip()
        if not normalized:
            raise RetrievalValidationError(
                "Search query must not be empty or whitespace-only."
            )
        if len(normalized) > self._max_query_length:
            raise RetrievalValidationError(
                f"Search query must not exceed {self._max_query_length} characters."
            )
        return normalized

    def _resolve_top_k(self, top_k: int | None) -> int:
        resolved = self._default_top_k if top_k is None else top_k
        if resolved < 1:
            raise RetrievalValidationError("top_k must be at least 1.")
        return min(resolved, self._max_top_k)

    def _validate_scoped_document(
        self,
        db: Session,
        *,
        user_id: int,
        document_id: int,
    ) -> None:
        document = get_document_for_user(db, document_id, user_id)
        if document is None or document.indexing_status != INDEXING_STATUS_INDEXED:
            raise RetrievalNotFoundError("Document not found.")

    def _compute_fetch_k(self, top_k: int) -> int:
        index_count = self._vector_store.count
        if index_count == 0:
            return 0

        candidate = max(
            top_k,
            top_k * self._over_fetch_multiplier,
            top_k + self._over_fetch_min_buffer,
        )
        return min(index_count, self._max_fetch_k, candidate)

    @staticmethod
    def _to_search_hit(record: SearchableChunkRecord, score: float) -> SearchHit:
        return SearchHit(
            chunk_id=record.chunk_id,
            document_id=record.document_id,
            document_filename=record.document_filename,
            chunk_index=record.chunk_index,
            chunk_text=record.chunk_text,
            score=score,
        )
