"""API tests for document indexing orchestration."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db, get_indexing_service_dependency
from app.main import app
from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document
from app.services.document_service import create_document_with_chunks
from app.services.indexing.service import INDEXING_STATUS_FAILED, INDEXING_STATUS_INDEXED
from app.utils import file_handler


@pytest.fixture
def upload_folder(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(file_handler, "UPLOAD_FOLDER", upload_dir)
    return upload_dir


@pytest.fixture
def client(db_session, upload_folder, fake_indexing_service):
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


def register_and_login(client: TestClient, email: str, password: str) -> str:
    client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Indexing API User",
            "password": password,
        },
    )
    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_upload_indexes_document_and_returns_indexing_fields(
    client,
    db_session,
) -> None:
    token = register_and_login(client, "index-upload@example.com", "password123")
    content = ("Upload indexing paragraph.\n\n" + "word " * 120).encode("utf-8")

    response = client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={"file": ("indexing.txt", BytesIO(content), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["indexing_status"] == INDEXING_STATUS_INDEXED
    assert payload["chunk_count"] > 0
    assert payload["vectors_indexed"] == payload["chunk_count"]
    assert payload["indexed_at"] is not None
    assert payload["indexing_error"] is None

    document = db_session.get(Document, payload["document_id"])
    assert document.indexing_status == INDEXING_STATUS_INDEXED
    chunk_ids = [chunk.id for chunk in document.chunks]
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.chunk_id.in_(chunk_ids))
        .count()
        == payload["chunk_count"]
    )


def test_index_endpoint_retries_failed_document(
    client,
    db_session,
    test_user,
) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="failed.txt",
        file_path="failed.txt",
        extracted_text="Retry endpoint paragraph.\n\n" + ("retry " * 80),
    )
    document.indexing_status = INDEXING_STATUS_FAILED
    document.indexing_error = "previous failure"
    db_session.commit()

    client.post(
        "/auth/register",
        json={
            "email": test_user.email,
            "full_name": test_user.full_name,
            "password": "testpassword",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login.json()["access_token"]

    response = client.post(
        f"/documents/{document.id}/index",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["indexing_status"] == INDEXING_STATUS_INDEXED
    assert payload["indexing_error"] is None


def test_index_endpoint_returns_404_for_other_user(
    client,
    db_session,
    test_user,
    other_user,
) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="private.txt",
        file_path="private.txt",
        extracted_text="Private paragraph.\n\n" + ("private " * 80),
    )
    db_session.commit()

    client.post(
        "/auth/register",
        json={
            "email": other_user.email,
            "full_name": other_user.full_name,
            "password": "otherpassword",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": other_user.email, "password": "otherpassword"},
    )
    token = login.json()["access_token"]

    response = client.post(
        f"/documents/{document.id}/index",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_upload_indexing_failure_returns_200_with_retry_info(
    client,
    db_session,
    fake_indexing_service,
    monkeypatch,
) -> None:
    from app.services.embedding.service import EmbeddingService
    from tests.conftest import FailingEmbeddingProvider

    failing_embedding_service = EmbeddingService(
        FailingEmbeddingProvider(),
        batch_size=2,
    )
    monkeypatch.setattr(
        fake_indexing_service,
        "_embedding_service",
        failing_embedding_service,
    )

    token = register_and_login(client, "index-fail@example.com", "password123")
    content = ("Upload failure paragraph.\n\n" + "fail " * 120).encode("utf-8")

    response = client.post(
        "/documents/upload",
        headers=auth_headers(token),
        files={"file": ("fail.txt", BytesIO(content), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["indexing_status"] == INDEXING_STATUS_FAILED
    assert payload["indexing_error"] is not None
    assert payload["retry"]["path"] == f"/documents/{payload['document_id']}/index"


def test_delete_purges_vectors_before_database_delete(
    client,
    db_session,
    fake_indexing_service,
    test_user,
    upload_folder,
) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="delete.txt",
        file_path="delete.txt",
        extracted_text="Delete purge paragraph.\n\n" + ("delete " * 80),
    )
    fake_indexing_service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )
    chunk_count = len(document.chunks)
    vector_count_before = fake_indexing_service._vector_store.count

    stored_path = upload_folder / "delete.txt"
    stored_path.write_text("placeholder", encoding="utf-8")
    document.file_path = "delete.txt"
    db_session.commit()

    client.post(
        "/auth/register",
        json={
            "email": test_user.email,
            "full_name": test_user.full_name,
            "password": "testpassword",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    token = login.json()["access_token"]

    response = client.delete(
        f"/documents/{document.id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert db_session.get(Document, document.id) is None
    assert fake_indexing_service._vector_store.count == vector_count_before - chunk_count
