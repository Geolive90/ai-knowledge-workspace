from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    delete_document,
    get_all_documents,
    get_document_by_id,
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

    document = Document(
        filename=original_filename,
        file_path=stored_filename,
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()
        delete_stored_file(stored_filename)

        raise HTTPException(
            status_code=500,
            detail="The document could not be saved.",
        )

    return {
        "message": "Document uploaded and text extracted successfully.",
        "document_id": document.id,
        "filename": document.filename,
        "extracted_character_count": len(extracted_text),
        "text_preview": extracted_text[:300],
    }


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_all_documents(db)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_by_id(db, document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return document


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_by_id(db, document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

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
    document = get_document_by_id(db, document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    delete_stored_file(document.file_path)
    delete_document(db, document)

    return {
        "message": "Document deleted successfully."
    }