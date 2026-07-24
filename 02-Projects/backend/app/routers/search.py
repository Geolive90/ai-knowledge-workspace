from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import (
    get_current_user,
    get_db,
    get_retrieval_service_dependency,
)
from app.models.user import User
from app.schemas.search import SearchHitResponse, SearchRequest, SearchResponse
from app.services.retrieval.exceptions import (
    RetrievalEmbeddingError,
    RetrievalError,
    RetrievalNotFoundError,
    RetrievalValidationError,
    RetrievalVectorStoreError,
)
from app.services.retrieval.service import RetrievalService

router = APIRouter(
    tags=["Search"],
)


@router.post("/search", response_model=SearchResponse)
def search_documents(
    body: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    retrieval_service: RetrievalService = Depends(get_retrieval_service_dependency),
):
    try:
        result = retrieval_service.search(
            db,
            user_id=current_user.id,
            query=body.query,
            top_k=body.top_k,
            document_id=body.document_id,
        )
    except RetrievalValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except RetrievalNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from error
    except RetrievalEmbeddingError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search could not be completed.",
        ) from error
    except RetrievalVectorStoreError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search could not be completed.",
        ) from error
    except RetrievalError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search could not be completed.",
        ) from error

    return SearchResponse(
        query=result.query,
        top_k=result.top_k,
        results=[
            SearchHitResponse(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                document_filename=hit.document_filename,
                chunk_index=hit.chunk_index,
                chunk_text=hit.chunk_text,
                score=hit.score,
            )
            for hit in result.results
        ],
    )
