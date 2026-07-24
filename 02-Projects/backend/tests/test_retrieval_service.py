"""Unit tests for RetrievalService."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.document import Document
from app.services.document_service import create_document_with_chunks
from app.services.indexing.service import (
    INDEXING_STATUS_FAILED,
    INDEXING_STATUS_INDEXED,
    IndexingService,
)
from app.services.retrieval.exceptions import (
    RetrievalNotFoundError,
    RetrievalValidationError,
)
from app.services.retrieval.service import RetrievalService
from tests.conftest import FakeVectorStore


class TrackingVectorStore(FakeVectorStore):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions)
        self.last_search_k: int | None = None

    def search(self, query_vector: list[float], k: int):
        self.last_search_k = k
        return super().search(query_vector, k)


def _create_retrieval_service(
    fake_embedding_service,
    fake_vector_store,
    **kwargs,
) -> RetrievalService:
    defaults = {
        "default_top_k": 10,
        "max_top_k": 50,
        "over_fetch_multiplier": 5,
        "over_fetch_min_buffer": 20,
        "max_fetch_k": 200,
        "max_query_length": 4000,
    }
    defaults.update(kwargs)
    return RetrievalService(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
        **defaults,
    )


def _create_document_with_text(db_session: Session, user, text: str) -> Document:
    return create_document_with_chunks(
        db_session,
        user_id=user.id,
        filename="sample.txt",
        file_path="stored-sample.txt",
        extracted_text=text,
    )


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


def test_search_returns_owned_indexed_chunks(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Retrieval alpha paragraph.\n\n" + ("alpha " * 80),
    )
    _index_document(
        db_session,
        test_user,
        document,
        fake_embedding_service,
        fake_vector_store,
    )

    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
    )
    result = service.search(
        db_session,
        user_id=test_user.id,
        query="alpha retrieval",
        top_k=5,
    )

    assert result.query == "alpha retrieval"
    assert result.top_k == 5
    assert len(result.results) >= 1
    assert all(hit.document_id == document.id for hit in result.results)
    assert all(hit.score > 0 for hit in result.results)
    assert result.results == sorted(
        result.results,
        key=lambda hit: hit.score,
        reverse=True,
    )


def test_search_empty_query_raises_validation_error(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
    )

    with pytest.raises(RetrievalValidationError, match="empty or whitespace-only"):
        service.search(
            db_session,
            user_id=test_user.id,
            query="   ",
        )


def test_search_invalid_top_k_raises_validation_error(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
    )

    with pytest.raises(RetrievalValidationError, match="top_k must be at least 1"):
        service.search(
            db_session,
            user_id=test_user.id,
            query="valid query",
            top_k=0,
        )


def test_search_excludes_other_users_chunks(
    db_session,
    test_user,
    other_user,
    fake_embedding_service,
) -> None:
    vector_store = FakeVectorStore()
    owner_document = _create_document_with_text(
        db_session,
        test_user,
        "Owner unique paragraph.\n\n" + ("ownerterm " * 80),
    )
    other_document = _create_document_with_text(
        db_session,
        other_user,
        "Other unique paragraph.\n\n" + ("otherterm " * 80),
    )
    _index_document(
        db_session,
        test_user,
        owner_document,
        fake_embedding_service,
        vector_store,
    )
    _index_document(
        db_session,
        other_user,
        other_document,
        fake_embedding_service,
        vector_store,
    )

    service = _create_retrieval_service(fake_embedding_service, vector_store)
    result = service.search(
        db_session,
        user_id=test_user.id,
        query="otherterm unique",
        top_k=10,
    )

    assert result.results
    assert all(hit.document_id == owner_document.id for hit in result.results)
    assert all(hit.document_id != other_document.id for hit in result.results)


def test_search_excludes_non_indexed_documents(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Failed status paragraph.\n\n" + ("failedterm " * 80),
    )
    _index_document(
        db_session,
        test_user,
        document,
        fake_embedding_service,
        fake_vector_store,
    )

    document.indexing_status = INDEXING_STATUS_FAILED
    document.indexing_error = "simulated failure"
    db_session.commit()

    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
    )
    result = service.search(
        db_session,
        user_id=test_user.id,
        query="failedterm status",
        top_k=5,
    )

    assert result.results == []


def test_search_uses_over_fetch_before_ownership_filter(
    db_session,
    test_user,
    other_user,
    fake_embedding_service,
) -> None:
    vector_store = TrackingVectorStore()
    owner_document = _create_document_with_text(
        db_session,
        test_user,
        "Target owner paragraph.\n\n" + ("targetowner " * 80),
    )
    other_documents = [
        _create_document_with_text(
            db_session,
            other_user,
            f"Noise paragraph {index}.\n\n" + (f"noise{index} " * 80),
        )
        for index in range(25)
    ]

    _index_document(
        db_session,
        test_user,
        owner_document,
        fake_embedding_service,
        vector_store,
    )
    for other_document in other_documents:
        _index_document(
            db_session,
            other_user,
            other_document,
            fake_embedding_service,
            vector_store,
        )

    service = _create_retrieval_service(
        fake_embedding_service,
        vector_store,
        over_fetch_multiplier=5,
        over_fetch_min_buffer=20,
        max_fetch_k=200,
    )
    result = service.search(
        db_session,
        user_id=test_user.id,
        query="targetowner paragraph",
        top_k=2,
    )

    assert vector_store.last_search_k == 22
    assert len(result.results) <= 2
    assert result.results
    assert all(hit.document_id == owner_document.id for hit in result.results)


def test_search_scoped_document_not_found_for_other_user(
    db_session,
    test_user,
    other_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    other_document = _create_document_with_text(
        db_session,
        other_user,
        "Scoped other paragraph.\n\n" + ("scopedother " * 80),
    )
    _index_document(
        db_session,
        other_user,
        other_document,
        fake_embedding_service,
        fake_vector_store,
    )

    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
    )

    with pytest.raises(RetrievalNotFoundError, match="Document not found."):
        service.search(
            db_session,
            user_id=test_user.id,
            query="scopedother paragraph",
            document_id=other_document.id,
        )


def test_search_scoped_document_requires_indexed_status(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Pending scope paragraph.\n\n" + ("pendingscope " * 80),
    )
    document.indexing_status = INDEXING_STATUS_FAILED
    document.indexing_error = "not searchable"
    db_session.commit()

    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
    )

    with pytest.raises(RetrievalNotFoundError, match="Document not found."):
        service.search(
            db_session,
            user_id=test_user.id,
            query="pendingscope paragraph",
            document_id=document.id,
        )


def test_search_scoped_document_limits_results_to_document(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    first_document = _create_document_with_text(
        db_session,
        test_user,
        "Scope first paragraph.\n\n" + ("scopefirst " * 80),
    )
    second_document = _create_document_with_text(
        db_session,
        test_user,
        "Scope second paragraph.\n\n" + ("scopesecond " * 80),
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

    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
    )
    result = service.search(
        db_session,
        user_id=test_user.id,
        query="scopesecond paragraph",
        top_k=10,
        document_id=second_document.id,
    )

    assert result.results
    assert all(hit.document_id == second_document.id for hit in result.results)


def test_search_returns_empty_results_when_index_is_empty(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
    )
    result = service.search(
        db_session,
        user_id=test_user.id,
        query="empty index query",
    )

    assert result.results == []


def test_search_caps_top_k_at_service_max(
    db_session,
    test_user,
    fake_embedding_service,
    fake_vector_store,
) -> None:
    document = _create_document_with_text(
        db_session,
        test_user,
        "Cap topk paragraph.\n\n" + ("capterm " * 80),
    )
    _index_document(
        db_session,
        test_user,
        document,
        fake_embedding_service,
        fake_vector_store,
    )

    service = _create_retrieval_service(
        fake_embedding_service,
        fake_vector_store,
        max_top_k=3,
    )
    result = service.search(
        db_session,
        user_id=test_user.id,
        query="capterm topk",
        top_k=100,
    )

    assert result.top_k == 3
    assert len(result.results) <= 3


def test_get_indexed_searchable_chunks_by_ids_preserves_faiss_order(
    db_session,
    test_user,
) -> None:
    from app.services.document_service import get_indexed_searchable_chunks_by_ids

    document = _create_document_with_text(
        db_session,
        test_user,
        "Order paragraph one.\n\n" + ("orderone " * 120),
    )
    document.indexing_status = INDEXING_STATUS_INDEXED
    document.indexed_at = datetime.utcnow()
    db_session.commit()

    chunk_ids = [chunk.id for chunk in document.chunks]
    assert len(chunk_ids) >= 2
    requested_order = list(reversed(chunk_ids))

    records = get_indexed_searchable_chunks_by_ids(
        db_session,
        user_id=test_user.id,
        chunk_ids=requested_order,
    )

    assert [record.chunk_id for record in records] == requested_order
