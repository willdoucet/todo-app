from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .routes import todos

app = FastAPI(title="To-Do & Recipe API")

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

app.include_router(todos.router)


@app.get("/")
async def root():
    return {"message": "To-Do + Recipe API is running!"}


# Later: include routers
# from .routes import todos, recipes
# app.include_router(todos.router, prefix="/todos")
# app.include_router(recipes.router, prefix="/recipes")
