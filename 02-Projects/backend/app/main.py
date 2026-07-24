from fastapi import FastAPI

from app.routers import auth, health, users, documents, search

app = FastAPI(
    title="AI Knowledge Workspace API"
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(search.router)

@app.get("/")
def root():
    return {
        "message": "AI Knowledge Workspace API is running."
    }