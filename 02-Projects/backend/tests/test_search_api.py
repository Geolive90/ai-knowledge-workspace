"""API tests for semantic search."""

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

import pytest

from app.dependencies import get_db, get_retrieval_service_dependency
from app.main import app
from app.models.document import Document
from app.services.document_service import create_document_with_chunks
from app.services.indexing.service import INDEXING_STATUS_FAILED, IndexingService
from app.services.retrieval.exceptions import (
    RetrievalEmbeddingError,
    RetrievalValidationError,
    RetrievalVectorStoreError,
)


class ValidationFailureRetrievalService:
    def search(self, *args, **kwargs):
        raise RetrievalValidationError("Simulated retrieval validation failure.")


class EmbeddingFailureRetrievalService:
    def search(self, *args, **kwargs):
        raise RetrievalEmbeddingError("Query embedding generation failed.")


class VectorStoreFailureRetrievalService:
    def search(self, *args, **kwargs):
        raise RetrievalVectorStoreError("Vector store search failed.")


@pytest.fixture
def client(db_session, fake_retrieval_service):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_retrieval_service_dependency] = (
        lambda: fake_retrieval_service
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client_with_retrieval_override(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def register_and_login(client: TestClient, email: str, password: str) -> str:
    client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Search API User",
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


def _index_document(
    db_session: Session,
    user,
    document: Document,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    indexing_service = IndexingService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
    )
    indexing_service.index_document(
        db_session,
        document_id=document.id,
        user_id=user.id,
    )


def test_search_requires_authentication(client) -> None:
    response = client.post(
        "/search",
        json={"query": "unauthenticated search"},
    )

    assert response.status_code == 401


def test_search_rejects_empty_query(client) -> None:
    token = register_and_login(client, "search-empty@example.com", "password123")

    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={"query": ""},
    )

    assert response.status_code == 422


def test_search_rejects_whitespace_only_query(client) -> None:
    token = register_and_login(client, "search-space@example.com", "password123")

    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={"query": "   \t\n  "},
    )

    assert response.status_code == 422


def test_search_rejects_top_k_below_one(client) -> None:
    token = register_and_login(client, "search-topk@example.com", "password123")

    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={"query": "valid query", "top_k": 0},
    )

    assert response.status_code == 422


def test_search_returns_matching_results(
    client,
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="search-hit.txt",
        file_path="search-hit.txt",
        extracted_text="Search API paragraph.\n\n" + ("searchterm " * 80),
    )
    _index_document(
        db_session,
        test_user,
        document,
        fake_embedding_service,
        fake_vector_store,
    )

    token = register_and_login(client, test_user.email, "testpassword")
    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={"query": "searchterm paragraph", "top_k": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "searchterm paragraph"
    assert payload["top_k"] == 5
    assert payload["results"]

    first = payload["results"][0]
    assert first["chunk_id"] > 0
    assert first["document_id"] == document.id
    assert first["document_filename"] == "search-hit.txt"
    assert first["chunk_index"] >= 0
    assert first["chunk_text"]
    assert isinstance(first["score"], float)


def test_search_returns_empty_results_for_empty_index(
    client,
    test_user,
) -> None:
    token = register_and_login(client, test_user.email, "testpassword")
    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={"query": "no indexed content"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "no indexed content"
    assert payload["top_k"] == 10
    assert payload["results"] == []


def test_search_never_returns_other_users_chunks(
    client,
    db_session,
    test_user,
    other_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    owner_document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="owner-search.txt",
        file_path="owner-search.txt",
        extracted_text="Owner search paragraph.\n\n" + ("owneronly " * 80),
    )
    other_document = create_document_with_chunks(
        db_session,
        user_id=other_user.id,
        filename="other-search.txt",
        file_path="other-search.txt",
        extracted_text="Other search paragraph.\n\n" + ("otheronly " * 80),
    )
    _index_document(
        db_session,
        test_user,
        owner_document,
        fake_embedding_service,
        fake_vector_store,
    )
    _index_document(
        db_session,
        other_user,
        other_document,
        fake_embedding_service,
        fake_vector_store,
    )

    token = register_and_login(client, test_user.email, "testpassword")
    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={"query": "otheronly search", "top_k": 10},
    )

    assert response.status_code == 200
    assert response.json()["results"]
    assert all(
        hit["document_id"] == owner_document.id
        for hit in response.json()["results"]
    )
    assert all(
        hit["document_id"] != other_document.id
        for hit in response.json()["results"]
    )


def test_search_document_scope_limits_results(
    client,
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    first_document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="scope-first.txt",
        file_path="scope-first.txt",
        extracted_text="Scope first paragraph.\n\n" + ("scopefirst " * 80),
    )
    second_document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="scope-second.txt",
        file_path="scope-second.txt",
        extracted_text="Scope second paragraph.\n\n" + ("scopesecond " * 80),
    )
    _index_document(
        db_session,
        test_user,
        first_document,
        fake_embedding_service,
        fake_vector_store,
    )
    _index_document(
        db_session,
        test_user,
        second_document,
        fake_embedding_service,
        fake_vector_store,
    )

    token = register_and_login(client, test_user.email, "testpassword")
    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={
            "query": "scopesecond paragraph",
            "document_id": second_document.id,
        },
    )

    assert response.status_code == 200
    assert response.json()["results"]
    assert all(
        hit["document_id"] == second_document.id
        for hit in response.json()["results"]
    )


def test_search_document_scope_other_user_returns_404(
    client,
    db_session,
    test_user,
    other_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    other_document = create_document_with_chunks(
        db_session,
        user_id=other_user.id,
        filename="scope-other.txt",
        file_path="scope-other.txt",
        extracted_text="Scope other paragraph.\n\n" + ("scopeother " * 80),
    )
    _index_document(
        db_session,
        other_user,
        other_document,
        fake_embedding_service,
        fake_vector_store,
    )

    token = register_and_login(client, test_user.email, "testpassword")
    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={
            "query": "scopeother paragraph",
            "document_id": other_document.id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_search_document_scope_non_indexed_returns_404(
    client,
    db_session,
    test_user,
) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="scope-failed.txt",
        file_path="scope-failed.txt",
        extracted_text="Scope failed paragraph.\n\n" + ("scopefailed " * 80),
    )
    document.indexing_status = INDEXING_STATUS_FAILED
    document.indexing_error = "not searchable"
    db_session.commit()

    token = register_and_login(client, test_user.email, "testpassword")
    response = client.post(
        "/search",
        headers=auth_headers(token),
        json={
            "query": "scopefailed paragraph",
            "document_id": document.id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_search_maps_retrieval_validation_error_to_422(
    client_with_retrieval_override,
    test_user,
) -> None:
    app.dependency_overrides[get_retrieval_service_dependency] = (
        lambda: ValidationFailureRetrievalService()
    )

    token = register_and_login(
        client_with_retrieval_override,
        test_user.email,
        "testpassword",
    )
    response = client_with_retrieval_override.post(
        "/search",
        headers=auth_headers(token),
        json={"query": "valid query"},
    )

    assert response.status_code == 422
    assert "Simulated retrieval validation failure." in response.json()["detail"]


def test_search_maps_embedding_failure_to_safe_500(
    client_with_retrieval_override,
    test_user,
) -> None:
    app.dependency_overrides[get_retrieval_service_dependency] = (
        lambda: EmbeddingFailureRetrievalService()
    )

    token = register_and_login(
        client_with_retrieval_override,
        test_user.email,
        "testpassword",
    )
    response = client_with_retrieval_override.post(
        "/search",
        headers=auth_headers(token),
        json={"query": "valid query"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Search could not be completed."
    assert "embedding" not in response.json()["detail"].lower()
    assert "faiss" not in response.json()["detail"].lower()


def test_search_maps_vector_store_failure_to_safe_500(
    client_with_retrieval_override,
    test_user,
) -> None:
    app.dependency_overrides[get_retrieval_service_dependency] = (
        lambda: VectorStoreFailureRetrievalService()
    )

    token = register_and_login(
        client_with_retrieval_override,
        test_user.email,
        "testpassword",
    )
    response = client_with_retrieval_override.post(
        "/search",
        headers=auth_headers(token),
        json={"query": "valid query"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Search could not be completed."
    assert "vector" not in response.json()["detail"].lower()
    assert "faiss" not in response.json()["detail"].lower()
