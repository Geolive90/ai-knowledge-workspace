from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    create_document_with_chunks,
    delete_document,
    get_document_for_user,
    get_documents_for_user,
)
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


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    canonical_text = document.extracted_text or ""

    return {
        "message": "Document uploaded and text extracted successfully.",
        "document_id": document.id,
        "filename": document.filename,
        "extracted_character_count": len(canonical_text),
        "text_preview": canonical_text[:300],
    }


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
):
    document = _get_owned_document_or_404(db, document_id, current_user.id)

    delete_stored_file(document.file_path)
    delete_document(db, document)

    return {
        "message": "Document deleted successfully."
    }
