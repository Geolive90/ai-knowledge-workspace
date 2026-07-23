"""Targeted Phase 4D verification tests for independent implementation review."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import MagicMock

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
    INDEXING_STATUS_PENDING,
    INDEXING_STATUS_PROCESSING,
    IndexingService,
)
from app.services.vector_store.exceptions import (
    VectorStoreDuplicateIdError,
    VectorStorePersistenceError,
    VectorStoreProviderError,
)
from app.services.vector_store.provider import VectorAddItem
from app.utils import file_handler
from tests.conftest import (
    CountingEmbeddingProvider,
    FailingEmbeddingProvider,
    FakeEmbeddingProvider,
    FakeVectorStore,
)


class RecordingVectorStore(FakeVectorStore):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions)
        self.events: list[str] = []

    def add(self, items: list[VectorAddItem]) -> None:
        self.events.append("add")
        super().add(items)

    def remove_by_chunk_ids(self, chunk_ids: list[int]) -> int:
        self.events.append("remove")
        return super().remove_by_chunk_ids(chunk_ids)

    def save(self) -> None:
        self.events.append("save")
        super().save()


class FailingAddVectorStore(FakeVectorStore):
    def add(self, items: list[VectorAddItem]) -> None:
        raise VectorStoreDuplicateIdError("simulated add failure")


class PartialAddVectorStore(FakeVectorStore):
    def add(self, items: list[VectorAddItem]) -> None:
        if items:
            super().add(items[:1])
        raise VectorStoreProviderError("simulated partial add failure")


class FailingRemoveVectorStore(FakeVectorStore):
    def remove_by_chunk_ids(self, chunk_ids: list[int]) -> int:
        raise VectorStoreProviderError("simulated remove failure")


class FailingPurgeSaveVectorStore(FakeVectorStore):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions)
        self.save_calls = 0

    def save(self) -> None:
        self.save_calls += 1
        if self.save_calls == 1 and self.count > 0:
            raise VectorStorePersistenceError("simulated purge save failure")
        super().save()


class NoSaveVectorStore(FakeVectorStore):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions)
        self.save_calls = 0

    def save(self) -> None:
        self.save_calls += 1
        super().save()


def _create_document_with_text(db_session: Session, test_user, text: str) -> Document:
    return create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="verify.txt",
        file_path="verify.txt",
        extracted_text=text,
    )


def _service(
    db_session,
    fake_embedding_service,
    vector_store,
    *,
    stale_timeout_seconds: int = 300,
    clock=None,
) -> IndexingService:
    return IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=vector_store,
        stale_timeout_seconds=stale_timeout_seconds,
        clock=clock or (lambda: datetime.utcnow()),
    )


def test_claim_pending_status(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Pending claim paragraph.\n\n" + ("pending " * 80),
    )
    assert document.indexing_status == INDEXING_STATUS_PENDING

    result = _service(
        db_session, fake_embedding_service, fake_vector_store
    ).index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.indexing_status == INDEXING_STATUS_INDEXED


def test_claim_failed_status(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Failed claim paragraph.\n\n" + ("failed " * 80),
    )
    document.indexing_status = INDEXING_STATUS_FAILED
    document.indexing_error = "previous"
    db_session.commit()

    result = _service(
        db_session, fake_embedding_service, fake_vector_store
    ).index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.indexing_status == INDEXING_STATUS_INDEXED
    db_session.refresh(document)
    assert document.indexing_error is None


def test_competing_claims_only_one_succeeds(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
    db_engine,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Race claim paragraph.\n\n" + ("race " * 80),
    )
    session_factory = sessionmaker(bind=db_engine)
    service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )

    first_session = session_factory()
    second_session = session_factory()
    try:
        first_claim = service._claim_processing(
            first_session,
            document.id,
            test_user.id,
            force_reindex=False,
        )
        second_claim = service._claim_processing(
            second_session,
            document.id,
            test_user.id,
            force_reindex=False,
        )
    finally:
        first_session.close()
        second_session.close()

    assert first_claim is True
    assert second_claim is False


def test_index_operation_order(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Order paragraph.\n\n" + ("order " * 80),
    )
    vector_store = RecordingVectorStore()
    provider = CountingEmbeddingProvider()
    service = IndexingService(
        embedding_service=EmbeddingService(provider, batch_size=4),
        vector_store=vector_store,
    )

    result = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert provider.call_count == 1
    assert vector_store.events == ["remove", "add", "save"]

    save_index = vector_store.events.index("save")
    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_INDEXED
    metadata_count = (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_([c.id for c in document.chunks]))
        .count()
    )
    assert metadata_count == len(document.chunks)
    assert save_index < len(vector_store.events)


def test_vector_add_failure_leaves_failed_without_metadata(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Add failure paragraph.\n\n" + ("addfail " * 80),
    )
    service = _service(
        db_session,
        fake_embedding_service,
        FailingAddVectorStore(),
    )

    with pytest.raises(IndexingVectorStoreError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    assert document.indexing_error is not None
    assert document.indexing_started_at is None
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_([c.id for c in document.chunks]))
        .count()
        == 0
    )


def test_partial_vector_add_failure_marks_failed(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Partial add paragraph.\n\n" + ("partial " * 120),
    )
    vector_store = PartialAddVectorStore()
    service = _service(db_session, fake_embedding_service, vector_store)

    with pytest.raises(IndexingVectorStoreError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED
    assert vector_store.count <= 1


def test_final_database_commit_failure_marks_failed(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
    monkeypatch,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Db commit failure paragraph.\n\n" + ("dbfail " * 80),
    )
    service = _service(db_session, fake_embedding_service, fake_vector_store)
    original_commit = db_session.commit
    commit_calls = {"count": 0}

    def flaky_commit() -> None:
        commit_calls["count"] += 1
        if commit_calls["count"] == 3:
            raise RuntimeError("simulated final commit failure")
        original_commit()

    monkeypatch.setattr(db_session, "commit", flaky_commit)

    with pytest.raises(IndexingPersistenceError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    db_session.refresh(document)
    assert document.indexing_status == INDEXING_STATUS_FAILED


def test_purge_neither_metadata_nor_vectors(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Purge empty paragraph.\n\n" + ("empty " * 80),
    )
    service = _service(db_session, fake_embedding_service, fake_vector_store)

    result = service.purge_document_index(db_session, document_id=document.id)

    assert result.chunk_ids_considered == len(document.chunks)
    assert result.vectors_removed == 0
    assert result.metadata_rows_deleted == 0


def test_purge_only_metadata_exists(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Metadata only paragraph.\n\n" + ("meta " * 80),
    )
    for chunk in document.chunks:
        db_session.add(
            ChunkEmbedding(
                chunk_id=chunk.id,
                model_name="fake/model",
                dimensions=8,
            )
        )
    db_session.commit()

    result = _service(
        db_session, fake_embedding_service, fake_vector_store
    ).purge_document_index(db_session, document_id=document.id)

    assert result.vectors_removed == 0
    assert result.metadata_rows_deleted == len(document.chunks)
    assert fake_vector_store.count == 0


def test_purge_only_vectors_exist(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Vectors only paragraph.\n\n" + ("vec " * 80),
    )
    chunk_ids = [chunk.id for chunk in document.chunks]
    fake_vector_store.add(
        [
            VectorAddItem(chunk_id=chunk_id, vector=[0.1] * 8)
            for chunk_id in chunk_ids
        ]
    )

    result = _service(
        db_session, fake_embedding_service, fake_vector_store
    ).purge_document_index(db_session, document_id=document.id)

    assert result.vectors_removed == len(chunk_ids)
    assert result.metadata_rows_deleted == 0
    assert fake_vector_store.count == 0


def test_purge_zero_chunk_document(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(db_session, test_user, "   \n  ")
    result = _service(
        db_session, fake_embedding_service, fake_vector_store
    ).purge_document_index(db_session, document_id=document.id)

    assert result.chunk_ids_considered == 0
    assert result.vectors_removed == 0
    assert result.metadata_rows_deleted == 0


def test_purge_skips_save_when_nothing_removed(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "No save paragraph.\n\n" + ("nosave " * 80),
    )
    vector_store = NoSaveVectorStore()
    service = _service(db_session, fake_embedding_service, vector_store)

    result = service.purge_document_index(db_session, document_id=document.id)

    assert result.vectors_removed == 0
    assert vector_store.save_calls == 0


def test_purge_save_when_vectors_removed(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Save purge paragraph.\n\n" + ("saves " * 80),
    )
    vector_store = NoSaveVectorStore()
    for chunk in document.chunks:
        vector_store.add(
            [VectorAddItem(chunk_id=chunk.id, vector=[0.2] * 8)]
        )

    service = _service(db_session, fake_embedding_service, vector_store)
    result = service.purge_document_index(db_session, document_id=document.id)

    assert result.vectors_removed == len(document.chunks)
    assert vector_store.save_calls == 1


def test_zero_chunk_indexing_details(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(db_session, test_user, "  \n\t ")
    provider = CountingEmbeddingProvider()
    vector_store = RecordingVectorStore()
    service = IndexingService(
        embedding_service=EmbeddingService(provider, batch_size=4),
        vector_store=vector_store,
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

    db_session.refresh(document)
    assert first.vectors_indexed == 0
    assert first.chunk_count == 0
    assert document.indexing_status == INDEXING_STATUS_INDEXED
    assert document.indexed_at is not None
    assert document.indexing_started_at is None
    assert provider.call_count == 0
    assert vector_store.events == []
    assert second.skipped is True


def test_indexed_without_force_skips_embed_add_save(
    db_session,
    test_user,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Skip embed paragraph.\n\n" + ("skip " * 80),
    )
    provider = CountingEmbeddingProvider()
    vector_store = RecordingVectorStore()
    service = IndexingService(
        embedding_service=EmbeddingService(provider, batch_size=4),
        vector_store=vector_store,
    )
    service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    vector_store.events.clear()
    provider.call_count = 0

    result = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.skipped is True
    assert provider.call_count == 0
    assert vector_store.events == []


def test_force_reindex_purges_once(
    db_session,
    test_user,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Force once paragraph.\n\n" + ("force " * 80),
    )
    vector_store = RecordingVectorStore()
    service = IndexingService(
        embedding_service=EmbeddingService(CountingEmbeddingProvider(), batch_size=4),
        vector_store=vector_store,
    )
    service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    vector_store.events.clear()

    service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
        force_reindex=True,
    )

    assert vector_store.events.count("remove") == 1
    assert vector_store.events.count("add") == 1
    assert vector_store.events.count("save") >= 1
    remove_index = vector_store.events.index("remove")
    add_index = vector_store.events.index("add")
    save_indices = [index for index, event in enumerate(vector_store.events) if event == "save"]
    assert remove_index < add_index
    assert all(save_index > add_index for save_index in save_indices if save_index > add_index)


def test_no_duplicate_metadata_on_retry(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Duplicate metadata paragraph.\n\n" + ("dupmeta " * 80),
    )
    failing = _service(
        db_session,
        EmbeddingService(FailingEmbeddingProvider(), batch_size=2),
        fake_vector_store,
    )
    with pytest.raises(IndexingEmbeddingError):
        failing.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    success = _service(db_session, fake_embedding_service, fake_vector_store)
    success.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    chunk_ids = [chunk.id for chunk in document.chunks]
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        .count()
        == len(chunk_ids)
    )


def test_document_lock_blocks_concurrent_index(
    db_session,
    test_user,
    fake_embedding_service,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Lock paragraph.\n\n" + ("lock " * 80),
    )
    service = _service(db_session, fake_embedding_service, FakeVectorStore())
    started = threading.Event()
    release = threading.Event()

    def hold_lock() -> None:
        with service.document_lock(document.id, blocking=True):
            started.set()
            release.wait(timeout=5)

    thread = threading.Thread(target=hold_lock)
    thread.start()
    assert started.wait(timeout=5)

    with pytest.raises(IndexingConflictError):
        service.index_document(
            db_session,
            document_id=document.id,
            user_id=test_user.id,
        )

    release.set()
    thread.join(timeout=5)


def test_different_documents_use_independent_locks(
    fake_embedding_service,
    fake_vector_store,
) -> None:
    service = _service(
        MagicMock(),
        fake_embedding_service,
        fake_vector_store,
    )
    lock_a = service._acquire_document_lock(1)
    lock_b = service._acquire_document_lock(2)

    assert lock_a is not lock_b
    assert lock_a.acquire(blocking=False) is True
    assert lock_b.acquire(blocking=False) is True
    lock_a.release()
    lock_b.release()


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


def test_upload_extraction_failure_does_not_create_document(
    api_client,
    db_session,
    monkeypatch,
) -> None:
    from app.routers import documents as documents_router

    monkeypatch.setattr(
        documents_router,
        "extract_text",
        lambda _path: (_ for _ in ()).throw(ValueError("unsupported format")),
    )

    api_client.post(
        "/auth/register",
        json={
            "email": "extract-fail@example.com",
            "full_name": "Extract Fail",
            "password": "password123",
        },
    )
    login = api_client.post(
        "/auth/login",
        data={"username": "extract-fail@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]

    response = api_client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bad.bin", BytesIO(b"not-text"), "application/octet-stream")},
    )

    assert response.status_code == 400
    assert db_session.query(Document).count() == 0


def test_delete_purge_failure_aborts_before_db_delete(
    api_client,
    db_session,
    test_user,
    fake_indexing_service,
    monkeypatch,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Purge abort paragraph.\n\n" + ("abort " * 80),
    )

    def fail_purge(*args, **kwargs):
        raise IndexingVectorStoreError("purge failed")

    monkeypatch.setattr(fake_indexing_service, "purge_document_index", fail_purge)

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
    token = login.json()["access_token"]

    response = api_client.delete(
        f"/documents/{document.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 500
    assert db_session.get(Document, document.id) is not None


def test_manual_smoke_flow(
    db_session,
    test_user,
    tmp_path,
) -> None:
    import os

    if os.environ.get("RUN_FAISS_INTEGRATION") != "1":
        pytest.skip("Set RUN_FAISS_INTEGRATION=1 to run manual smoke flow.")

    from app.config import Settings
    from app.services.vector_store.factory import create_vector_store

    index_path = tmp_path / "smoke.faiss"
    upload_path = tmp_path / "uploads"
    upload_path.mkdir()
    stored_name = "smoke.txt"
    (upload_path / stored_name).write_text("Smoke test content.", encoding="utf-8")

    settings = Settings(
        database_url="sqlite:///:memory:",
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
        faiss_index_path=str(index_path),
    )

    vector_store = create_vector_store(app_settings=settings, dimensions=8)
    embedding_service = EmbeddingService(FakeEmbeddingProvider(), batch_size=4)
    service = IndexingService(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="smoke.txt",
        file_path=stored_name,
        extracted_text="Smoke paragraph.\n\n" + ("smoke " * 80),
    )

    first = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    assert first.indexing_status == INDEXING_STATUS_INDEXED
    chunk_ids = [chunk.id for chunk in document.chunks]
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        .count()
        == len(chunk_ids)
    )
    assert index_path.exists()
    assert vector_store.count == len(chunk_ids)

    reloaded = create_vector_store(app_settings=settings, dimensions=8)
    query = embedding_service.embed_text(document.chunks[0].chunk_text)
    matches = reloaded.search(query.vector, k=len(chunk_ids))
    assert {match.chunk_id for match in matches} == set(chunk_ids)

    second = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    assert second.skipped is True

    third = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
        force_reindex=True,
    )
    assert third.skipped is False
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        .count()
        == len(chunk_ids)
    )

    service.purge_document_index(db_session, document_id=document.id)
    delete_document(db_session, document)
    (upload_path / stored_name).unlink(missing_ok=True)

    reloaded_after = create_vector_store(app_settings=settings, dimensions=8)
    assert reloaded_after.count == 0
    assert db_session.get(Document, document.id) is None
    assert not (upload_path / stored_name).exists()
