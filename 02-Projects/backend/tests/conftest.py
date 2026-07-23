"""Shared pytest fixtures for backend tests."""

import hashlib

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.chunk_embedding import ChunkEmbedding  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.document_chunk import DocumentChunk  # noqa: F401
from app.models.user import User
from app.services.embedding.factory import clear_embedding_caches
from app.services.embedding.service import EmbeddingService
from app.services.indexing.factory import clear_indexing_caches, create_indexing_service
from app.services.vector_store.exceptions import (
    VectorStoreDimensionMismatchError,
    VectorStoreDuplicateIdError,
)
from app.services.vector_store.factory import clear_vector_store_caches
from app.services.vector_store.provider import VectorAddItem, VectorSearchResult
from app.utils.security import hash_password


class FakeEmbeddingProvider:
    model_name = "fake/test-model"
    dimensions = 8

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [self._vector_for_text(text) for text in texts]

    def _vector_for_text(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [
            ((digest[index % len(digest)] / 255.0) * 2.0) - 1.0
            for index in range(self.dimensions)
        ]


class FailingEmbeddingProvider:
    model_name = "fake/failing-model"
    dimensions = 4

    def embed_text(self, text: str) -> list[float]:
        raise RuntimeError("provider failure")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("provider failure")


class WrongCountEmbeddingProvider(FakeEmbeddingProvider):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [self._vector_for_text(texts[0])]


class WrongDimensionEmbeddingProvider(FakeEmbeddingProvider):
    dimensions = 8

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class CountingEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self) -> None:
        self.call_count = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        return super().embed_texts(texts)


class FakeVectorStore:
    def __init__(self, dimensions: int = 8) -> None:
        self._dimensions = dimensions
        self._vectors: dict[int, list[float]] = {}

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def count(self) -> int:
        return len(self._vectors)

    def add(self, items: list[VectorAddItem]) -> None:
        seen_in_batch: set[int] = set()
        for item in items:
            if item.chunk_id in self._vectors or item.chunk_id in seen_in_batch:
                raise VectorStoreDuplicateIdError(
                    f"chunk_id {item.chunk_id} already exists in the vector index."
                )
            seen_in_batch.add(item.chunk_id)
            if len(item.vector) != self._dimensions:
                raise VectorStoreDimensionMismatchError(
                    "Vector dimensions do not match the configured index dimensions."
                )
            self._vectors[item.chunk_id] = self._normalize(item.vector)

    def search(self, query_vector: list[float], k: int) -> list[VectorSearchResult]:
        if k <= 0 or not self._vectors:
            return []
        if len(query_vector) != self._dimensions:
            raise VectorStoreDimensionMismatchError(
                "Vector dimensions do not match the configured index dimensions."
            )

        query = self._normalize(query_vector)
        scored = [
            VectorSearchResult(
                chunk_id=chunk_id,
                score=sum(left * right for left, right in zip(query, vector)),
            )
            for chunk_id, vector in self._vectors.items()
        ]
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:k]

    def remove_by_chunk_ids(self, chunk_ids: list[int]) -> int:
        removed = 0
        for chunk_id in chunk_ids:
            if chunk_id in self._vectors:
                del self._vectors[chunk_id]
                removed += 1
        return removed

    def clear(self) -> None:
        self._vectors.clear()

    def save(self) -> None:
        return None

    def load(self) -> None:
        return None

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0:
            raise RuntimeError("Zero-norm vector cannot be indexed or searched.")
        return [value / norm for value in vector]


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def fake_embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def fake_embedding_service(fake_embedding_provider) -> EmbeddingService:
    return EmbeddingService(fake_embedding_provider, batch_size=4)


@pytest.fixture
def fake_indexing_service(fake_embedding_service, fake_vector_store):
    return create_indexing_service(
        embedding_service=fake_embedding_service,
        vector_store=fake_vector_store,
        stale_timeout_seconds=300,
    )


@pytest.fixture(autouse=True)
def clear_embedding_factory_caches():
    clear_embedding_caches()
    clear_vector_store_caches()
    clear_indexing_caches()
    yield
    clear_embedding_caches()
    clear_vector_store_caches()
    clear_indexing_caches()


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )
    session = session_factory()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session):
    user = User(
        email="phase3-test@example.com",
        full_name="Phase 3 Test User",
        hashed_password=hash_password("testpassword"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    user = User(
        email="phase3-other@example.com",
        full_name="Other User",
        hashed_password=hash_password("otherpassword"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
