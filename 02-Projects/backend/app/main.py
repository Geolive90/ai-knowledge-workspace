from fastapi import FastAPI
from app.api.router import router

app = FastAPI(
    title="AI Knowledge Workspace",
    version="1.0.0",
    description="Production-ready AI Knowledge Workspace API"
)

app.include_router(router)