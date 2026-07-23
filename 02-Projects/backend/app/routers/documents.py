import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import (
    get_current_user,
    get_db,
    get_indexing_service_dependency,
)
from app.models.user import User
from app.schemas.document import DocumentResponse, IndexingOutcomeResponse, IndexingRetryInfo
from app.services.document_service import (
    create_document_with_chunks,
    delete_document,
    get_document_for_user,
    get_documents_for_user,
    get_indexing_chunk_records,
    get_owned_document_with_ordered_chunks,
)
from app.services.indexing.exceptions import (
    IndexingConflictError,
    IndexingError,
    IndexingNotFoundError,
)
from app.services.indexing.result import IndexingResult
from app.services.indexing.service import INDEXING_STATUS_FAILED, IndexingService
from app.services.text_extraction_service import extract_text
from app.utils.file_handler import (
    delete_stored_file,
    get_file_path,
    save_uploaded_file,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

logger = logging.getLogger(__name__)


def _get_owned_document_or_404(
    db: Session,
    document_id: int,
    user_id: int,
):
    document = get_document_for_user(db, document_id, user_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return document


def _indexing_retry_info(document_id: int) -> IndexingRetryInfo:
    return IndexingRetryInfo(
        method="POST",
        path=f"/documents/{document_id}/index",
    )


def _indexing_outcome_from_result(result: IndexingResult) -> IndexingOutcomeResponse:
    retry = None
    if result.indexing_status == INDEXING_STATUS_FAILED:
        retry = _indexing_retry_info(result.document_id)

    return IndexingOutcomeResponse(
        indexing_status=result.indexing_status,
        chunk_count=result.chunk_count,
        vectors_indexed=result.vectors_indexed,
        indexed_at=result.indexed_at,
        indexing_error=result.indexing_error,
        retry=retry,
    )


def _run_indexing(
    db: Session,
    indexing_service: IndexingService,
    *,
    document_id: int,
    user_id: int,
    force_reindex: bool = False,
) -> IndexingResult:
    try:
        return indexing_service.index_document(
            db,
            document_id=document_id,
            user_id=user_id,
            force_reindex=force_reindex,
        )
    except IndexingNotFoundError as error:
        raise HTTPException(status_code=404, detail="Document not found.") from error
    except IndexingConflictError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error
    except IndexingError as error:
        document = get_owned_document_with_ordered_chunks(
            db,
            document_id=document_id,
            user_id=user_id,
        )
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.") from error

        chunk_records = get_indexing_chunk_records(document)
        return IndexingResult(
            document_id=document.id,
            indexing_status=document.indexing_status,
            chunk_count=len(chunk_records),
            vectors_indexed=0,
            indexed_at=document.indexed_at,
            indexing_error=document.indexing_error,
            skipped=False,
        )


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    indexing_service: IndexingService = Depends(get_indexing_service_dependency),
):
    stored_filename, original_filename = save_uploaded_file(file)
    file_path = get_file_path(stored_filename)

    try:
        extracted_text = extract_text(file_path)

    except ValueError as error:
        delete_stored_file(stored_filename)

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        delete_stored_file(stored_filename)

        raise HTTPException(
            status_code=422,
            detail="The document was uploaded, but its text could not be extracted.",
        ) from error

    try:
        document = create_document_with_chunks(
            db,
            user_id=current_user.id,
            filename=original_filename,
            file_path=stored_filename,
            extracted_text=extracted_text,
        )

    except Exception:
        db.rollback()
        delete_stored_file(stored_filename)

        raise HTTPException(
            status_code=500,
            detail="The document could not be saved.",
        )

    indexing_result = _run_indexing(
        db,
        indexing_service,
        document_id=document.id,
        user_id=current_user.id,
    )
    indexing_outcome = _indexing_outcome_from_result(indexing_result)

    canonical_text = document.extracted_text or ""
    if indexing_outcome.indexing_status == INDEXING_STATUS_FAILED:
        message = "Document uploaded successfully; indexing failed."
    else:
        message = "Document uploaded and indexed successfully."

    return {
        "message": message,
        "document_id": document.id,
        "filename": document.filename,
        "extracted_character_count": len(canonical_text),
        "text_preview": canonical_text[:300],
        **indexing_outcome.model_dump(),
    }


@router.post("/{document_id}/index", response_model=IndexingOutcomeResponse)
def index_document(
    document_id: int,
    force_reindex: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    indexing_service: IndexingService = Depends(get_indexing_service_dependency),
):
    result = _run_indexing(
        db,
        indexing_service,
        document_id=document_id,
        user_id=current_user.id,
        force_reindex=force_reindex,
    )
    return _indexing_outcome_from_result(result)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_documents_for_user(db, current_user.id)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_document_or_404(db, document_id, current_user.id)


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = _get_owned_document_or_404(db, document_id, current_user.id)

    file_path = get_file_path(document.file_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Stored file not found.",
        )

    return FileResponse(
        path=file_path,
        filename=document.filename,
        media_type="application/octet-stream",
    )


@router.delete("/{document_id}")
def remove_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    indexing_service: IndexingService = Depends(get_indexing_service_dependency),
):
    document = _get_owned_document_or_404(db, document_id, current_user.id)
    stored_file_path = document.file_path

    try:
        with indexing_service.document_lock(document.id, blocking=True):
            indexing_service.purge_document_index(db, document_id=document.id)
            delete_document(db, document)
    except IndexingConflictError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error
    except IndexingError as error:
        raise HTTPException(
            status_code=500,
            detail="Document indexing data could not be purged.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="The document could not be deleted.",
        ) from error

    try:
        delete_stored_file(stored_file_path)
    except Exception as error:
        logger.warning(
            "Stored file deletion failed for document_id=%s path=%s",
            document_id,
            stored_file_path,
            exc_info=error,
        )

    return {
        "message": "Document deleted successfully."
    }
