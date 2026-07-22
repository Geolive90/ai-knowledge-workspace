"""Tests for document_service.create_document_with_chunks()."""

from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking_service import build_chunks
from app.services.document_service import (
    create_document,
    create_document_with_chunks,
    delete_document,
)


def assert_persisted_slice_invariant(document: Document) -> None:
    assert document.extracted_text is not None
    for chunk in document.chunks:
        assert (
            document.extracted_text[
                chunk.character_start : chunk.character_end
            ]
            == chunk.chunk_text
        )


def test_normal_document_creates_document_and_chunks(
    db_session,
    test_user,
) -> None:
    text = "Introduction paragraph.\n\n" + ("Body sentence. " * 200)

    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="sample.txt",
        file_path="stored-sample.txt",
        extracted_text=text,
    )

    assert document.id is not None
    assert len(document.chunks) == len(build_chunks(document.extracted_text))
    assert len(document.chunks) > 0
    assert_persisted_slice_invariant(document)


def test_persisted_extracted_text_is_normalized(
    db_session,
    test_user,
) -> None:
    raw_text = "Line one\r\nLine two\r\n\r\nLine three"

    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="crlf.txt",
        file_path="stored-crlf.txt",
        extracted_text=raw_text,
    )

    assert document.extracted_text is not None
    assert "\r" not in document.extracted_text
    assert document.extracted_text == "Line one\nLine two\n\nLine three"
    assert_persisted_slice_invariant(document)


def test_crlf_offsets_remain_valid(db_session, test_user) -> None:
    raw_text = ("Section A\r\n\r\n" + "word " * 300).strip()

    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="crlf-long.txt",
        file_path="stored-crlf-long.txt",
        extracted_text=raw_text,
    )

    assert document.extracted_text is not None
    assert "\r" not in document.extracted_text
    assert len(document.chunks) > 0
    assert_persisted_slice_invariant(document)


def test_whitespace_only_text_creates_document_with_zero_chunks(
    db_session,
    test_user,
) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="blank.txt",
        file_path="stored-blank.txt",
        extracted_text="   \n\t  \r\n  ",
    )

    assert document.id is not None
    assert document.extracted_text == "   \n\t  \n  "
    assert document.chunks == []


def test_empty_extracted_text_creates_document_with_zero_chunks(
    db_session,
    test_user,
) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="empty.txt",
        file_path="stored-empty.txt",
        extracted_text="",
    )

    assert document.id is not None
    assert document.extracted_text == ""
    assert document.chunks == []


def test_chunk_indexes_are_sequential(db_session, test_user) -> None:
    text = ("paragraph\n\n" * 300).strip()

    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="indexed.txt",
        file_path="stored-indexed.txt",
        extracted_text=text,
    )

    indexes = [chunk.chunk_index for chunk in document.chunks]
    assert indexes == list(range(len(document.chunks)))
    assert len(set(indexes)) == len(indexes)


def test_token_count_is_null_for_all_chunks(db_session, test_user) -> None:
    text = "Chunked content " * 200

    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="tokens.txt",
        file_path="stored-tokens.txt",
        extracted_text=text,
    )

    assert len(document.chunks) > 0
    for chunk in document.chunks:
        assert chunk.token_count is None

    rows = (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .all()
    )
    assert len(rows) == len(document.chunks)
    for row in rows:
        assert row.token_count is None


def test_persistence_failure_leaves_no_durable_rows(
    db_session,
    test_user,
) -> None:
    with patch.object(
        db_session,
        "commit",
        side_effect=SQLAlchemyError("simulated commit failure"),
    ):
        with pytest.raises(SQLAlchemyError):
            create_document_with_chunks(
                db_session,
                user_id=test_user.id,
                filename="fail.txt",
                file_path="stored-fail.txt",
                extracted_text="Failure path content.",
            )

    db_session.rollback()

    assert db_session.query(Document).count() == 0
    assert db_session.query(DocumentChunk).count() == 0


def test_document_deletion_cascades_to_chunks(db_session, test_user) -> None:
    document = create_document_with_chunks(
        db_session,
        user_id=test_user.id,
        filename="delete-me.txt",
        file_path="stored-delete-me.txt",
        extracted_text="Delete cascade " * 200,
    )

    document_id = document.id
    chunk_count = len(document.chunks)
    assert chunk_count > 0

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


def test_legacy_document_without_chunks_remains_valid(
    db_session,
    test_user,
) -> None:
    document = create_document(
        db_session,
        user_id=test_user.id,
        filename="legacy.txt",
        file_path="stored-legacy.txt",
        extracted_text="Legacy document without chunk rows.",
    )

    db_session.refresh(document)
    assert document.id is not None
    assert document.chunks == []

    loaded = (
        db_session.query(Document)
        .filter(Document.id == document.id)
        .first()
    )
    assert loaded is not None
    assert loaded.extracted_text == "Legacy document without chunk rows."
