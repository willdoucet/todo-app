from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .routes import tasks, family_members, responsibilities, uploads, lists, items, calendar_events, integrations, app_settings, calendars, sections, meal_slot_types, meal_entries

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))

# Ensure uploads directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Task & Recipe API")


def _parse_cors_origins(raw: str | None) -> list[str]:
    """Parse CORS_ALLOW_ORIGINS env var (comma-separated). Falls back to the
    default localhost dev servers when unset. Empty entries are dropped so a
    trailing comma in the env var doesn't produce an empty-string origin."""
    _DEFAULT = ["http://localhost:5173", "http://localhost:3000"]
    source = raw if raw is not None else ",".join(_DEFAULT)
    return [o.strip() for o in source.split(",") if o.strip()]


# Env-driven so the visual-regression test stack can inject
# `http://frontend-preview:4173` without changing prod config. Prod behavior is
# unchanged when CORS_ALLOW_ORIGINS is unset.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(os.getenv("CORS_ALLOW_ORIGINS")),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers BEFORE mounting StaticFiles so the specific
# POST /uploads/item-icon route wins over the static mount, which would
# otherwise intercept all /uploads/* requests and return 405 for non-GET.
app.include_router(tasks.router)
app.include_router(family_members.router)
app.include_router(responsibilities.router)
app.include_router(uploads.router)
app.include_router(uploads.item_icon_router)
app.include_router(lists.router)
app.include_router(items.router)
app.include_router(calendar_events.router)
app.include_router(integrations.router)
app.include_router(app_settings.router)
app.include_router(calendars.router)
app.include_router(sections.router)
app.include_router(meal_slot_types.router)
app.include_router(meal_entries.router)

# Mount static files AFTER routers so that specific router paths (e.g.
# POST /uploads/item-icon) take precedence over the catch-all static mount.
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    return {"message": "To-Do + Recipe API is running!"}
