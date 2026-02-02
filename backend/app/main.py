from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .routes import tasks, family_members, responsibilities, uploads, lists

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))

# Ensure uploads directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Task & Recipe API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],  # Frontend dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.include_router(tasks.router)
app.include_router(family_members.router)
app.include_router(responsibilities.router)
app.include_router(uploads.router)
app.include_router(lists.router)


@app.get("/")
async def root():
    return {"message": "To-Do + Recipe API is running!"}
