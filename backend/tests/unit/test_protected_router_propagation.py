"""Structural enumeration of `app.routes` against the production app instance.

This test is the structural guard that makes the wrapping `protected`
APIRouter pattern's value proposition real. A future contributor adding
a router via ``app.include_router(X)`` instead of
``protected.include_router(X)`` causes this test to fail with the path
name in the error, not silently ship as a public surface.

Three assertions:

1. Every non-allowlisted ``APIRoute`` has ``get_current_user`` somewhere
   in its dependency tree.
2. The only public ``Mount`` is ``/uploads`` (the StaticFiles mount, gated
   in M7). Protected upload APIs (``/upload/*`` and ``/uploads/item-icon``)
   are ``APIRoute`` objects, not mounts, so they are NOT allowlisted here
   — they fail the first assertion if they ever lose ``get_current_user``.
3. ``/docs``, ``/redoc``, and ``/openapi.json`` are absent (FastAPI's
   built-in routes are registered by ``FastAPI(...)`` itself and bypass
   router-level dependencies; PR1 disables them via
   ``docs_url=None, redoc_url=None, openapi_url=None``).
"""

from __future__ import annotations

from app.auth.dependencies import get_current_user
from app.main import app
from fastapi.routing import APIRoute
from starlette.routing import Mount

# Public APIRoute prefixes (auth-portal endpoints only after PR2).
PUBLIC_PREFIXES = ("/auth/",)
# Public APIRoute exact paths (root sanity + healthz).
PUBLIC_EXACT = {"/", "/healthz"}
# The only public StaticFiles mount. /uploads is gated in M7.
PUBLIC_STATIC_MOUNTS = {"/uploads"}
# FastAPI auto-docs/schema must be disabled, not allowlisted.
FORBIDDEN_PUBLIC_DOCS = {"/docs", "/redoc", "/openapi.json"}


def _is_public(path: str) -> bool:
    return path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIXES)


def _has_dep(deps, target) -> bool:
    """Recursive walk of FastAPI's dependant tree looking for `target`."""
    for d in deps:
        if d.call is target:
            return True
        if _has_dep(d.dependencies, target):
            return True
    return False


def test_every_protected_route_requires_auth():
    """Every non-allowlisted APIRoute must have get_current_user in its dep tree."""
    # Negative control: an empty dep list must not falsely report
    # `get_current_user` present. Catches a `_has_dep` regression that
    # accidentally short-circuits to True.
    assert _has_dep([], get_current_user) is False

    failures = []
    protected_count = 0
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if _is_public(route.path):
            continue
        if not _has_dep(route.dependant.dependencies, get_current_user):
            failures.append(route.path)
        else:
            protected_count += 1
    assert not failures, f"Routes missing auth: {failures}"
    # Positive minimum: 14 protected routers register dozens of routes.
    # If a future FastAPI internal refactor changes `route.dependant.dependencies`
    # to be empty (renamed attribute, alternative shape), every route would
    # silently look "protected" because `failures` stays empty. This guard
    # forces the test to fail vacuously instead of passing vacuously.
    assert protected_count >= 14, (
        f"Expected at least 14 protected routes; counted {protected_count}. "
        "This usually means FastAPI's dep-tree shape changed and `_has_dep` "
        "is no longer finding `get_current_user` even though routes are wired."
    )


def test_only_expected_static_mounts_are_public():
    """Only `/uploads` may be a public Mount. Anything else is a regression."""
    mounts = [route.path for route in app.routes if isinstance(route, Mount)]
    unexpected = sorted(set(mounts) - PUBLIC_STATIC_MOUNTS)
    assert not unexpected, f"Unexpected public mounts: {unexpected}"


def test_fastapi_docs_are_not_public():
    """FastAPI's built-in /docs, /redoc, /openapi.json must be disabled."""
    paths = {getattr(route, "path", None) for route in app.routes}
    assert paths.isdisjoint(
        FORBIDDEN_PUBLIC_DOCS
    ), f"Forbidden public docs/schema present: {paths & FORBIDDEN_PUBLIC_DOCS}"
