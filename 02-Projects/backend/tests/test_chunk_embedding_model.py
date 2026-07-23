"""Tests for ChunkEmbedding model, relationships, and cascade behavior."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.document_service import create_document_with_chunks, delete_document

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_MODULE = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "f3a1b8c45201_create_chunk_embeddings_table.py"
)


def _create_document_with_single_chunk(db_session, test_user) -> Document:
    return create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="embedding-test.txt",
        file_path="stored-embedding-test.txt",
        extracted_text="Embedding metadata test content.",
    )


def _add_embedding_for_chunk(
    db_session,
    chunk: DocumentChunk,
    *,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    dimensions: int = 384,
) -> ChunkEmbedding:
    embedding = ChunkEmbedding(
        chunk_id=chunk.id,
        model_name=model_name,
        dimensions=dimensions,
    )
    db_session.add(embedding)
    db_session.commit()
    db_session.refresh(embedding)
    return embedding


def test_chunk_embedding_can_be_persisted(db_session, test_user) -> None:
    document = _create_document_with_single_chunk(db_session, test_user)
    chunk = document.chunks[0]

    embedding = _add_embedding_for_chunk(db_session, chunk)

    assert embedding.id is not None
    assert embedding.chunk_id == chunk.id
    assert embedding.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert embedding.dimensions == 384
    assert embedding.created_at is not None


def test_one_to_one_relationship_from_chunk_to_embedding(
    db_session,
    test_user,
) -> None:
    document = _create_document_with_single_chunk(db_session, test_user)
    chunk = document.chunks[0]
    embedding = _add_embedding_for_chunk(db_session, chunk)

    db_session.refresh(chunk)

    assert chunk.embedding is not None
    assert chunk.embedding.id == embedding.id
    assert chunk.embedding.chunk_id == chunk.id


def test_one_to_one_relationship_from_embedding_to_chunk(
    db_session,
    test_user,
) -> None:
    document = _create_document_with_single_chunk(db_session, test_user)
    chunk = document.chunks[0]
    embedding = _add_embedding_for_chunk(db_session, chunk)

    db_session.refresh(embedding)

    assert embedding.chunk is not None
    assert embedding.chunk.id == chunk.id
    assert embedding.chunk.chunk_text == chunk.chunk_text


def test_second_embedding_for_same_chunk_is_rejected(
    db_session,
    test_user,
) -> None:
    document = _create_document_with_single_chunk(db_session, test_user)
    chunk = document.chunks[0]
    _add_embedding_for_chunk(db_session, chunk)

    duplicate = ChunkEmbedding(
        chunk_id=chunk.id,
        model_name="other-model",
        dimensions=1536,
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_deleting_chunk_removes_embedding(db_session, test_user) -> None:
    document = _create_document_with_single_chunk(db_session, test_user)
    chunk = document.chunks[0]
    embedding = _add_embedding_for_chunk(db_session, chunk)
    embedding_id = embedding.id
    chunk_id = chunk.id

    db_session.delete(chunk)
    db_session.commit()

    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.id == embedding_id)
        .first()
        is None
    )
    assert (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.id == chunk_id)
        .first()
        is None
    )


def test_deleting_document_cascades_through_chunks_to_embeddings(
    db_session,
    test_user,
) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="cascade-test.txt",
        file_path="stored-cascade-test.txt",
        extracted_text="Cascade embedding test " * 200,
    )

    embedding_ids = []
    for chunk in document.chunks:
        embedding = _add_embedding_for_chunk(db_session, chunk)
        embedding_ids.append(embedding.id)

    document_id = document.id
    assert len(embedding_ids) > 0

    delete_document(db_session, document)

    assert (
        db_session.query(Document)
        .filter(Document.id == document_id)
        .first()
        is None
    )
    assert (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .count()
        == 0
    )
    assert (
        db_session.query(ChunkEmbedding)
        .filter(ChunkEmbedding.id.in_(embedding_ids))
        .count()
        == 0
    )


def test_migration_module_is_structurally_valid() -> None:
    spec = importlib.util.spec_from_file_location(
        "chunk_embeddings_migration",
        MIGRATION_MODULE,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "f3a1b8c45201"
    assert module.down_revision == "e8c5b6a30293"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_migration_upgrade_and_downgrade(tmp_path) -> None:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine

    from app.models.document_chunk import DocumentChunk
    from app.models.user import User

    database_path = tmp_path / "migration_test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    legacy_metadata = MetaData()
    legacy_documents = Table(
        "documents",
        legacy_metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, nullable=False),
        Column("filename", String, nullable=False),
        Column("file_path", String, nullable=False),
        Column("extracted_text", Text, nullable=True),
        Column("uploaded_at", DateTime),
    )

    engine = create_engine(database_url)
    User.__table__.create(bind=engine, checkfirst=True)
    legacy_documents.create(bind=engine, checkfirst=True)
    DocumentChunk.__table__.create(bind=engine, checkfirst=True)
    engine.dispose()

    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    command.stamp(alembic_cfg, "e8c5b6a30293")
    command.upgrade(alembic_cfg, "head")

    import sqlite3

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_embeddings'"
    )
    assert cursor.fetchone() is not None

    cursor.execute("PRAGMA table_info(chunk_embeddings)")
    columns = {row[1] for row in cursor.fetchall()}
    assert columns == {
        "id",
        "chunk_id",
        "model_name",
        "dimensions",
        "created_at",
    }

    cursor.execute("PRAGMA table_info(documents)")
    document_columns = {row[1] for row in cursor.fetchall()}
    assert {
        "indexing_status",
        "indexing_error",
        "indexed_at",
        "indexing_started_at",
    }.issubset(document_columns)
    connection.close()

    command.downgrade(alembic_cfg, "e8c5b6a30293")

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_embeddings'"
    )
    assert cursor.fetchone() is None
    connection.close()
