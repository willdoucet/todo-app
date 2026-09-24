"""``app.auth.service.rotate_password`` end to end (M8 item 6, criterion 6).

After a rotation the old password fails, the new one works, and every session the household
had — a refresh cookie, and an access JWT that has not expired — is dead. Refusals write
nothing, and a crash between setting the hash and revoking sessions leaves the old hash.

The last three tests use a second, real connection: a rotation and a sign-in in flight at
the same moment must serialize on the session-issue advisory lock (``service.py`` →
"Concurrency invariants"), or a sign-in that checked the old hash commits a session the
rotation never saw.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import func, select, text

from app.auth import passwords, service
from app.auth.models import RefreshToken, User
from app.auth.service import RotationRejected, rotate_password

EMAIL = "household@example.com"
OLD = "old-password-1234567890"
NEW = "new-password-0987654321"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _live_rows(db) -> int:
    return await db.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.revoked_at.is_(None)))


async def _login(client, password: str):
    return await client.post("/auth/login", json={"email": EMAIL, "password": password})


@pytest.mark.asyncio
async def test_rotation_swaps_the_password_and_kills_every_session(client, register_user, db_session):
    access, cookie, _ = await register_user(EMAIL, OLD)
    second = await _login(client, OLD)  # a second device
    assert second.status_code == 200
    live_before = await _live_rows(db_session)
    version_before = (await db_session.execute(select(User))).scalar_one().session_version

    summary = await rotate_password(db_session, EMAIL, NEW)

    assert summary.tokens_revoked == live_before == 2
    assert summary.session_version == version_before + 1
    assert await _live_rows(db_session) == 0
    assert (await _login(client, OLD)).status_code == 401
    assert (await _login(client, NEW)).status_code == 200
    # An access JWT minted before the rotation no longer validates.
    assert (await client.post("/auth/logout", headers=_bearer(access))).status_code == 401
    # An outstanding refresh cookie is rejected.
    client.cookies.set("__Host-refresh", cookie)
    assert (await client.post("/auth/refresh")).status_code == 401


@pytest.mark.asyncio
async def test_the_email_lookup_is_case_insensitive_like_login(client, register_user, db_session):
    await register_user(EMAIL, OLD)
    summary = await rotate_password(db_session, EMAIL.upper(), NEW)
    assert summary.tokens_revoked == 1


@pytest.mark.asyncio
async def test_an_unknown_email_is_refused_and_writes_nothing(client, register_user, db_session):
    await register_user(EMAIL, OLD)
    hash_before = (await db_session.execute(select(User))).scalar_one().password_hash
    with pytest.raises(RotationRejected, match="no user with that email"):
        await rotate_password(db_session, "someone-else@example.com", NEW)
    await db_session.rollback()
    user = (await db_session.execute(select(User))).scalar_one()
    assert (user.password_hash, user.session_version) == (hash_before, 0)
    assert await _live_rows(db_session) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("password", ["x" * 129, ""])
async def test_an_unusable_password_is_refused_before_hashing(client, register_user, db_session, monkeypatch, password):
    """CEO review 2D: argon2's limit is 128 characters and login refuses anything longer, so
    a 129-character password would lock the household out."""
    await register_user(EMAIL, OLD)
    hashed = []
    real = passwords.hash_password

    async def spy(plaintext):
        hashed.append(plaintext)
        return await real(plaintext)

    monkeypatch.setattr(passwords, "hash_password", spy)
    with pytest.raises(RotationRejected):
        await rotate_password(db_session, EMAIL, password)
    assert hashed == []
    assert (await _login(client, OLD)).status_code == 200


@pytest.mark.asyncio
async def test_exactly_128_characters_is_accepted(client, register_user, db_session):
    await register_user(EMAIL, OLD)
    await rotate_password(db_session, EMAIL, "y" * 128)
    assert (await client.post("/auth/login", json={"email": EMAIL, "password": "y" * 128})).status_code == 200


@pytest.mark.asyncio
async def test_a_crash_after_the_hash_is_set_leaves_the_old_hash(client, register_user, db_session, monkeypatch):
    """Adversarial review: one transaction. ``logout`` is the only commit, so if it fails
    after the new hash is already dirty on the session, nothing lands."""
    await register_user(EMAIL, OLD)
    hash_before = (await db_session.execute(select(User))).scalar_one().password_hash

    async def crash(db, user_id):
        await db.flush()  # the new hash is written inside the transaction...
        raise ConnectionResetError("database connection lost")  # ...and never committed

    monkeypatch.setattr(service, "logout", crash)
    with pytest.raises(ConnectionResetError):
        await rotate_password(db_session, EMAIL, NEW)
    await db_session.rollback()
    user = (await db_session.execute(select(User))).scalar_one()
    assert user.password_hash == hash_before
    assert user.session_version == 0
    assert await _live_rows(db_session) == 1


# --- a rotation and a sign-in at the same moment (M8 PR1b review) ------------------------
# The other connection holds the lock the way a real login, refresh or rotation would in
# the middle of its transaction; the call under test runs on the test's own session.

LOCK_SHARED = text("SELECT pg_advisory_xact_lock_shared(hashtext('auth_session_issue'))")
LOCK_EXCLUSIVE = text("SELECT pg_advisory_xact_lock(hashtext('auth_session_issue'))")


async def _still_waiting(task: asyncio.Task, seconds: float = 0.5) -> bool:
    await asyncio.sleep(seconds)
    return not task.done()


@pytest.mark.asyncio
async def test_a_rotation_waits_for_a_sign_in_in_flight(register_user, db_session, test_engine):
    """A login that has checked the old hash, or a refresh that has inserted its successor,
    holds the shared lock until it commits. The rotation must wait for that commit, so its
    revoke sees the new row."""
    await register_user(EMAIL, OLD)
    async with test_engine.connect() as sign_in:
        await sign_in.execute(LOCK_SHARED)
        rotation = asyncio.create_task(rotate_password(db_session, EMAIL, NEW))
        try:
            waiting = await _still_waiting(rotation)
        finally:
            await sign_in.rollback()
            summary = await asyncio.wait_for(rotation, 5)
    assert waiting, "the rotation did not wait for the sign-in in flight"
    assert summary.tokens_revoked == 1


@pytest.mark.asyncio
async def test_a_login_waits_for_a_rotation_in_flight(register_user, db_session, test_engine):
    """A login that starts during a rotation waits for it, then reads the hash that stands."""
    await register_user(EMAIL, OLD)
    async with test_engine.connect() as rotation:
        await asyncio.wait_for(rotation.execute(LOCK_EXCLUSIVE), 5)
        login = asyncio.create_task(service.login(db_session, EMAIL, OLD, None))
        try:
            waiting = await _still_waiting(login)
        finally:
            await rotation.rollback()
            result = await asyncio.wait_for(login, 5)
    assert waiting, "the login did not wait for the rotation in flight"
    assert result.refresh_plaintext


@pytest.mark.asyncio
async def test_a_refresh_waits_for_a_rotation_in_flight(register_user, db_session, test_engine):
    _, cookie, _ = await register_user(EMAIL, OLD)
    async with test_engine.connect() as rotation:
        await asyncio.wait_for(rotation.execute(LOCK_EXCLUSIVE), 5)
        refresh = asyncio.create_task(service.refresh(db_session, cookie))
        try:
            waiting = await _still_waiting(refresh)
        finally:
            await rotation.rollback()
            outcome = await asyncio.wait_for(refresh, 5)
    assert waiting, "the refresh did not wait for the rotation in flight"
    assert outcome.new_refresh_plaintext
