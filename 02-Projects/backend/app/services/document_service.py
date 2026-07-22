from typing import Optional

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking_service import build_chunks, normalize_line_endings


def get_documents_for_user(db: Session, user_id: int) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .all()
    )


def get_document_for_user(
    db: Session,
    document_id: int,
    user_id: int,
) -> Optional[Document]:
    return (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )


def create_document(
    db: Session,
    user_id: int,
    filename: str,
    file_path: str,
    extracted_text: str,
) -> Document:
    document = Document(
        user_id=user_id,
        filename=filename,
        file_path=file_path,
        extracted_text=extracted_text,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def create_document_with_chunks(
    db: Session,
    user_id: int,
    filename: str,
    file_path: str,
    extracted_text: str,
) -> Document:
    canonical_text = normalize_line_endings(extracted_text)
    chunk_records = build_chunks(canonical_text)

    document = Document(
        user_id=user_id,
        filename=filename,
        file_path=file_path,
        extracted_text=canonical_text,
    )

    for record in chunk_records:
        document.chunks.append(
            DocumentChunk(
                chunk_index=record.chunk_index,
                chunk_text=record.chunk_text,
                character_start=record.character_start,
                character_end=record.character_end,
                token_count=record.token_count,
            )
        )

    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, document: Document) -> None:
    db.delete(document)
    db.commit()
