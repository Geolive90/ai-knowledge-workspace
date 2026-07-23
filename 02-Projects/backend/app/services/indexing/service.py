"""Document indexing orchestration service."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Callable, Iterator

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document
from app.services.document_service import (
    IndexingChunkRecord,
    get_document_chunk_ids,
    get_indexing_chunk_records,
    get_owned_document_with_ordered_chunks,
)
from app.services.embedding.exceptions import (
    EmbeddingError,
)
from app.services.embedding.service import EmbeddingService
from app.services.indexing.exceptions import (
    IndexingConflictError,
    IndexingEmbeddingError,
    IndexingError,
    IndexingNotFoundError,
    IndexingPersistenceError,
    IndexingVectorStoreError,
)
from app.services.indexing.result import IndexingResult, PurgeResult
from app.services.vector_store.exceptions import VectorStoreError
from app.services.vector_store.provider import VectorAddItem, VectorStore

INDEXING_STATUS_PENDING = "pending"
INDEXING_STATUS_PROCESSING = "processing"
INDEXING_STATUS_INDEXED = "indexed"
INDEXING_STATUS_FAILED = "failed"

_MAX_ERROR_LENGTH = 2000

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.utcnow()


class IndexingService:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        stale_timeout_seconds: int = 300,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if stale_timeout_seconds < 30:
            raise ValueError("stale_timeout_seconds must be at least 30")
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._stale_timeout_seconds = stale_timeout_seconds
        self._clock = clock
        self._document_locks: dict[int, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    def index_document(
        self,
        db: Session,
        *,
        document_id: int,
        user_id: int,
        force_reindex: bool = False,
    ) -> IndexingResult:
        lock = self._acquire_document_lock(document_id)
        if not lock.acquire(blocking=False):
            raise IndexingConflictError(
                "Another indexing operation is already in progress for this document."
            )

        try:
            return self._index_document_locked(
                db,
                document_id=document_id,
                user_id=user_id,
                force_reindex=force_reindex,
            )
        finally:
            lock.release()

    @contextmanager
    def document_lock(
        self,
        document_id: int,
        *,
        blocking: bool = True,
    ) -> Iterator[None]:
        lock = self._acquire_document_lock(document_id)
        acquired = lock.acquire(blocking=blocking)
        if not acquired:
            raise IndexingConflictError(
                "Another indexing operation is already in progress for this document."
            )
        try:
            yield
        finally:
            lock.release()

    def purge_document_index(
        self,
        db: Session,
        *,
        document_id: int,
    ) -> PurgeResult:
        with self.document_lock(document_id, blocking=True):
            return self._purge_document_index_unlocked(db, document_id=document_id)

    def _purge_document_index_unlocked(
        self,
        db: Session,
        *,
        document_id: int,
    ) -> PurgeResult:
        chunk_ids = get_document_chunk_ids(db, document_id)

        try:
            vectors_removed = self._vector_store.remove_by_chunk_ids(chunk_ids)
            if vectors_removed > 0:
                self._vector_store.save()
        except VectorStoreError as error:
            raise IndexingVectorStoreError(
                "Failed to purge vectors from the vector store."
            ) from error

        metadata_rows_deleted = 0
        if chunk_ids:
            metadata_rows_deleted = (
                db.query(ChunkEmbedding)
                .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
                .delete(synchronize_session=False)
            )
            db.commit()

        return PurgeResult(
            chunk_ids_considered=len(chunk_ids),
            vectors_removed=vectors_removed,
            metadata_rows_deleted=metadata_rows_deleted,
        )

    def _index_document_locked(
        self,
        db: Session,
        *,
        document_id: int,
        user_id: int,
        force_reindex: bool,
    ) -> IndexingResult:
        document = get_owned_document_with_ordered_chunks(
            db,
            document_id=document_id,
            user_id=user_id,
        )
        if document is None:
            raise IndexingNotFoundError("Document not found.")

        if (
            document.indexing_status == INDEXING_STATUS_INDEXED
            and not force_reindex
        ):
            chunk_records = get_indexing_chunk_records(document)
            return IndexingResult(
                document_id=document.id,
                indexing_status=document.indexing_status,
                chunk_count=len(chunk_records),
                vectors_indexed=len(chunk_records),
                indexed_at=document.indexed_at,
                indexing_error=document.indexing_error,
                skipped=True,
            )

        if self._is_active_processing(document):
            raise IndexingConflictError(
                "Document indexing is already in progress."
            )

        if not self._claim_processing(db, document_id, user_id, force_reindex):
            raise IndexingConflictError(
                "Document indexing could not be claimed."
            )

        document = get_owned_document_with_ordered_chunks(
            db,
            document_id=document_id,
            user_id=user_id,
        )
        if document is None:
            raise IndexingNotFoundError("Document not found.")

        chunk_records = get_indexing_chunk_records(document)

        try:
            if not chunk_records:
                return self._mark_indexed_zero_chunks(db, document)

            self.purge_document_index(db, document_id=document.id)

            texts = [record.chunk_text for record in chunk_records]
            try:
                embeddings = self._embedding_service.embed_texts(texts)
            except EmbeddingError as error:
                raise IndexingEmbeddingError(
                    "Embedding generation failed during indexing."
                ) from error

            add_items = [
                VectorAddItem(
                    chunk_id=record.chunk_id,
                    vector=embedding.vector,
                )
                for record, embedding in zip(chunk_records, embeddings)
            ]

            try:
                self._vector_store.add(add_items)
                self._vector_store.save()
            except VectorStoreError as error:
                raise IndexingVectorStoreError(
                    "Vector store operation failed during indexing."
                ) from error

            now = self._clock()
            try:
                for record, embedding in zip(chunk_records, embeddings):
                    db.add(
                        ChunkEmbedding(
                            chunk_id=record.chunk_id,
                            model_name=embedding.model_name,
                            dimensions=embedding.dimensions,
                        )
                    )
                document.indexing_status = INDEXING_STATUS_INDEXED
                document.indexed_at = now
                document.indexing_started_at = None
                document.indexing_error = None
                db.commit()
                db.refresh(document)
            except Exception as error:
                db.rollback()
                raise IndexingPersistenceError(
                    "Failed to persist indexing metadata."
                ) from error

            return IndexingResult(
                document_id=document.id,
                indexing_status=document.indexing_status,
                chunk_count=len(chunk_records),
                vectors_indexed=len(chunk_records),
                indexed_at=document.indexed_at,
                indexing_error=document.indexing_error,
                skipped=False,
            )

        except IndexingError as error:
            self._mark_failed(db, document_id=document.id, error_message=str(error))
            raise

    def _mark_indexed_zero_chunks(
        self,
        db: Session,
        document: Document,
    ) -> IndexingResult:
        now = self._clock()
        document.indexing_status = INDEXING_STATUS_INDEXED
        document.indexed_at = now
        document.indexing_started_at = None
        document.indexing_error = None
        db.commit()
        db.refresh(document)
        return IndexingResult(
            document_id=document.id,
            indexing_status=document.indexing_status,
            chunk_count=0,
            vectors_indexed=0,
            indexed_at=document.indexed_at,
            indexing_error=document.indexing_error,
            skipped=False,
        )

    def _mark_failed(
        self,
        db: Session,
        *,
        document_id: int,
        error_message: str,
    ) -> None:
        compensation_error: str | None = None
        try:
            self.purge_document_index(db, document_id=document_id)
        except IndexingError as error:
            compensation_error = str(error)
            logger.warning(
                "Indexing compensation purge failed for document_id=%s",
                document_id,
                exc_info=error,
            )

        truncated = error_message[:_MAX_ERROR_LENGTH]
        if compensation_error:
            suffix = f" (compensation purge failed: {compensation_error})"
            truncated = error_message[: _MAX_ERROR_LENGTH - len(suffix)] + suffix

        db.query(Document).filter(Document.id == document_id).update(
            {
                Document.indexing_status: INDEXING_STATUS_FAILED,
                Document.indexing_error: truncated,
                Document.indexing_started_at: None,
            },
            synchronize_session=False,
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    def _claim_processing(
        self,
        db: Session,
        document_id: int,
        user_id: int,
        force_reindex: bool,
    ) -> bool:
        now = self._clock()
        stale_cutoff = now - timedelta(seconds=self._stale_timeout_seconds)

        claim_conditions = or_(
            Document.indexing_status.in_(
                [INDEXING_STATUS_PENDING, INDEXING_STATUS_FAILED]
            ),
            and_(
                Document.indexing_status == INDEXING_STATUS_PROCESSING,
                Document.indexing_started_at.isnot(None),
                Document.indexing_started_at < stale_cutoff,
            ),
        )
        if force_reindex:
            claim_conditions = or_(
                claim_conditions,
                Document.indexing_status == INDEXING_STATUS_INDEXED,
            )

        rows_updated = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                Document.user_id == user_id,
                claim_conditions,
            )
            .update(
                {
                    Document.indexing_status: INDEXING_STATUS_PROCESSING,
                    Document.indexing_started_at: now,
                    Document.indexing_error: None,
                },
                synchronize_session=False,
            )
        )
        if rows_updated == 0:
            db.rollback()
            return False

        db.commit()
        return True

    def _is_active_processing(self, document: Document) -> bool:
        if document.indexing_status != INDEXING_STATUS_PROCESSING:
            return False
        if document.indexing_started_at is None:
            return True

        stale_cutoff = self._clock() - timedelta(
            seconds=self._stale_timeout_seconds
        )
        return document.indexing_started_at >= stale_cutoff

    def _acquire_document_lock(self, document_id: int) -> threading.RLock:
        with self._locks_guard:
            if document_id not in self._document_locks:
                self._document_locks[document_id] = threading.RLock()
            return self._document_locks[document_id]
