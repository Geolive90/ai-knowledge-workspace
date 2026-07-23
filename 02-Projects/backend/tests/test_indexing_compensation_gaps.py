"""Phase 4D compensation and deletion gap verification tests."""

from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.dependencies import get_db, get_indexing_service_dependency
from app.main import app
from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document
from app.services.document_service import create_document_with_chunks, delete_document
from app.services.embedding.service import EmbeddingService
from app.services.indexing.exceptions import (
    IndexingConflictError,
    IndexingEmbeddingError,
    IndexingPersistenceError,
    IndexingVectorStoreError,
)
from app.services.indexing.service import (
    INDEXING_STATUS_FAILED,
    INDEXING_STATUS_INDEXED,
    INDEXING_STATUS_PROCESSING,
    IndexingService,
)
from app.services.vector_store.exceptions import (
    VectorStorePersistenceError,
    VectorStoreProviderError,
)
from app.services.vector_store.provider import VectorAddItem
from app.utils import file_handler
from tests.conftest import (
    FailingEmbeddingProvider,
    FakeEmbeddingProvider,
    FakeVectorStore,
)


def _create_document_with_text(db_session: Session, test_user, text: str) -> Document:
    return create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="gap-test.txt",
        file_path="gap-test.txt",
        extracted_text=text,
    )


def _service(
    embedding_service,
    vector_store,
    *,
    stale_timeout_seconds: int = 300,
    clock=None,
) -> IndexingService:
    return IndexingService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        stale_timeout_seconds=stale_timeout_seconds,
        clock=clock or (lambda: datetime.utcnow()),
    )


def _load_document_fresh(db_engine, document_id: int) -> Document | None:
    session = sessionmaker(bind=db_engine)()
    try:
        return session.get(Document, document_id)
    finally:
        session.close()


class FailingRemoveWhenVectorsExist(FakeVectorStore):
    def remove_by_chunk_ids(self, chunk_ids: list[int]) -> int:
        if self.count > 0:
            raise VectorStoreProviderError("simulated compensation remove failure")
        return super().remove_by_chunk_ids(chunk_ids)


class CompensationSaveFailVectorStore(FakeVectorStore):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions)
        self._fail_next_save_after_remove = False

    def remove_by_chunk_ids(self, chunk_ids: list[int]) -> int:
        removed = super().remove_by_chunk_ids(chunk_ids)
        if removed > 0:
            self._fail_next_save_after_remove = True
        return removed

    def save(self) -> None:
        if self._fail_next_save_after_remove:
            self._fail_next_save_after_remove = False
            raise VectorStorePersistenceError("simulated compensation save failure")
        super().save()


class PartialAddVectorStore(FakeVectorStore):
    def add(self, items: list[VectorAddItem]) -> None:
        if not items:
            return
        super().add([items[0]])
        if len(items) > 1:
            raise VectorStoreProviderError("simulated partial add failure")


class MemoryDiskVectorStore(FakeVectorStore):
    """In-memory store with a separate durable snapshot updated only on save()."""

    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions)
        self.disk = FakeVectorStore(dimensions=dimensions)
        self._fail_next_compensation_save = False

    def remove_by_chunk_ids(self, chunk_ids: list[int]) -> int:
        removed = super().remove_by_chunk_ids(chunk_ids)
        if removed > 0:
            self._fail_next_compensation_save = True
        return removed

    def save(self) -> None:
        if self._fail_next_compensation_save:
            self._fail_next_compensation_save = False
            raise VectorStorePersistenceError("simulated compensation save failure")
        self.disk.clear()
        for chunk_id, vector in self._vectors.items():
            self.disk.add([VectorAddItem(chunk_id=chunk_id, vector=vector)])


def test_failed_status_commit_failure_leaves_processing_until_stale(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
    db_engine,
    monkeypatch,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Failed commit paragraph.\n\n" + ("failcommit " * 80),
    )
    service = _service(fake_embedding_service, fake_vector_store)
    true_commit = db_session.commit
    commit_count = {"value": 0}

    def patched_commit() -> None:
        commit_count["value"] += 1
        if commit_count["value"] == 3:
            db_session.rollback()
            raise RuntimeError("simulated metadata commit failure")
        if commit_count["value"] == 5:
            db_session.rollback()
            raise RuntimeError("simulated failed-status commit failure")
        true_commit()

    monkeypatch.setattr(db_session, "commit", patched_commit)

    with pytest.raises(RuntimeError, match="simulated failed-status commit failure"):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.rollback()
    durable = _load_document_fresh(db_engine, document.id)
    assert durable is not None
    assert durable.indexing_status == INDEXING_STATUS_PROCESSING
    assert durable.indexing_started_at is not None
    assert durable.indexing_error is None
    assert fake_vector_store.count == 0
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_([c.id for c in document.chunks]))
        .count()
        == 0
    )

    stale_clock = [
        durable.indexing_started_at + timedelta(seconds=301),
    ]
    recovery_service = _service(
        fake_embedding_service,
        fake_vector_store,
        stale_timeout_seconds=300,
        clock=lambda: stale_clock[0],
    )
    result = recovery_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    assert result.indexing_status == INDEXING_STATUS_INDEXED


def test_compensation_purge_remove_failure_preserves_primary_error_context(
    db_session,
    test_user,
    fake_embedding_service,
    monkeypatch,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Comp remove paragraph.\n\n" + ("compremove " * 80),
    )
    vector_store = FailingRemoveWhenVectorsExist()
    service = _service(fake_embedding_service, vector_store)
    original_commit = db_session.commit
    commit_calls = {"count": 0}

    def fail_metadata_commit() -> None:
        commit_calls["count"] += 1
        if commit_calls["count"] == 3:
            db_session.rollback()
            raise RuntimeError("simulated metadata commit failure")
        original_commit()

    monkeypatch.setattr(db_session, "commit", fail_metadata_commit)

    with pytest.raises(IndexingPersistenceError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    assert document.indexing_started_at is None
    assert "Failed to persist indexing metadata." in (document.indexing_error or "")
    assert "compensation purge failed" in (document.indexing_error or "")
    assert vector_store.count > 0
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_([c.id for c in document.chunks]))
        .count()
        == 0
    )

    healthy_store = FakeVectorStore()
    for chunk_id in [chunk.id for chunk in document.chunks]:
        healthy_store.add([VectorAddItem(chunk_id=chunk_id, vector=[0.1] * 8)])
    recovery_service = _service(fake_embedding_service, healthy_store)
    result = recovery_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert healthy_store.count == len(document.chunks)


def test_compensation_purge_save_failure_leaves_disk_vectors(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Comp save paragraph.\n\n" + ("compsave " * 80),
    )
    backing = MemoryDiskVectorStore()
    service = _service(fake_embedding_service, backing)
    original_commit = db_session.commit
    commit_calls = {"count": 0}

    def fail_metadata_commit() -> None:
        commit_calls["count"] += 1
        if commit_calls["count"] == 3:
            raise RuntimeError("simulated metadata commit failure")
        original_commit()

    db_session.commit = fail_metadata_commit  # type: ignore[method-assign]

    with pytest.raises(IndexingPersistenceError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    assert document.indexing_started_at is None
    assert backing.count == 0
    assert backing.disk.count > 0
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_([c.id for c in document.chunks]))
        .count()
        == 0
    )

    healthy_store = FakeVectorStore()
    recovery_service = _service(fake_embedding_service, healthy_store)
    result = recovery_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert healthy_store.count == len(document.chunks)


def test_compensation_purge_save_failure_faiss_reload(
    db_session,
    test_user,
    tmp_path,
) -> None:
    if os.environ.get("RUN_FAISS_INTEGRATION") != "1":
        pytest.skip("Set RUN_FAISS_INTEGRATION=1 to run FAISS compensation save test.")

    from app.config import Settings
    from app.services.vector_store.factory import create_vector_store

    index_path = tmp_path / "comp-save-fail.faiss"
    settings = Settings(
        database_url="sqlite:///:memory:",
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
        faiss_index_path=str(index_path),
    )
    vector_store = CompensationSaveFailVectorStore()
    service = _service(EmbeddingService(FakeEmbeddingProvider(), batch_size=4), vector_store)
    document = _create_document_with_text(
        db_session,
        test_user,
        "FAISS comp save paragraph.\n\n" + ("faisscomp " * 80),
    )
    original_commit = db_session.commit
    commit_calls = {"count": 0}

    def fail_metadata_commit() -> None:
        commit_calls["count"] += 1
        if commit_calls["count"] == 3:
            raise RuntimeError("simulated metadata commit failure")
        original_commit()

    db_session.commit = fail_metadata_commit  # type: ignore[method-assign]

    with pytest.raises(IndexingPersistenceError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    chunk_ids = [chunk.id for chunk in document.chunks]
    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    assert vector_store.count == 0

    faiss_store = create_vector_store(app_settings=settings, dimensions=8)
    for chunk_id in chunk_ids:
        faiss_store.add([VectorAddItem(chunk_id=chunk_id, vector=[0.2] * 8)])
    faiss_store.save()
    assert faiss_store.count == len(chunk_ids)

    recovery = _service(
        EmbeddingService(FakeEmbeddingProvider(), batch_size=4),
        create_vector_store(app_settings=settings, dimensions=8),
    )
    result = recovery.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    assert result.indexing_status == INDEXING_STATUS_INDEXED
    reloaded_after = create_vector_store(app_settings=settings, dimensions=8)
    assert reloaded_after.count == len(chunk_ids)


def test_partial_vector_add_compensation_and_retry(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Partial add paragraph.\n\n" + ("partial chunk content. " * 200),
    )
    vector_store = PartialAddVectorStore()
    service = _service(fake_embedding_service, vector_store)
    chunk_ids = [chunk.id for chunk in document.chunks]
    assert len(chunk_ids) > 1

    with pytest.raises(IndexingVectorStoreError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    assert document.indexing_started_at is None
    assert vector_store.count == 0
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        .count()
        == 0
    )

    healthy_store = FakeVectorStore()
    recovery = _service(fake_embedding_service, healthy_store)
    result = recovery.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert healthy_store.count == len(chunk_ids)
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        .count()
        == len(chunk_ids)
    )


@pytest.fixture
def upload_folder(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(file_handler, "UPLOAD_FOLDER", upload_dir)
    return upload_dir


@pytest.fixture
def api_client(db_session, upload_folder, fake_indexing_service):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_indexing_service_dependency] = (
        lambda: fake_indexing_service
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _auth_client(api_client: TestClient, test_user) -> str:
    api_client.post(
        "/auth/register",
        json={
            "email": test_user.email,
            "full_name": test_user.full_name,
            "password": "testpassword",
        },
    )
    login = api_client.post(
        "/auth/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    return login.json()["access_token"]


def test_database_deletion_failure_after_purge_is_retry_safe(
    api_client,
    db_session,
    test_user,
    fake_indexing_service,
    upload_folder,
    monkeypatch,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Db delete fail paragraph.\n\n" + ("dbdelete " * 80),
    )
    fake_indexing_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    chunk_ids = [chunk.id for chunk in document.chunks]
    vector_count = fake_indexing_service._vector_store.count

    stored_path = upload_folder / "gap-test.txt"
    stored_path.write_text("stored content", encoding="utf-8")
    db_session.commit()

    attempts = {"count": 0}
    original_delete = delete_document

    def flaky_delete(db, doc) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("simulated database deletion failure")
        original_delete(db, doc)

    monkeypatch.setattr(
        "app.routers.documents.delete_document",
        flaky_delete,
    )

    token = _auth_client(api_client, test_user)
    first = api_client.delete(
        f"/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 500
    assert db_session.get(Document, document.id) is not None
    assert stored_path.exists()
    assert fake_indexing_service._vector_store.count == vector_count - len(chunk_ids)

    second = api_client.delete(
        f"/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 200
    assert db_session.get(Document, document.id) is None
    assert not stored_path.exists()
    assert fake_indexing_service._vector_store.count == vector_count - len(chunk_ids)


def test_stored_file_deletion_failure_returns_success_and_logs(
    api_client,
    db_session,
    test_user,
    fake_indexing_service,
    upload_folder,
    monkeypatch,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "File delete fail paragraph.\n\n" + ("filedelete " * 80),
    )
    fake_indexing_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    chunk_ids = [chunk.id for chunk in document.chunks]

    stored_path = upload_folder / "gap-test.txt"
    stored_path.write_text("stored content", encoding="utf-8")
    db_session.commit()

    from unittest.mock import patch

    from app.routers import documents as documents_router

    calls: list[str] = []

    def fail_unlink(stored_filename: str) -> bool:
        calls.append(stored_filename)
        raise OSError("simulated stored file deletion failure")

    monkeypatch.setattr(documents_router, "delete_stored_file", fail_unlink)

    token = _auth_client(api_client, test_user)

    with patch.object(documents_router.logger, "warning") as warning_mock:
        response = api_client.delete(
            f"/documents/{document.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert calls == ["gap-test.txt"]
    assert db_session.get(Document, document.id) is None
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        .count()
        == 0
    )
    assert fake_indexing_service._vector_store.count == 0
    assert stored_path.exists()
    warning_mock.assert_called_once()
    assert warning_mock.call_args.args[0] == "Stored file deletion failed for document_id=%s path=%s"


def test_delete_flow_acquires_document_lock(
    db_session,
    test_user,
    fake_indexing_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Lock acquire paragraph.\n\n" + ("lockacq " * 80),
    )
    fake_indexing_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    lock = fake_indexing_service._acquire_document_lock(document.id)
    assert lock.acquire(blocking=False) is True
    lock.release()

    with fake_indexing_service.document_lock(document.id, blocking=True):
        fake_indexing_service.purge_document_index(
            db_session,
            document_id=document.id,
        )
        delete_document(db_session, document)

    assert lock.acquire(blocking=False) is True
    lock.release()


def test_purge_reacquires_document_lock_without_deadlock(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Reentrant lock paragraph.\n\n" + ("reentrant " * 80),
    )
    service = _service(fake_embedding_service, fake_vector_store)
    service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    with service.document_lock(document.id, blocking=True):
        result = service.purge_document_index(db_session, document_id=document.id)
        assert result.vectors_removed == len(document.chunks)


def test_index_cannot_run_between_purge_and_db_delete(
    db_session,
    test_user,
    fake_indexing_service,
    monkeypatch,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Between purge delete paragraph.\n\n" + ("between " * 80),
    )
    fake_indexing_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    vector_count = fake_indexing_service._vector_store.count
    gate = threading.Event()
    proceed = threading.Event()
    index_errors: list[Exception] = []

    original_delete = delete_document

    def slow_delete(db, doc) -> None:
        gate.set()
        proceed.wait(timeout=5)
        original_delete(db, doc)

    monkeypatch.setattr(
        "app.routers.documents.delete_document",
        slow_delete,
    )

    def run_delete() -> None:
        with fake_indexing_service.document_lock(document.id, blocking=True):
            fake_indexing_service.purge_document_index(
                db_session,
                document_id=document.id,
            )
            slow_delete(db_session, document)

    delete_thread = threading.Thread(target=run_delete)
    delete_thread.start()
    assert gate.wait(timeout=5)

    try:
        fake_indexing_service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )
    except IndexingConflictError as error:
        index_errors.append(error)

    assert index_errors
    assert fake_indexing_service._vector_store.count == 0

    proceed.set()
    delete_thread.join(timeout=5)
    assert db_session.get(Document, document.id) is None


def test_document_lock_released_when_db_delete_raises(
    db_session,
    test_user,
    fake_indexing_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Lock release paragraph.\n\n" + ("lockrel " * 80),
    )
    fake_indexing_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    with pytest.raises(RuntimeError, match="simulated db delete failure"):
        with fake_indexing_service.document_lock(document.id, blocking=True):
            fake_indexing_service.purge_document_index(
                db_session,
                document_id=document.id,
            )
            raise RuntimeError("simulated db delete failure")

    acquired = fake_indexing_service._acquire_document_lock(document.id).acquire(
        blocking=False
    )
    assert acquired is True
    fake_indexing_service._acquire_document_lock(document.id).release()
