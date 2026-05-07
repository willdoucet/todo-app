from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .routes import tasks, family_members, responsibilities, uploads, lists, items, calendar_events, integrations, app_settings, calendars, sections, meal_slot_types, meal_entries, plumbing_test
from app.auth import get_current_user, router as auth_router

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
    :class:`AuthConfigError` at call time. After M5 PR1, every
    protected route also surfaces 500 because the wrapping
    ``protected`` APIRouter calls :func:`get_current_user`, which
    decodes a JWT against ``get_settings()``. We log a clear startup
    warning so a contributor who forgot the new env vars sees the
    correct diagnosis instead of debugging a generic 500.
    """
    import logging
    import sys

    from app.auth.config import AuthConfigError, configure, load_from_env

    if os.getenv("APP_ENV") == "production":
        configure(load_from_env())
        return

    try:
        configure(load_from_env())
    except AuthConfigError as exc:
        # M5: previously this was a silent pass. Post-PR1, every protected
        # route returns 500 (auth_config not initialized) without a clear
        # signal. Log at WARNING so docker-compose logs and `uv run` both
        # surface the cause on the first request.
        logging.getLogger(__name__).warning(
            "M5 auth bootstrap: auth config not loaded (%s). "
            "Protected routes will fail until JWT_SECRET_KEY and "
            "HOUSEHOLD_ACCESS_KEY are set in the environment. "
            "Auth endpoints (/auth/*) will return AuthConfigError on call.",
            exc,
        )
        # Belt-and-suspenders for non-stderr-buffered runtimes.
        print(
            "[M5 auth bootstrap warning] Set JWT_SECRET_KEY and "
            "HOUSEHOLD_ACCESS_KEY in your .env to enable protected routes.",
            file=sys.stderr,
            flush=True,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _initialize_auth_config()
    yield


# M5 PR1 — disable FastAPI's automatic /docs, /redoc, /openapi.json. These
# routes are registered directly by FastAPI(...) and bypass router-level
# dependencies — the wrapping `protected` APIRouter cannot gate them.
# After PR2 removes Cloudflare Access, leaving them on would expose the
# full API schema to the open internet.
app = FastAPI(
    title="Task & Recipe API",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


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

# M5 PR1 — wrapping `protected` APIRouter. ONE place to audit "is this
# auth-gated?". A new router added on `protected` is auth-gated
# automatically. A new router added on `app` directly is public — grep
# for `app.include_router` in this file to audit the public surface.
#
# Include routers BEFORE mounting StaticFiles so the specific
# POST /uploads/item-icon route wins over the static mount, which would
# otherwise intercept all /uploads/* requests and return 405 for non-GET.
protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(tasks.router)
protected.include_router(family_members.router)
protected.include_router(responsibilities.router)
# uploads.router is the legacy /upload/* (singular) protected API surface.
protected.include_router(uploads.router)
# uploads.item_icon_router is a distinct router in the same module —
# POST /uploads/item-icon. Protected. NOT the same as the public
# StaticFiles mount on /uploads/* below.
protected.include_router(uploads.item_icon_router)
protected.include_router(lists.router)
protected.include_router(items.router)
protected.include_router(calendar_events.router)
protected.include_router(integrations.router)
protected.include_router(app_settings.router)
protected.include_router(calendars.router)
protected.include_router(sections.router)
protected.include_router(meal_slot_types.router)
protected.include_router(meal_entries.router)
app.include_router(protected)

# Public surface — registered directly on `app`, NOT on `protected`.
app.include_router(auth_router)
app.include_router(plumbing_test.router)  # Removed in M5 PR2.

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
