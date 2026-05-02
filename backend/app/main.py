from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .routes import tasks, family_members, responsibilities, uploads, lists, items, calendar_events, integrations, app_settings, calendars, sections, meal_slot_types, meal_entries, plumbing_test
from app.auth import router as auth_router

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))

# Ensure uploads directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _initialize_auth_config() -> None:
    """Lifespan startup hook for the M3 auth subsystem.

    In production (``APP_ENV=production``), fail closed: any
    :class:`AuthConfigError` propagates and crashes startup — Fly's
    restart loop will keep the deploy unhealthy until secrets are fixed.

    In dev / local docker, try to load; if env vars are missing or
    invalid, leave auth unconfigured. Auth endpoints will surface
    :class:`AuthConfigError` at call time (other routes work fine), so a
    contributor who hasn't set ``JWT_SECRET_KEY`` / ``HOUSEHOLD_ACCESS_KEY``
    can still run the existing app.
    """
    from app.auth.config import AuthConfigError, configure, load_from_env

    if os.getenv("APP_ENV") == "production":
        configure(load_from_env())
        return

    try:
        configure(load_from_env())
    except AuthConfigError:
        # Dev: contributor hasn't set auth env vars yet. Auth endpoints
        # will surface a clear error if hit; other routes are unaffected.
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    _initialize_auth_config()
    yield


app = FastAPI(title="Task & Recipe API", lifespan=lifespan)


def _parse_cors_origins(raw: str | None, app_env: str | None = None) -> list[str]:
    """Parse CORS_ALLOW_ORIGINS env var (comma-separated). Falls back to the
    default localhost dev servers when unset. Empty entries are dropped so a
    trailing comma in the env var doesn't produce an empty-string origin.

    In production (APP_ENV=production), an unset or empty CORS_ALLOW_ORIGINS
    raises RuntimeError at import time. Without this guard, a missing-secret
    deploy returns 200 from /healthz but rejects every cross-origin XHR — the
    failure mode is invisible at the edge but total at the app layer."""
    if app_env == "production":
        origins = [o.strip() for o in (raw or "").split(",") if o.strip()]
        if not origins:
            raise RuntimeError(
                "CORS_ALLOW_ORIGINS must be set when APP_ENV=production"
            )
        return origins

    _DEFAULT = ["http://localhost:5173", "http://localhost:3000"]
    source = raw if raw is not None else ",".join(_DEFAULT)
    return [o.strip() for o in source.split(",") if o.strip()]


# Env-driven so the visual-regression test stack can inject
# `http://frontend-preview:4173` without changing prod config. Prod behavior is
# unchanged when CORS_ALLOW_ORIGINS is unset.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(
        os.getenv("CORS_ALLOW_ORIGINS"),
        os.getenv("APP_ENV"),
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)


# Production host gate — reject direct Fly-hostname traffic for any
# non-/healthz path. Cloudflare Access + the /auth/* WAF rule are
# load-bearing through M5; if a caller can hit *.fly.dev directly, both
# are bypassed (Adversarial review run 2). The gate is a no-op outside
# production so dev / test can continue to use arbitrary Host headers.
@app.middleware("http")
async def production_host_gate(request: Request, call_next):
    if os.getenv("APP_ENV") != "production":
        return await call_next(request)

    # /healthz must remain reachable for Fly's TCP health checks.
    if request.url.path == "/healthz":
        return await call_next(request)

    allowed = os.getenv("PUBLIC_API_HOST", "").strip().lower()
    # Strip port; Host headers may carry one (e.g. ``api.mealy.dev:443``).
    incoming = request.headers.get("host", "").strip().lower().split(":")[0]
    if not allowed or incoming != allowed:
        return JSONResponse(
            status_code=421,
            content={"detail": "host_not_allowed"},
        )
    return await call_next(request)

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
app.include_router(plumbing_test.router)
app.include_router(auth_router)

# Mount static files AFTER routers so that specific router paths (e.g.
# POST /uploads/item-icon) take precedence over the catch-all static mount.
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    return {"message": "To-Do + Recipe API is running!"}


@app.get("/healthz")
async def healthz():
    # Shallow probe by design: deep DB/Redis checks would turn a transient
    # dep flap into total user-facing downtime when min_machines_running=1.
    return {"status": "ok"}
