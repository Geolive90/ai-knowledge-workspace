"""Indexing service integration tests with temporary FAISS paths."""

import os

import pytest

from app.config import Settings
from app.services.document_service import create_document_with_chunks
from app.services.embedding.service import EmbeddingService
from app.services.indexing.service import INDEXING_STATUS_INDEXED, IndexingService
from app.services.vector_store.factory import create_vector_store
from tests.conftest import FakeEmbeddingProvider

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_FAISS_INTEGRATION") != "1",
    reason="Set RUN_FAISS_INTEGRATION=1 to run indexing FAISS integration tests.",
)


def _test_settings(index_path: str) -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
        faiss_index_path=index_path,
    )


def test_index_document_persists_vectors_to_faiss(
    db_session,
    test_user,
    tmp_path,
) -> None:
    index_path = tmp_path / "indexing-integration.faiss"
    vector_store = create_vector_store(
        app_settings=_test_settings(str(index_path)),
        dimensions=8,
    )
    embedding_service = EmbeddingService(FakeEmbeddingProvider(), batch_size=4)
    service = IndexingService(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="faiss-index.txt",
        file_path="faiss-index.txt",
        extracted_text="FAISS integration paragraph.\n\n" + ("vector " * 80),
    )

    result = service.index_document(
        db_session,
        document_id=document.id,
        user_id=test_user.id,
    )

    assert result.indexing_status == INDEXING_STATUS_INDEXED
    assert index_path.exists()

    query = embedding_service.embed_text(document.chunks[0].chunk_text)
    matches = vector_store.search(query.vector, k=1)
    assert matches
    assert matches[0].chunk_id == document.chunks[0].id
