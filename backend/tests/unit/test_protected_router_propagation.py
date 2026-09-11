"""Structural enumeration of `app.routes` against the production app instance.

This test is the structural guard that makes the wrapping `protected`
APIRouter pattern's value proposition real. A future contributor adding
a router via ``app.include_router(X)`` instead of
``protected.include_router(X)`` causes this test to fail with the path
name in the error, not silently ship as a public surface.

Assertions:

1. Every non-allowlisted ``APIRoute`` has ``get_current_user`` somewhere
   in its dependency tree.
2. There are NO ``Mount`` objects at all. M7 PR2 deleted the ``/uploads``
   StaticFiles mount — the last public static surface, and the one thing a
   router-level dependency could not gate. Protected upload APIs
   (``/upload/*`` and ``POST /uploads/item-icon``) are ``APIRoute`` objects,
   not mounts, so they are NOT allowlisted here — they fail the first
   assertion if they ever lose ``get_current_user``.

3. ``GET /uploads/{key:path}`` is the one API route that is auth-gated by
   something OTHER than ``get_current_user``: it uses the cookie-based
   ``require_media_session`` because ``<img>`` cannot send a Bearer header.
   It is exempt from assertion 1 but has its own assertion that it really
   carries that guard — an exemption without a replacement check would be a
   hole, which is the whole failure mode this file exists to prevent.
4. ``/docs``, ``/redoc``, and ``/openapi.json`` are absent (FastAPI's
   built-in routes are registered by ``FastAPI(...)`` itself and bypass
   router-level dependencies; PR1 disables them via
   ``docs_url=None, redoc_url=None, openapi_url=None``).
"""

from __future__ import annotations

from app.auth.dependencies import get_current_user, require_media_session
from app.main import app
from fastapi.routing import APIRoute
from starlette.routing import Mount

# Public APIRoute prefixes (auth-portal endpoints only).
PUBLIC_PREFIXES = ("/auth/",)
# Public APIRoute exact paths (root sanity + healthz).
PUBLIC_EXACT = {"/", "/healthz"}
# NO public mounts remain after M7 PR2. Deliberately empty, not absent: an
# empty allowlist plus the subtraction below fails loudly the moment any mount
# reappears.
PUBLIC_STATIC_MOUNTS: set[str] = set()
# Routes gated by a cookie dependency instead of the Bearer dependency, with
# the dependency each one MUST carry. Exempt from assertion 1, checked by
# assertion 4.
COOKIE_GUARDED_ROUTES = {"/uploads/{key:path}": require_media_session}
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
        if route.path in COOKIE_GUARDED_ROUTES:
            continue  # checked by test_cookie_guarded_routes_carry_their_guard
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


def test_no_public_static_mounts_remain():
    """M7 PR2's headline structural property: there is no public static
    surface left. A `Mount` cannot be gated by a router dependency, so any
    mount reappearing here is an ungated hole by construction — and would
    re-create the exact reason CF Access Application 1 had to exist."""
    mounts = [route.path for route in app.routes if isinstance(route, Mount)]
    unexpected = sorted(set(mounts) - PUBLIC_STATIC_MOUNTS)
    assert not unexpected, f"Unexpected public mounts: {unexpected}"
    assert mounts == [], f"No mounts should remain after M7 PR2; found {mounts}"


def test_cookie_guarded_routes_carry_their_guard():
    """Assertion 4 — the counterpart to assertion 1's exemption.

    `GET /uploads/{key}` serves private family photos and is NOT on the
    `protected` router. If it ever lost `require_media_session` it would
    become a public read surface for every uploaded image, and assertion 1
    would stay green because the path is exempt. This closes that gap.
    """
    by_path = {
        route.path: route for route in app.routes if isinstance(route, APIRoute)
    }
    for path, required_dep in COOKIE_GUARDED_ROUTES.items():
        route = by_path.get(path)
        assert route is not None, f"{path} is not registered any more"
        assert _has_dep(route.dependant.dependencies, required_dep), (
            f"{path} lost its {required_dep.__name__} guard — it is not on the "
            "`protected` router, so nothing else is gating it"
        )
        # It must NOT be on `protected`: <img> cannot send a Bearer header, so
        # adding get_current_user here would 401 every image in the app.
        assert not _has_dep(route.dependant.dependencies, get_current_user), (
            f"{path} must not require a Bearer token — `<img>` cannot send one"
        )


def test_media_read_is_the_only_cookie_guarded_route():
    """A second cookie-guarded route added without updating
    COOKIE_GUARDED_ROUTES would be exempt from nothing and checked by nothing
    — so enumerate them from the app and compare."""
    found = sorted(
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        and _has_dep(route.dependant.dependencies, require_media_session)
    )
    assert found == sorted(COOKIE_GUARDED_ROUTES), (
        f"cookie-guarded routes changed: app has {found}, "
        f"COOKIE_GUARDED_ROUTES lists {sorted(COOKIE_GUARDED_ROUTES)}"
    )


def test_fastapi_docs_are_not_public():
    """FastAPI's built-in /docs, /redoc, /openapi.json must be disabled."""
    paths = {getattr(route, "path", None) for route in app.routes}
    assert paths.isdisjoint(
        FORBIDDEN_PUBLIC_DOCS
    ), f"Forbidden public docs/schema present: {paths & FORBIDDEN_PUBLIC_DOCS}"
