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


@pytest.fixture
def fake_embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture(autouse=True)
def clear_embedding_factory_caches():
    clear_embedding_caches()
    yield
    clear_embedding_caches()


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
