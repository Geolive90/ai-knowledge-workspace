"""Unit tests for IndexingService."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document
from app.services.document_service import create_document_with_chunks
from app.services.embedding.service import EmbeddingService
from app.services.indexing.exceptions import (
    IndexingConflictError,
    IndexingEmbeddingError,
    IndexingNotFoundError,
    IndexingVectorStoreError,
)
from app.services.indexing.service import (
    INDEXING_STATUS_FAILED,
    INDEXING_STATUS_INDEXED,
    INDEXING_STATUS_PROCESSING,
    IndexingService,
)
from app.services.vector_store.exceptions import VectorStorePersistenceError
from tests.conftest import FailingEmbeddingProvider, FakeVectorStore


class FailingSaveVectorStore(FakeVectorStore):
    def save(self) -> None:
        raise VectorStorePersistenceError("simulated save failure")


def _create_document_with_text(db_session: Session, test_user, text: str) -> Document:
    return create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="sample.txt",
        file_path="stored-sample.txt",
        extracted_text=text,
    )


def test_index_document_success(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Indexing service paragraph.\n\n" + ("word " * 120),
    )
    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )

    result = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.skipped is False
    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert result.chunk_count == len(document.chunks)
    assert result.vectors_indexed == len(document.chunks)
    assert result.indexed_at is not None

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_INDEXED

    chunk_ids = [chunk.id for chunk in document.chunks]
    metadata_count = (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        .count()
    )
    assert metadata_count == len(document.chunks)
    assert fake_vector_store.count == len(document.chunks)


def test_index_document_zero_chunks(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(db_session, test_user, "   \n\t  ")
    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )

    result = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert result.chunk_count == 0
    assert result.vectors_indexed == 0
    assert fake_vector_store.count == 0


def test_index_document_idempotent(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Repeat indexing paragraph.\n\n" + ("term " * 80),
    )
    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )
    first = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    second = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert first.skipped is False
    assert second.skipped is True
    assert fake_vector_store.count == len(document.chunks)


def test_index_document_force_reindex(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Force reindex paragraph.\n\n" + ("line " * 80),
    )
    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )
    service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    result = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
        force_reindex=True,
    )

    assert result.skipped is False
    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert fake_vector_store.count == len(document.chunks)


def test_index_document_embedding_failure(
    db_session,
    test_user,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Embedding failure paragraph.\n\n" + ("fail " * 80),
    )
    failing_service = EmbeddingService(FailingEmbeddingProvider(), batch_size=2)
    service = IndexingService(
        embedding_service=failing_service,
        vector_store=fake_vector_store,
    )

    with pytest.raises(IndexingEmbeddingError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    assert document.indexing_error is not None
    assert fake_vector_store.count == 0
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_([c.id for c in document.chunks]))
        .count()
        == 0
    )


def test_index_document_vector_save_failure(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Vector save failure paragraph.\n\n" + ("save " * 80),
    )
    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=FailingSaveVectorStore(),
    )

    with pytest.raises(IndexingVectorStoreError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_([c.id for c in document.chunks]))
        .count()
        == 0
    )


def test_index_document_active_processing_conflict(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Active processing paragraph.\n\n" + ("busy " * 80),
    )
    document.indexing_status = INDEXING_STATUS_PROCESSING
    document.indexing_started_at = datetime.utcnow()
    db_session.commit()

    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
        stale_timeout_seconds=300,
    )

    with pytest.raises(IndexingConflictError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )


def test_index_document_stale_processing_reclaim(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Stale processing paragraph.\n\n" + ("stale " * 80),
    )
    document.indexing_status = INDEXING_STATUS_PROCESSING
    document.indexing_started_at = datetime.utcnow() - timedelta(seconds=600)
    db_session.commit()

    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
        stale_timeout_seconds=300,
    )

    result = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.indexing_status == INDEXING_STATUS_INDEXED


def test_index_document_wrong_owner(
    db_session,
    test_user,
    other_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Ownership paragraph.\n\n" + ("owner " * 80),
    )
    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )

    with pytest.raises(IndexingNotFoundError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=other_user.id,
        )


def test_purge_document_index_idempotent(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Purge idempotency paragraph.\n\n" + ("purge " * 80),
    )
    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )
    service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    first = service.purge_document_index(db_session, document_id=document.id)
    second = service.purge_document_index(db_session, document_id=document.id)

    assert first.vectors_removed == len(document.chunks)
    assert second.vectors_removed == 0
    assert second.metadata_rows_deleted == 0


def test_indexed_status_not_set_before_vector_save(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Ordering paragraph.\n\n" + ("order " * 80),
    )
    vector_store = MagicMock()
    vector_store.add = MagicMock()
    vector_store.remove_by_chunk_ids = MagicMock(return_value=0)
    vector_store.save = MagicMock(side_effect=VectorStorePersistenceError("save failed"))

    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=vector_store,
    )

    with pytest.raises(IndexingVectorStoreError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    vector_store.save.assert_called_once()
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_([c.id for c in document.chunks]))
        .count()
        == 0
    )


def test_retry_after_failed_succeeds(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Retry paragraph.\n\n" + ("retry " * 80),
    )
    failing_service = IndexingService(
        embedding_service=EmbeddingService(FailingEmbeddingProvider(), batch_size=2),
        vector_store=fake_vector_store,
    )
    with pytest.raises(IndexingEmbeddingError):
        failing_service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    success_service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )
    result = success_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert fake_vector_store.count == len(document.chunks)
