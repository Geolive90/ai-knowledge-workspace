from sqlalchemy.orm import Session

from app.models.document import Document


def get_all_documents(db: Session):
    return db.query(Document).all()


def get_document_by_id(db: Session, document_id: int):
    return (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )


def delete_document(db: Session, document: Document):
    db.delete(document)
    db.commit()