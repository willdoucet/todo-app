"""HTTP layer for /auth/*.

Each handler:
  1. Calls the service layer for business logic.
  2. Translates :class:`AuthSuccess` → access_token body + Set-Cookie.
  3. Emits exactly ONE structured JSON log line at completion (success
     OR failure) via :func:`emit_log_line`.

``/auth/logout`` does NOT use ``Depends(get_current_user)`` because
FastAPI dependency failures bypass the handler body — we'd never get to
emit the failure log line. The route calls :func:`validate_bearer`
directly in a try/except instead.
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import schemas, service, tokens
from app.auth.dependencies import validate_bearer
from app.auth.logging_utils import emit_log_line
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "__Host-refresh"
# Same-origin SPA on Vercel — no email-link sign-in flow needs the cookie
# to survive cross-origin top-level nav, so Strict is safe and stricter
# than the M2 plumbing default. M3 originally settled on "lax"; bumped
# pre-M4 because the frontend silent-refresh flow runs same-origin.
REFRESH_COOKIE_SAMESITE = "strict"


def _set_refresh_cookie(response: Response, plaintext: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=plaintext,
        httponly=True,
        secure=True,
        samesite=REFRESH_COOKIE_SAMESITE,
        path="/",
        # No domain — __Host- prefix forbids it; host-only is exactly
        # what we want (cookie binds to api.<domain> only).
        max_age=tokens.REFRESH_TOKEN_TTL_DAYS * 24 * 3600,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear with the EXACT attributes the original was set with so
    browsers actually delete it (Adversarial review run 2)."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value="",
        httponly=True,
        secure=True,
        samesite=REFRESH_COOKIE_SAMESITE,
        path="/",
        max_age=0,
    )


def _log_failed(
    request: Request, event: str, exc: HTTPException, start: float
) -> None:
    reason = getattr(exc, "log_reason", "unknown")
    emit_log_line(
        request,
        event=event,
        outcome="failed",
        reason=reason,
        user_id=None,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )


def _log_success(
    request: Request,
    event: str,
    user_id: Optional[int],
    start: float,
    *,
    reason: Optional[str] = None,
) -> None:
    emit_log_line(
        request,
        event=event,
        outcome="success",
        reason=reason,
        user_id=user_id,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )


# =============================================================================
# POST /auth/register
# =============================================================================

@router.post("/register", response_model=schemas.AccessTokenOut)
async def register(
    payload: schemas.RegisterIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    start = time.perf_counter()
    try:
        result = await service.register(
            db,
            email=payload.email,
            password=payload.password,
            access_key=payload.access_key,
        )
    except HTTPException as exc:
        _log_failed(request, "auth.register", exc, start)
        raise
    _set_refresh_cookie(response, result.refresh_plaintext)
    _log_success(request, "auth.register", result.user_id, start)
    return schemas.AccessTokenOut(access_token=result.access_token)


# =============================================================================
# POST /auth/login
# =============================================================================

@router.post("/login", response_model=schemas.AccessTokenOut)
async def login(
    payload: schemas.LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_cookie: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    start = time.perf_counter()
    try:
        result = await service.login(
            db,
            email=payload.email,
            password=payload.password,
            incoming_refresh_cookie=refresh_cookie,
        )
    except HTTPException as exc:
        _log_failed(request, "auth.login", exc, start)
        raise
    _set_refresh_cookie(response, result.refresh_plaintext)
    _log_success(request, "auth.login", result.user_id, start)
    return schemas.AccessTokenOut(access_token=result.access_token)


# =============================================================================
# POST /auth/refresh
# =============================================================================

@router.post("/refresh", response_model=schemas.AccessTokenOut)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_cookie: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    start = time.perf_counter()
    try:
        outcome = await service.refresh(db, refresh_cookie)
    except HTTPException as exc:
        _log_failed(request, "auth.refresh", exc, start)
        raise

    # Case A → new cookie. Case B → no cookie (browser already has it).
    if outcome.new_refresh_plaintext is not None:
        _set_refresh_cookie(response, outcome.new_refresh_plaintext)

    _log_success(
        request,
        "auth.refresh",
        outcome.user_id,
        start,
        reason=outcome.reason_log,
    )
    return schemas.AccessTokenOut(access_token=outcome.access_token)


# =============================================================================
# POST /auth/logout
# =============================================================================

@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    start = time.perf_counter()
    try:
        # Full bearer validation BEFORE any mutation. A stale token after
        # password rotation must 401 and must not revoke any newly issued
        # valid refresh token (Adversarial review run 2).
        user = await validate_bearer(authorization, db)
    except HTTPException as exc:
        _log_failed(request, "auth.logout", exc, start)
        raise

    await service.logout(db, user.id)
    _clear_refresh_cookie(response)
    _log_success(request, "auth.logout", user.id, start)
    response.status_code = 204
    return None


# =============================================================================
# GET /auth/status
# =============================================================================

@router.get("/status", response_model=schemas.AuthStatusOut)
async def status_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public — no auth. Drives the M4 portal's "Create account" toggle."""
    start = time.perf_counter()
    exists = await service.auth_status(db)
    _log_success(
        request, "auth.status", user_id=None, start=start
    )
    return schemas.AuthStatusOut(account_exists=exists)
