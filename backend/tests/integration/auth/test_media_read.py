"""Integration tests for ``GET /uploads/{key}`` — the M7 PR2 media read proxy.

This is the security-critical surface of the milestone. Before PR2, `/uploads/*`
was a public `StaticFiles` mount that bypassed the `protected` router entirely
and was gated only by Cloudflare Access at the edge. These tests are what let
CF Access Application 1 come down: they prove first-party auth now guards every
private image byte.

Lives under `tests/integration/auth/` to inherit that conftest's unauthenticated
`client` and the `register_user` helper — the media route needs only the
`__Host-refresh` cookie, never a Bearer header.

There is NO dev/test auth bypass in the guard (eng review A2), so these tests
hit the real route with a real cookie. pytest can set the cookie directly, so
the browser same-site question never arises here; that is covered by the
Playwright shim and by the operator's live pre-merge check (OQ1).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from botocore.exceptions import ClientError, EndpointConnectionError

from app.auth import service
from app.auth.models import RefreshToken, User
from app.auth.tokens import REFRESH_TOKEN_GRACE_SECONDS, hash_refresh_token
from app.models import Asset
from app.storage import ObjectNotFound, get_storage

COOKIE = "__Host-refresh"

# A 1x1 PNG. Real magic bytes so nothing here depends on validation being lax.
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)
MANAGED_KEY = "item-icons/0190a1b2-c3d4-4e5f-8a9b-0c1d2e3f4a5b.png"


async def _seed_asset(db_session, key=MANAGED_KEY, content_type="image/png", data=PNG_BYTES):
    """Put an object in storage + its manifest row, the way `store_upload`
    would. Bypasses the upload endpoint on purpose: the read path is what is
    under test, and the write path already has its own suite."""
    await get_storage().put(key, data, content_type)
    db_session.add(
        Asset(key=key, content_type=content_type, size_bytes=len(data), referenced=True)
    )
    await db_session.flush()
    return key


async def _row_for(db_session, cookie):
    return (
        await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(cookie)
            )
        )
    ).scalar_one()


# =============================================================================
# The rejection matrix (eng review — mandated)
# =============================================================================

@pytest.mark.asyncio
async def test_absent_cookie_is_401(client, register_user, db_session):
    """The headline property: no session, no private image."""
    await _seed_asset(db_session)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 401
    assert r.json() == {"detail": "unauthorized"}
    assert r.headers["cache-control"] == "private, no-store"


@pytest.mark.asyncio
async def test_unknown_cookie_is_401(client, register_user, db_session):
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, "this-cookie-matches-no-row-at-all")
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_live_cookie_serves_bytes(client, register_user, db_session):
    _, cookie, _ = await register_user("live@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 200
    assert r.content == PNG_BYTES
    assert r.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_revoked_cookie_is_401(client, register_user, db_session):
    _, cookie, _ = await register_user("revoked@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    row = await _row_for(db_session, cookie)
    row.revoked_at = datetime.now(timezone.utc)
    await db_session.flush()

    client.cookies.set(COOKIE, cookie)
    assert (await client.get(f"/uploads/{MANAGED_KEY}")).status_code == 401


@pytest.mark.asyncio
async def test_expired_cookie_is_401(client, register_user, db_session):
    _, cookie, _ = await register_user("expired@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    row = await _row_for(db_session, cookie)
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    client.cookies.set(COOKIE, cookie)
    assert (await client.get(f"/uploads/{MANAGED_KEY}")).status_code == 401


@pytest.mark.asyncio
async def test_superseded_past_grace_is_401(client, register_user, db_session):
    """A rotated-away cookie must not keep loading images for its full 30-day
    TTL just because it can no longer refresh."""
    _, cookie, _ = await register_user("stale@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    row = await _row_for(db_session, cookie)
    row.superseded_at = datetime.now(timezone.utc) - timedelta(
        seconds=REFRESH_TOKEN_GRACE_SECONDS + 5
    )
    await db_session.flush()

    client.cookies.set(COOKIE, cookie)
    assert (await client.get(f"/uploads/{MANAGED_KEY}")).status_code == 401


@pytest.mark.asyncio
async def test_superseded_within_grace_still_serves(client, register_user, db_session):
    """Mid-rotation, a page must not flash broken images for 60 seconds."""
    _, cookie, _ = await register_user("grace@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    row = await _row_for(db_session, cookie)
    row.superseded_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 200
    assert r.content == PNG_BYTES


@pytest.mark.asyncio
async def test_read_does_not_rotate_or_perturb_the_grace_window(
    client, register_user, db_session
):
    """OQ1's second half: a read is READ-ONLY. It must not rotate the cookie,
    supersede the row, or otherwise disturb the window /auth/refresh owns."""
    _, cookie, _ = await register_user("norotate@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    before = await _row_for(db_session, cookie)
    before_state = (before.superseded_at, before.successor_id, before.revoked_at)

    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 200
    assert COOKIE not in r.cookies
    assert not any(
        COOKIE in v for v in r.headers.get_list("set-cookie")
    ), "a media read must never issue a Set-Cookie"

    await db_session.refresh(before)
    assert (before.superseded_at, before.successor_id, before.revoked_at) == before_state


@pytest.mark.asyncio
async def test_401_body_is_identical_across_rejection_reasons(
    client, register_user, db_session
):
    """Absent vs unknown vs revoked must be indistinguishable to the caller —
    the categorical reason lives only in the log."""
    _, cookie, _ = await register_user("identical@example.com", "pwd-1234567890")
    await _seed_asset(db_session)

    bodies = set()
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    bodies.add((r.status_code, r.text))

    client.cookies.set(COOKIE, "unknown-value")
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    bodies.add((r.status_code, r.text))

    row = await _row_for(db_session, cookie)
    row.revoked_at = datetime.now(timezone.utc)
    await db_session.flush()
    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    bodies.add((r.status_code, r.text))

    assert len(bodies) == 1, f"401 responses differ between reasons: {bodies}"


@pytest.mark.asyncio
async def test_rejection_is_logged_with_a_categorical_reason(
    client, register_user, db_session, caplog
):
    """Ops needs to see unauthenticated hits on private media."""
    await _seed_asset(db_session)
    caplog.set_level(logging.WARNING, logger="app.auth")
    caplog.clear()

    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 401
    reasons = [
        rec.__dict__.get("reason")
        for rec in caplog.records
        if rec.__dict__.get("event") == "media_read"
    ]
    assert "media_no_cookie" in reasons


# =============================================================================
# Key validation — nothing malformed may reach storage
# =============================================================================

# Only shapes that genuinely survive an HTTP client. httpx (like every
# conforming client) normalizes literal `../` dot-segments out of the path
# before sending, so `/uploads/item-icons/../../app/main.py` arrives as a
# different path and 404s on no route match — a route test for it would pass
# with no validator at all. Literal-traversal rejection is pinned in
# tests/unit/test_storage_keys.py instead. What DOES arrive, verified against
# httpx + Starlette:
#   %2f-encoded traversal  -> key "stock_icons/../../app/main.py"
#   /uploads//etc/passwd   -> key "/etc/passwd"  (leading slash; `root / key`
#                             would discard the storage root)
MALFORMED_KEYS = [
    pytest.param("stock_icons/..%2f..%2fapp%2fmain.py", id="encoded-traversal"),
    pytest.param("item-icons/..%2f..%2fetc%2fpasswd", id="encoded-traversal-managed"),
    pytest.param("/etc/passwd", id="absolute-leading-slash"),
    pytest.param("item-icons//x.png", id="empty-segment"),
    pytest.param(
        "unknown-subdir/0190a1b2-c3d4-4e5f-8a9b-0c1d2e3f4a5b.png", id="unknown-subdir"
    ),
    pytest.param("item-icons/not-a-uuid.png", id="non-uuid"),
    pytest.param(
        "item-icons/0190a1b2-c3d4-4e5f-8a9b-0c1d2e3f4a5b.gif", id="rejected-ext"
    ),
    pytest.param(
        "item-icons/0190a1b2-c3d4-4e5f-8a9b-0c1d2e3f4a5b", id="no-ext"
    ),
]


class _ExplodingBackend:
    """Any call means a malformed key got past validation."""

    def __init__(self):
        self.calls = []

    async def get(self, key):
        self.calls.append(key)
        raise AssertionError(f"storage.get reached with key {key!r}")

    async def put(self, key, data, content_type):
        raise AssertionError("storage.put must not be called by a read")

    async def delete(self, key):
        raise AssertionError("storage.delete must not be called by a read")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_key", MALFORMED_KEYS)
async def test_malformed_keys_404_without_touching_storage(
    client, register_user, db_session, monkeypatch, bad_key
):
    """Rejected BEFORE any storage lookup.

    The backend is patched at the FACTORY (`app.routes.media.get_storage`), not
    on an instance: `get_storage()` constructs a fresh `LocalDiskBackend` per
    call, so patching a returned object patches something the route never uses
    — which is how the first version of this test passed vacuously.
    """
    _, cookie, _ = await register_user("badkey@example.com", "pwd-1234567890")
    backend = _ExplodingBackend()
    monkeypatch.setattr("app.routes.media.get_storage", lambda: backend)

    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{bad_key}")
    assert r.status_code == 404
    assert backend.calls == [], f"storage was reached with {backend.calls}"


@pytest.mark.asyncio
async def test_exploding_backend_would_be_reached_for_a_valid_key(
    client, register_user, db_session, monkeypatch
):
    """Negative control for the test above.

    Without this, `backend.calls == []` could hold because the patch never
    took effect rather than because validation rejected the key. A VALID key
    must reach the patched backend and blow up.
    """
    _, cookie, _ = await register_user("control@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    backend = _ExplodingBackend()
    monkeypatch.setattr("app.routes.media.get_storage", lambda: backend)

    client.cookies.set(COOKIE, cookie)

    # The route catches only genuine storage-failure classes (botocore errors,
    # OSError, TimeoutError). An AssertionError is a BUG, not an outage, so it
    # propagates instead of being laundered into `503 storage_unavailable` and
    # sending whoever is on call to the Cloudflare dashboard. Pre-landing
    # review: this test used to assert 503 here, which was the tell.
    with pytest.raises(AssertionError, match="storage.get reached with key"):
        await client.get(f"/uploads/{MANAGED_KEY}")

    assert backend.calls == [MANAGED_KEY], "the factory patch did not take effect"


@pytest.mark.asyncio
async def test_malformed_key_still_requires_auth_first(client, db_session):
    """A malformed key with no cookie must 401, not 404 — the guard runs as a
    dependency, so the route cannot be probed for which key shapes are real.

    Uses `unknown-subdir` rather than a `../` string because the latter never
    reaches the route (see the MALFORMED_KEYS note).
    """
    r = await client.get("/uploads/unknown-subdir/whatever.png")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_missing_manifest_row_is_404(client, register_user, db_session):
    _, cookie, _ = await register_user("norow@example.com", "pwd-1234567890")
    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_manifest_row_but_object_gone_is_404(client, register_user, db_session):
    """Row present, bytes gone (ephemeral disk, or a half-finished delete).
    The page degrades to a broken image, not a 500."""
    _, cookie, _ = await register_user("noobject@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    await get_storage().delete(MANAGED_KEY)

    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_storage_unreachable_is_503_and_logged_distinctly(
    client, register_user, db_session, monkeypatch, caplog
):
    """R2 down / timeout must NOT masquerade as a missing-key 404 — ops has to
    tell those apart from the logs alone (eng review 1).

    Patched at the factory for the same reason as the malformed-key test.
    """
    _, cookie, _ = await register_user("r2down@example.com", "pwd-1234567890")
    await _seed_asset(db_session)

    class _UnreachableBackend:
        async def get(self, key):
            raise OSError("simulated R2 timeout")

    monkeypatch.setattr("app.routes.media.get_storage", lambda: _UnreachableBackend())
    caplog.set_level(logging.ERROR, logger="app.routes.media")
    caplog.clear()

    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 503
    assert r.json() == {"detail": "storage_unavailable"}
    assert any(
        "STORAGE UNREACHABLE" in rec.getMessage() for rec in caplog.records
    ), "storage-unreachable must be logged distinctly from a 404"


@pytest.mark.asyncio
async def test_storage_unreachable_is_not_confused_with_a_missing_object(
    client, register_user, db_session, monkeypatch
):
    """The pair that makes the distinction meaningful: same route, same key,
    two different storage failures, two different statuses."""
    _, cookie, _ = await register_user("bothfails@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)

    class _MissingBackend:
        async def get(self, key):
            raise ObjectNotFound(key)

    monkeypatch.setattr("app.routes.media.get_storage", lambda: _MissingBackend())
    assert (await client.get(f"/uploads/{MANAGED_KEY}")).status_code == 404

    class _DownBackend:
        async def get(self, key):
            raise TimeoutError("boom")

    monkeypatch.setattr("app.routes.media.get_storage", lambda: _DownBackend())
    assert (await client.get(f"/uploads/{MANAGED_KEY}")).status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(
            ClientError({"Error": {"Code": "InternalError", "Message": "R2 5xx"}}, "GetObject"),
            id="botocore-ClientError",
        ),
        pytest.param(
            EndpointConnectionError(endpoint_url="https://r2.invalid"),
            id="botocore-EndpointConnectionError",
        ),
        pytest.param(OSError("socket"), id="OSError"),
        pytest.param(TimeoutError("read"), id="TimeoutError"),
    ],
)
async def test_every_real_storage_failure_class_is_503(
    client, register_user, db_session, monkeypatch, exc
):
    """The 503 branch catches a specific tuple. The two classes R2 actually
    raises (botocore's) were previously untested, so dropping them from the
    tuple would have shipped green with a 500 where ops expects a 503."""
    _, cookie, _ = await register_user(f"fail{type(exc).__name__}@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)

    class _Backend:
        async def get(self, key):
            raise exc

    monkeypatch.setattr("app.routes.media.get_storage", lambda: _Backend())
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 503
    assert r.json() == {"detail": "storage_unavailable"}
    assert r.headers["cache-control"] == "private, no-store"


@pytest.mark.asyncio
async def test_error_responses_are_never_cacheable(client, register_user, db_session):
    """Cloudflare caches by URL extension and these URLs end in .png. A 404
    with no Cache-Control could be edge-cached for minutes and replayed to an
    unauthenticated requester. `private, no-store` on every error makes that
    structurally impossible."""
    _, cookie, _ = await register_user("errcache@example.com", "pwd-1234567890")
    client.cookies.set(COOKIE, cookie)

    for path in (f"/uploads/{MANAGED_KEY}", "/uploads/unknown-subdir/x.png",
                 "/uploads/stock_icons/does-not-exist.png"):
        r = await client.get(path)
        assert r.status_code == 404, path
        assert r.headers["cache-control"] == "private, no-store", path


@pytest.mark.asyncio
async def test_db_transaction_ends_before_the_storage_fetch(
    client, register_user, db_session, monkeypatch
):
    """Pre-landing review, run 2: the manifest SELECT autobegins a transaction
    and `get_db` would hold that pooled connection across the R2 round trip.
    The route must end the transaction (commit) BEFORE calling storage, so a
    slow R2 cannot exhaust the 15-wide pool and starve every other route.

    Pinned by call ORDER rather than by inspecting transaction state, because
    the test session runs in SAVEPOINT mode where an outer transaction is
    always open."""
    _, cookie, _ = await register_user("txorder@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)

    calls: list[str] = []
    real_commit = db_session.commit

    async def spy_commit():
        calls.append("commit")
        await real_commit()

    monkeypatch.setattr(db_session, "commit", spy_commit)

    class _Backend:
        async def get(self, key):
            calls.append("storage.get")
            return PNG_BYTES

    monkeypatch.setattr("app.routes.media.get_storage", lambda: _Backend())

    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 200
    assert r.content == PNG_BYTES
    assert calls == ["commit", "storage.get"], calls
    # and the content-type still came from the manifest after the commit
    assert r.headers["content-type"] == "image/png"


# =============================================================================
# Manifest is the content-type authority
# =============================================================================

@pytest.mark.asyncio
async def test_content_type_comes_from_the_manifest(client, register_user, db_session):
    """Not from the file extension, and not from anything the backend reports —
    LocalDiskBackend stores no content-type at all."""
    _, cookie, _ = await register_user("ctype@example.com", "pwd-1234567890")
    key = "recipe_images/0190a1b2-c3d4-4e5f-8a9b-0c1d2e3f4a5c.webp"
    await _seed_asset(db_session, key=key, content_type="image/webp")

    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{key}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/webp"


# =============================================================================
# stock_icons/* compat branch
# =============================================================================

@pytest.mark.asyncio
async def test_stock_icon_serves_from_the_image(client, register_user, db_session):
    """Bundled, no manifest row, never in R2 — but entity columns adopted
    `/uploads/stock_icons/*.png` long before M7, so these must keep resolving."""
    _, cookie, _ = await register_user("stock@example.com", "pwd-1234567890")
    client.cookies.set(COOKIE, cookie)

    r = await client.get("/uploads/stock_icons/homework.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_stock_icons_still_require_a_session(client, db_session):
    r = await client.get("/uploads/stock_icons/homework.png")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_unknown_stock_icon_is_404(client, register_user, db_session):
    _, cookie, _ = await register_user("nostock@example.com", "pwd-1234567890")
    client.cookies.set(COOKIE, cookie)
    r = await client.get("/uploads/stock_icons/does-not-exist.png")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_stock_icon_traversal_is_404(client, register_user, db_session):
    """`stock_icons/` must not become a file-read primitive over the image."""
    _, cookie, _ = await register_user("stocktrav@example.com", "pwd-1234567890")
    client.cookies.set(COOKIE, cookie)
    for bad in (
        "/uploads/stock_icons/../../app/main.py",
        "/uploads/stock_icons/..%2f..%2fapp%2fmain.py",
        "/uploads/stock_icons/sub/dir.png",
    ):
        assert (await client.get(bad)).status_code == 404, bad


@pytest.mark.asyncio
async def test_every_listed_stock_icon_resolves(client, register_user, db_session):
    """The `/upload/stock-icons` picker's URLs must all actually load — this is
    the regression that would strand the icon picker."""
    access, cookie, _ = await register_user("picker@example.com", "pwd-1234567890")
    listing = await client.get(
        "/upload/stock-icons", headers={"Authorization": f"Bearer {access}"}
    )
    assert listing.status_code == 200
    client.cookies.set(COOKIE, cookie)
    for entry in listing.json():
        r = await client.get(entry["url"])
        assert r.status_code == 200, f"{entry['url']} did not resolve"
        assert r.headers["content-type"] == "image/png"


# =============================================================================
# Cache-Control + ETag / 304 (eng review 1 — perf, built into PR2)
# =============================================================================

@pytest.mark.asyncio
async def test_cache_control_is_private_no_cache(client, register_user, db_session):
    """`private` is load-bearing: it forbids the Cloudflare edge from caching a
    private image. `no-cache` (not `no-store`) lets the browser keep bytes but
    revalidate every time, so the guard still runs on every load."""
    _, cookie, _ = await register_user("cc@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)

    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.headers["cache-control"] == "private, no-cache"
    assert "public" not in r.headers["cache-control"]
    assert "max-age" not in r.headers["cache-control"]


@pytest.mark.asyncio
async def test_etag_is_the_key_and_if_none_match_returns_304(
    client, register_user, db_session
):
    _, cookie, _ = await register_user("etag@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)

    first = await client.get(f"/uploads/{MANAGED_KEY}")
    etag = first.headers["etag"]
    assert etag == f'"{MANAGED_KEY}"'

    second = await client.get(
        f"/uploads/{MANAGED_KEY}", headers={"If-None-Match": etag}
    )
    assert second.status_code == 304
    assert second.content == b""
    assert second.headers["etag"] == etag
    assert second.headers["cache-control"] == "private, no-cache"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "header,expected",
    [
        pytest.param(f'"{MANAGED_KEY}"', 304, id="exact"),
        pytest.param(f'W/"{MANAGED_KEY}"', 304, id="weak"),
        pytest.param("*", 304, id="star"),
        pytest.param(f'"other", "{MANAGED_KEY}"', 304, id="list-contains"),
        pytest.param('"some-other-key"', 200, id="no-match"),
    ],
)
async def test_if_none_match_shapes(
    client, register_user, db_session, header, expected
):
    """Real clients send bare tags, weak tags, `*`, and comma-separated lists."""
    _, cookie, _ = await register_user("inm@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)

    r = await client.get(
        f"/uploads/{MANAGED_KEY}", headers={"If-None-Match": header}
    )
    assert r.status_code == expected


@pytest.mark.asyncio
async def test_304_still_requires_a_valid_session(client, register_user, db_session):
    """The whole reason `no-cache` is safe: a revalidation carries the cookie
    and re-runs the guard. A revoked session must get 401, never a cheap 304."""
    _, cookie, _ = await register_user("revalidate@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)
    etag = (await client.get(f"/uploads/{MANAGED_KEY}")).headers["etag"]

    row = await _row_for(db_session, cookie)
    row.revoked_at = datetime.now(timezone.utc)
    await db_session.flush()

    r = await client.get(
        f"/uploads/{MANAGED_KEY}", headers={"If-None-Match": etag}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_no_304_when_the_manifest_row_is_gone(
    client, register_user, db_session
):
    """RFC 9110 §13.1.2 — a conditional is only evaluated against a CURRENT
    representation. Returning 304 for a key with no manifest row would let a
    browser keep rendering a deleted family photo out of its own cache
    forever, because `no-cache` revalidation would never be told it is gone.
    """
    _, cookie, _ = await register_user("ghost@example.com", "pwd-1234567890")
    client.cookies.set(COOKIE, cookie)

    ghost = "item-icons/deadbeef-0000-4000-8000-000000000000.png"
    plain = await client.get(f"/uploads/{ghost}")
    conditional = await client.get(
        f"/uploads/{ghost}", headers={"If-None-Match": f'"{ghost}"'}
    )
    assert plain.status_code == 404
    assert conditional.status_code == 404, (
        "a conditional request must not turn a 404 into a 304"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("header", ["*", '"unknown-subdir/x.png"'])
async def test_no_304_for_a_key_that_fails_validation(
    client, register_user, db_session, header
):
    """The conditional must not run before the key allowlist. `*` matched
    unconditionally, so a malformed or unknown-subdir key answered 304 and
    skipped the validator entirely."""
    _, cookie, _ = await register_user(
        f"badcond{abs(hash(header))}@example.com", "pwd-1234567890"
    )
    client.cookies.set(COOKIE, cookie)

    r = await client.get(
        "/uploads/unknown-subdir/x.png", headers={"If-None-Match": header}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_non_latin1_key_with_a_conditional_header_does_not_crash(
    client, register_user, db_session
):
    """Regression: `{key:path}` accepts any character, and the ETag was built
    from the raw param BEFORE validation. Starlette encodes header values as
    latin-1, so `ETag: "日"` raised UnicodeEncodeError — an unhandled 500 on
    the route that serves private photos. Building the ETag only from an
    already-allowlisted key makes it ASCII by construction.
    """
    _, cookie, _ = await register_user("unicode@example.com", "pwd-1234567890")
    client.cookies.set(COOKIE, cookie)

    for header in ("*", '"whatever"'):
        r = await client.get("/uploads/%E6%97%A5", headers={"If-None-Match": header})
        assert r.status_code == 404, header


@pytest.mark.asyncio
async def test_media_responses_carry_nosniff_and_no_vary_cookie(
    client, register_user, db_session
):
    """This route hands user-uploaded bytes back to a browser: it must never
    invite content-type sniffing — on the 200 AND on the 304.

    It must also NOT send `Vary: Cookie` (pre-landing review, run 2): the
    refresh cookie rotates every ~15 min of use, and a browser treats a cached
    entry whose Vary'd header changed as unusable — every rotation would turn
    every image back into a full download and void the 304 path."""
    _, cookie, _ = await register_user("headers@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)

    ok = await client.get(f"/uploads/{MANAGED_KEY}")
    assert ok.status_code == 200
    assert ok.headers["x-content-type-options"] == "nosniff"
    assert "cookie" not in ok.headers.get("vary", "").lower()

    not_modified = await client.get(
        f"/uploads/{MANAGED_KEY}", headers={"If-None-Match": ok.headers["etag"]}
    )
    assert not_modified.status_code == 304
    assert not_modified.headers["x-content-type-options"] == "nosniff"
    assert "cookie" not in not_modified.headers.get("vary", "").lower()


@pytest.mark.asyncio
async def test_stock_icon_conditional_still_serves_and_still_304s(
    client, register_user, db_session
):
    """The stock branch has its own conditional check now that the shared
    early return is gone — pin both arms so the reorder cannot silently drop
    ETag support for bundled icons."""
    _, cookie, _ = await register_user("stockcond@example.com", "pwd-1234567890")
    client.cookies.set(COOKIE, cookie)

    first = await client.get("/uploads/stock_icons/homework.png")
    assert first.status_code == 200
    assert first.headers["etag"] == '"stock_icons/homework.png"'
    assert first.headers["x-content-type-options"] == "nosniff"

    second = await client.get(
        "/uploads/stock_icons/homework.png",
        headers={"If-None-Match": first.headers["etag"]},
    )
    assert second.status_code == 304

    # A stock icon that does not exist must 404 even with `*`.
    missing = await client.get(
        "/uploads/stock_icons/does-not-exist.png", headers={"If-None-Match": "*"}
    )
    assert missing.status_code == 404


# =============================================================================
# T2 — the session_version → read-access invariant (eng review, mandated)
# =============================================================================

@pytest.mark.asyncio
async def test_logout_revokes_read_access_for_the_same_cookie(
    client, register_user, db_session
):
    """THE security-critical end-to-end check: log in → image loads → log out →
    the very same cookie can no longer load that image."""
    access, cookie, _ = await register_user("logout@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    client.cookies.set(COOKIE, cookie)

    assert (await client.get(f"/uploads/{MANAGED_KEY}")).status_code == 200

    out = await client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {access}"}
    )
    assert out.status_code == 204

    client.cookies.set(COOKIE, cookie)
    assert (await client.get(f"/uploads/{MANAGED_KEY}")).status_code == 401


@pytest.mark.asyncio
async def test_logout_bumps_session_version_and_revokes_refresh_rows(
    client, register_user, db_session
):
    """The invariant the read guard LEANS ON, asserted directly.

    The guard deliberately does not re-check `users.session_version` (that
    would be a second query per image). Instead it relies on the M3 property
    that anything bumping `session_version` ALSO sets `revoked_at` on the
    user's refresh rows. If a future change bumps the version without
    revoking, private images would stay readable by a dead session — so the
    two halves are pinned together here.
    """
    _, cookie, _ = await register_user("invariant@example.com", "pwd-1234567890")
    row = await _row_for(db_session, cookie)
    user = (
        await db_session.execute(select(User).where(User.id == row.user_id))
    ).scalar_one()
    version_before = user.session_version

    await service.logout(db_session, row.user_id)

    await db_session.refresh(user)
    assert user.session_version == version_before + 1, "session_version must bump"

    rows = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
    ).scalars().all()
    assert rows, "expected at least one refresh row"
    assert all(r.revoked_at is not None for r in rows), (
        "every refresh row must be revoked in the SAME operation that bumps "
        "session_version — the media read guard's revocation depends on it"
    )


@pytest.mark.asyncio
async def test_session_version_bump_alone_does_not_revoke_reads(
    client, register_user, db_session
):
    """Documented hazard, not a defect (plan failure-mode table:
    "session_version bump w/o revoke → silent read access").

    This test exists to make the dependency explicit and to fail loudly if
    someone later assumes the read guard checks `session_version` itself. A
    bump WITHOUT a revoke leaves image reads working — which is exactly why
    `service.logout` must always do both, as the test above pins.
    """
    _, cookie, _ = await register_user("bumponly@example.com", "pwd-1234567890")
    await _seed_asset(db_session)
    row = await _row_for(db_session, cookie)

    await db_session.execute(
        update(User)
        .where(User.id == row.user_id)
        .values(session_version=User.session_version + 1)
    )
    await db_session.flush()

    client.cookies.set(COOKIE, cookie)
    r = await client.get(f"/uploads/{MANAGED_KEY}")
    assert r.status_code == 200, (
        "If this now 401s, the read guard started checking session_version. "
        "That is an improvement — update this test and the guard's docstring."
    )
