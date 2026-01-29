from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .routes import tasks, family_members, responsibilities

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

app.include_router(tasks.router)
app.include_router(family_members.router)
app.include_router(responsibilities.router)


@app.get("/")
async def root():
    return {"message": "To-Do + Recipe API is running!"}
