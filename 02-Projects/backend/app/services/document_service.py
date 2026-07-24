from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking_service import build_chunks, normalize_line_endings


@dataclass(frozen=True)
class IndexingChunkRecord:
    chunk_id: int
    chunk_index: int
    chunk_text: str


@dataclass(frozen=True)
class SearchableChunkRecord:
    chunk_id: int
    document_id: int
    document_filename: str
    chunk_index: int
    chunk_text: str


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


def get_owned_document_with_ordered_chunks(
    db: Session,
    document_id: int,
    user_id: int,
) -> Optional[Document]:
    return (
        db.query(Document)
        .options(joinedload(Document.chunks))
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )


def get_indexing_chunk_records(document: Document) -> list[IndexingChunkRecord]:
    ordered_chunks = sorted(document.chunks, key=lambda chunk: chunk.chunk_index)
    return [
        IndexingChunkRecord(
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.chunk_text,
        )
        for chunk in ordered_chunks
    ]


def get_document_chunk_ids(db: Session, document_id: int) -> list[int]:
    rows = (
        db.query(DocumentChunk.id)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    return [row[0] for row in rows]


def get_indexed_searchable_chunks_by_ids(
    db: Session,
    *,
    user_id: int,
    chunk_ids: list[int],
    document_id: int | None = None,
) -> list[SearchableChunkRecord]:
    if not chunk_ids:
        return []

    query = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            Document.user_id == user_id,
            Document.indexing_status == "indexed",
            DocumentChunk.id.in_(chunk_ids),
        )
    )

    if document_id is not None:
        query = query.filter(Document.id == document_id)

    rows = query.all()
    records = [
        SearchableChunkRecord(
            chunk_id=chunk.id,
            document_id=document.id,
            document_filename=document.filename,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.chunk_text,
        )
        for chunk, document in rows
    ]
    order = {chunk_id: index for index, chunk_id in enumerate(chunk_ids)}
    records.sort(key=lambda record: order[record.chunk_id])
    return records


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
