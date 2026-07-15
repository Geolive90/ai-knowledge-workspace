from fastapi import APIRouter

from app.routers.auth import router as auth_router


router = APIRouter()

router.include_router(auth_router)


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "AI Knowledge Workspace API is running."
    }