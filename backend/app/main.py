from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import hmac
import os
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .routes import tasks, family_members, responsibilities, uploads, lists, items, calendar_events, integrations, app_settings, calendars, sections, meal_slot_types, meal_entries, media
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


def _initialize_storage_backend() -> None:
    """Lifespan startup hook for the M7 storage layer.

    In production, build the configured backend once so a misconfigured deploy
    CRASHES AT BOOT instead of degrading silently. `get_storage()` is otherwise
    lazy: with `STORAGE_BACKEND=r2` (backend/fly.toml) but a MISSING `R2_*`
    secret, the app would pass `release_command`, pass `/healthz`, take
    traffic, and only then 503 every image and 500 every upload — invisible at
    the edge, total at the app layer. Scope: this catches an absent variable
    (`KeyError` at client construction). A present-but-rotated credential is
    NOT caught — building a boto3 client makes no network call, and a boot-time
    bucket probe would make every deploy depend on R2 being up. The runbook's
    smoke upload is the check for that case. That is the same failure mode
    `_parse_cors_origins` already refuses to allow, and REVIEW_CHECKLIST →
    FastAPI → Secrets & config requires ("Lifespan fails closed in production
    when a required secret is missing"). A boot crash leaves the previous Fly
    image serving, which is the correct outcome.

    Outside production this is a no-op: dev/test default to `local`, and the
    R2 client must never be constructed there.
    """
    if os.getenv("APP_ENV") != "production":
        return

    from .storage import get_storage

    get_storage()


_ORIGIN_VERIFY_HEADER = "x-origin-verify"
_ORIGIN_VERIFY_MIN_LENGTH = 32


def _initialize_origin_verify() -> None:
    """Lifespan startup hook for the Cloudflare origin lock.

    In production, `production_host_gate` admits a request only when its
    `X-Origin-Verify` header matches `ORIGIN_VERIFY_SECRET`, the value a
    Cloudflare Transform Rule adds (`infra/cloudflare-state.md`). With the
    secret missing the gate fails closed per request: `/healthz` stays green,
    Fly keeps the machine, and every real request 421s. Crash the boot instead
    so the deploy fails and the previous image keeps serving. The error names
    the variable, never its value.
    """
    if os.getenv("APP_ENV") != "production":
        return

    secret = os.getenv("ORIGIN_VERIFY_SECRET", "").strip()
    if len(secret) < _ORIGIN_VERIFY_MIN_LENGTH:
        raise RuntimeError(
            f"ORIGIN_VERIFY_SECRET must be set to at least "
            f"{_ORIGIN_VERIFY_MIN_LENGTH} characters when APP_ENV=production"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _initialize_auth_config()
    _initialize_storage_backend()
    _initialize_origin_verify()
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


def _origin_verified(request: Request) -> bool:
    expected = os.getenv("ORIGIN_VERIFY_SECRET", "").strip()
    # An unset secret must never match an absent header ("" == "").
    if not expected:
        return False
    presented = request.headers.get(_ORIGIN_VERIFY_HEADER, "")
    # Compare bytes: compare_digest raises TypeError on non-ASCII str, which
    # would turn a forged header into a 500 instead of a 421.
    return hmac.compare_digest(presented.encode(), expected.encode())


# Production host gate — admit a non-/healthz request only if it came through
# Cloudflare, whose /auth/* WAF rate limit is the only brute-force control on
# login (infra/cloudflare-state.md). Two checks, both required:
#
# 1. Host must be PUBLIC_API_HOST. Turns away *.fly.dev traffic (Adversarial
#    review run 2), but the client writes the Host header: Fly holds a cert
#    for api.mealy.dev, so `curl --resolve api.mealy.dev:443:<fly-ip>` passed
#    this check alone and skipped Cloudflare entirely (found 2026-09-11).
# 2. X-Origin-Verify must match ORIGIN_VERIFY_SECRET, which a Cloudflare
#    Transform Rule sets on every request for the API host. Only the edge
#    can add it, so it proves the request came through Cloudflare.
#
# Both failures return the same 421 body. The gate is a no-op outside
# production so dev / test can continue to use arbitrary Host headers.
@app.middleware("http")
async def production_host_gate(request: Request, call_next):
    if os.getenv("APP_ENV") != "production":
        return await call_next(request)

    # /healthz must remain reachable for Fly's TCP health checks. Match on
    # scope["path"] — the value the router dispatches on — NOT request.url.path,
    # which Starlette builds from the client's Host header: a Host of
    # "api.mealy.dev/healthz?" makes request.url.path read "/healthz" while the
    # request still routes to /auth/login, skipping the gate entirely.
    if request.scope["path"] == "/healthz":
        return await call_next(request)

    allowed = os.getenv("PUBLIC_API_HOST", "").strip().lower()
    # Strip port; Host headers may carry one (e.g. ``api.mealy.dev:443``).
    incoming = request.headers.get("host", "").strip().lower().split(":")[0]
    if not allowed or incoming != allowed or not _origin_verified(request):
        return JSONResponse(
            status_code=421,
            content={"detail": "host_not_allowed"},
        )
    return await call_next(request)

# M5 PR1 — wrapping `protected` APIRouter. ONE place to audit "is this
# auth-gated?". A new router added on `protected` is auth-gated
# automatically. A new router added on `app` directly is public — grep
# for `app.include_router` in this file to audit the public surface.
protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(tasks.router)
protected.include_router(family_members.router)
protected.include_router(responsibilities.router)
# uploads.router is the legacy /upload/* (singular) protected API surface.
protected.include_router(uploads.router)
# uploads.item_icon_router is a distinct router in the same module —
# POST /uploads/item-icon. Protected.
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

# M7 PR2 — GET /uploads/{key} replaces the public static mount that used to
# live here. That mount bypassed `protected` entirely (a router dependency
# cannot gate a mount), leaving private family photos gated only by
# Cloudflare Access at the edge — the one reason CF Access Application 1 had
# to survive since M5. It is gone; no public static surface remains.
#
# Registered on `app`, NOT on `protected`, because `<img>` cannot send an
# Authorization header. The route carries its own cookie dependency
# (`require_media_session`), and
# `tests/unit/test_protected_router_propagation.py` asserts it is the ONLY
# non-`protected` API route outside /auth/* and that it really carries it.
#
# Registered AFTER `protected` so POST /uploads/item-icon keeps its exact-path
# match; Starlette falls through to this catch-all only when no earlier route
# matches both path and method.
app.include_router(media.router)


@app.get("/")
async def root():
    return {"message": "To-Do + Recipe API is running!"}


@app.get("/healthz")
async def healthz():
    # Shallow probe by design: deep DB/Redis checks would turn a transient
    # dep flap into total user-facing downtime when min_machines_running=1.
    return {"status": "ok"}
