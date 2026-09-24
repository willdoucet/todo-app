"""Auth business logic — async throughout.

Refresh-token rotation chain (Case A/B/C):

    LoginA  (live row #1) ──refresh──▶  Case A: row #1.superseded_at = NOW(),
                                                row #1.successor_id = #2
                                                INSERT row #2 (live)
                                        ────────────────────────────────
    Concurrent /refresh with same cookie within 60s grace:
         Row lock on #1 (SELECT ... FOR UPDATE) forces second caller to wait.
         When they read post-lock, they see #1.superseded_at NOT NULL,
         so they fall to Case B.
         Case B: walk successor chain forward — lock each successor row
         FOR UPDATE before evaluating it. At the live terminal
         (successor_id IS NULL, revoked_at IS NULL, superseded_at IS NULL,
         expires_at > NOW()) → mint access JWT using current
         users.session_version, return access token only — NO Set-Cookie
         (the browser already has the new cookie from the parallel
         Case A response).
    ────────────────────────────────
    Past 60s grace: superseded_at + 60s < NOW() → Case C: reject 401.

Same-client login rotation: a successful /auth/login that arrives carrying
its own __Host-refresh cookie revokes ONLY that one row (revoked_at).
Other devices' tokens remain live. Multi-device household preserved.

Operator password rotation (M8: ``rotate_password()``, run by ``app.cli.rotate_password``):
    hash the new password → pg_advisory_xact_lock('auth_session_issue')  (exclusive:
        waits for every in-flight login and refresh to commit, holds new ones off)
    → set password_hash (dirty, same session) → count live refresh rows
    → logout(): session_version += 1 (kills all in-flight access JWTs)
                UPDATE refresh_tokens SET revoked_at = NOW()
                    WHERE user_id = X AND revoked_at IS NULL  (kills all active sessions)
                ONE commit: hash, bump and revoke land together or not at all
    → re-read session_version for the summary
    The ordering is what keeps a crash fail-closed: there is no moment where the new
    password is stored and the old sessions still work, or the reverse. The lock is what
    keeps a CONCURRENT sign-in from outliving it: without it, a login that checked the old
    hash, or a refresh that inserted a successor, could commit its row after the revoke's
    snapshot was taken, and that row would survive (found by /review-implementation's
    adversarial pass, M8 PR1b; READ COMMITTED never re-scans for rows inserted after a
    statement began).

Concurrency invariants:
    /auth/refresh:  SELECT ... FOR UPDATE on the row whose token_hash
                    matches the incoming cookie, AND on each successor
                    row visited during Case B traversal.
    /auth/register: pg_advisory_xact_lock(hashtext('auth_register_singleton'))
                    serializes concurrent registrations behind the
                    "no existing user" check.
    /auth/login success block: revoke-old-cookie + insert-new-refresh
                    commit together via the single db.commit() at the end.
    /auth/login, /auth/refresh vs rotate_password and logout:
                    pg_advisory_xact_lock_shared(hashtext('auth_session_issue'))
                    first, before any row lock; rotate_password and logout (the
                    Sign out button revokes every device too) take the same key
                    exclusive, also before any row lock. So a rotation waits
                    for every in-flight sign-in to commit (its rows are
                    then visible to the revoke), and a sign-in that starts
                    during a rotation waits and then reads the new hash
                    and session_version. Shared holders never block each
                    other; everyone takes the advisory lock before row
                    locks, so no deadlock.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import errors, passwords, tokens
from app.auth.config import get_settings
from app.auth.models import RefreshToken, User
from app.auth.schemas import PASSWORD_MAX_LENGTH

# Single advisory-lock key for every register attempt — concurrent
# registrations serialize on this lock so only one passes the
# "no existing user" check.
ADVISORY_LOCK_KEY = "auth_register_singleton"

# Every path that issues a session (login, refresh) holds this shared; the operator's
# password rotation holds it exclusive. See "Concurrency invariants" above.
SESSION_ISSUE_LOCK_KEY = "auth_session_issue"


async def _hold_session_issue_lock(db: AsyncSession, *, exclusive: bool = False) -> None:
    # Transaction-scoped: released by the commit or rollback that ends the request. text()
    # interpolation is safe: the function name and key are module constants, not input.
    fn = "pg_advisory_xact_lock" if exclusive else "pg_advisory_xact_lock_shared"
    await db.execute(text(f"SELECT {fn}(hashtext('{SESSION_ISSUE_LOCK_KEY}'))"))

# Bound Case B successor traversal so a corrupt chain can't loop forever.
SUCCESSOR_TRAVERSAL_MAX_HOPS = 10


# =============================================================================
# Result types
# =============================================================================

@dataclass(frozen=True)
class AuthSuccess:
    """register / login result. ``refresh_plaintext`` is always set so the
    route handler can issue a Set-Cookie header."""

    access_token: str
    refresh_plaintext: str
    user_id: int


@dataclass(frozen=True)
class RefreshOutcome:
    """refresh result. ``new_refresh_plaintext`` is None for Case B (no
    Set-Cookie — the browser already has the cookie from the parallel
    Case A rotation)."""

    access_token: str
    new_refresh_plaintext: Optional[str]
    user_id: int
    reason_log: str  # one of "case_a", "case_b" — drives the structured log line


# =============================================================================
# Register
# =============================================================================

async def register(
    db: AsyncSession,
    email: str,
    password: str,
    access_key: str,
) -> AuthSuccess:
    """Create the singleton account. Raises ``registration_unavailable`` for
    wrong-key / already-claimed / concurrent-loser — all byte-identical."""
    # 1. Constant-time access-key compare. Both inputs encoded to bytes so
    # compare_digest doesn't raise on mixed types.
    expected_key = get_settings().household_access_key
    if not hmac.compare_digest(
        access_key.encode("utf-8"), expected_key.encode("utf-8")
    ):
        raise errors.registration_unavailable("bad_access_key")

    # 2. Acquire transaction-scoped advisory lock. Serializes concurrent
    # registers so only one thread can pass the "no existing user" check.
    # text() interpolation is safe here — ADVISORY_LOCK_KEY is a module
    # constant, not user input.
    await db.execute(
        text(f"SELECT pg_advisory_xact_lock(hashtext('{ADVISORY_LOCK_KEY}'))")
    )

    # 3. Singleton invariant — ANY existing user means this deployment is
    # claimed. Same response as wrong-key (byte-identical).
    existing = await db.execute(select(func.count()).select_from(User))
    if existing.scalar_one() > 0:
        raise errors.registration_unavailable("account_exists")

    # 4. Hash + insert. UNIQUE(email) is the secondary fence — the advisory
    # lock + count check above SHOULD prevent any race here, but if a
    # second register slips in via UNIQUE(email) collision we still
    # collapse to the same byte-identical response.
    password_hash = await passwords.hash_password(password)
    user = User(email=email, password_hash=password_hash, session_version=0)
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise errors.registration_unavailable("race_loser")

    # 5. Mint access + refresh; persist in the same transaction.
    access = tokens.encode_access_token(user.id, user.session_version)
    plaintext, token_hash = tokens.generate_refresh_token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=tokens.REFRESH_TOKEN_TTL_DAYS),
    )
    db.add(rt)
    await db.commit()
    return AuthSuccess(
        access_token=access, refresh_plaintext=plaintext, user_id=user.id
    )


# =============================================================================
# Login
# =============================================================================

async def login(
    db: AsyncSession,
    email: str,
    password: str,
    incoming_refresh_cookie: Optional[str],
) -> AuthSuccess:
    """Authenticate, optionally revoke the same-client refresh cookie row,
    mint fresh access + refresh. Single-transaction atomicity: revoke +
    insert commit together via the one db.commit() at the end."""

    # 1. Overlong password → byte-identical invalid_credentials. NOT 422,
    # which would be a length oracle. We still spend dummy-verify time
    # so the latency profile stays constant.
    if len(password) > PASSWORD_MAX_LENGTH:
        await passwords.verify_or_dummy(None, password)
        raise errors.invalid_credentials("bad_credentials")

    # 2. Hold off a concurrent password rotation until this login commits, and wait for
    # one already in flight, so the hash checked below is the one that stands (see
    # "Concurrency invariants").
    await _hold_session_issue_lock(db)

    # Lookup. CITEXT email column means the comparison is case-insensitive.
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # 3. Always run password verify — real hash if user exists, dummy
    # otherwise. Mock-spy in tests asserts verify is called even on the
    # unknown-email branch.
    stored = user.password_hash if user is not None else None
    ok = await passwords.verify_or_dummy(stored, password)
    if not ok or user is None:
        raise errors.invalid_credentials("bad_credentials")

    # 4. Same-client login rotation. If the request carries a refresh
    # cookie whose hash matches a NON-revoked row for THIS user, revoke
    # that row only. Other devices' rows are untouched (multi-device
    # household preserved).
    if incoming_refresh_cookie:
        incoming_hash = tokens.hash_refresh_token(incoming_refresh_cookie)
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.token_hash == incoming_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=func.now())
        )

    # 5. Mint access + refresh, INSERT new row, commit atomically.
    access = tokens.encode_access_token(user.id, user.session_version)
    plaintext, token_hash = tokens.generate_refresh_token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=tokens.REFRESH_TOKEN_TTL_DAYS),
    )
    db.add(rt)
    await db.commit()
    return AuthSuccess(
        access_token=access, refresh_plaintext=plaintext, user_id=user.id
    )


# =============================================================================
# Refresh
# =============================================================================

async def refresh(
    db: AsyncSession,
    incoming_cookie: Optional[str],
) -> RefreshOutcome:
    """Refresh access token. Cases A/B/C per module docstring. Raises
    ``refresh_failed`` (byte-identical 401) for any rejection."""

    if not incoming_cookie:
        raise errors.refresh_failed("bad_refresh")

    incoming_hash = tokens.hash_refresh_token(incoming_cookie)

    # 0. Before any row lock: a concurrent password rotation must see this refresh's
    # successor row, or wait for it (see "Concurrency invariants").
    await _hold_session_issue_lock(db)

    # 1. Lookup + lock. The FOR UPDATE is required (Adversarial review):
    # without it, two simultaneous Case-A refreshes can both insert
    # successors against the same row.
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == incoming_hash)
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise errors.refresh_failed("bad_refresh")

    now = datetime.now(timezone.utc)

    # 2-4. Classify the row through the SHARED validity predicate (M7 PR2,
    # eng review CQ1). The media read guard behind GET /uploads/{key} calls
    # the same function, so "is this session valid?" cannot drift between the
    # refresh path and the image-read path. Rotation stays here; only the
    # predicate is shared.
    status = tokens.refresh_row_status(row, now)

    if status is tokens.RefreshStatus.REVOKED:
        raise errors.refresh_failed("bad_refresh_revoked")
    if status is tokens.RefreshStatus.EXPIRED:
        raise errors.refresh_failed("bad_refresh_expired")
    if status is tokens.RefreshStatus.LIVE:
        return await _refresh_case_a(db, row, now)
    if status is tokens.RefreshStatus.SUPERSEDED_IN_GRACE:
        return await _refresh_case_b(db, row, now)

    # Case C — superseded past grace. Reject.
    raise errors.refresh_failed("bad_refresh_superseded")


async def _refresh_case_a(
    db: AsyncSession,
    row: RefreshToken,
    now: datetime,
) -> RefreshOutcome:
    """Case A — fresh-token rotation. Insert successor; mark current row
    superseded_at + successor_id; mint access JWT + new refresh cookie."""

    plaintext, new_hash = tokens.generate_refresh_token()
    new_row = RefreshToken(
        user_id=row.user_id,
        token_hash=new_hash,
        expires_at=now + timedelta(days=tokens.REFRESH_TOKEN_TTL_DAYS),
    )
    db.add(new_row)
    await db.flush()  # populate new_row.id

    row.superseded_at = now
    row.successor_id = new_row.id

    # Read user.session_version AS IT STANDS NOW. A password rotation cannot
    # be in flight: it waits on the session-issue lock this refresh holds
    # (see "Concurrency invariants"), so it commits either before this
    # transaction began — and then the incoming row was already revoked —
    # or after it commits, when the revoke sees and revokes new_row. The
    # row lock alone never did that: an UPDATE's snapshot does not include
    # rows inserted after it began (M8 PR1b review).
    sv_result = await db.execute(
        select(User.session_version).where(User.id == row.user_id)
    )
    session_version = sv_result.scalar_one()
    access = tokens.encode_access_token(row.user_id, session_version)

    await db.commit()
    return RefreshOutcome(
        access_token=access,
        new_refresh_plaintext=plaintext,
        user_id=row.user_id,
        reason_log="case_a",
    )


async def _refresh_case_b(
    db: AsyncSession,
    row: RefreshToken,
    now: datetime,
) -> RefreshOutcome:
    """Case B — superseded within grace. Walk successor_id forward,
    locking each visited row, until the live terminal is found.

    Cap at SUCCESSOR_TRAVERSAL_MAX_HOPS hops; cycle detection via visited
    set. Both yield ``bad_refresh_chain`` on rejection."""

    visited: set[int] = {row.id}
    current = row
    for _ in range(SUCCESSOR_TRAVERSAL_MAX_HOPS):
        if current.successor_id is None:
            # Hit a terminal. Re-check liveness post-lock — through the same
            # shared predicate (CQ1), so this third copy of "is this row
            # live?" cannot drift from steps 2-4 or from the media guard.
            if tokens.refresh_row_status(current, now) is tokens.RefreshStatus.LIVE:
                # Live terminal — mint access JWT, NO new cookie.
                sv_result = await db.execute(
                    select(User.session_version).where(User.id == current.user_id)
                )
                session_version = sv_result.scalar_one()
                access = tokens.encode_access_token(
                    current.user_id, session_version
                )
                await db.commit()
                return RefreshOutcome(
                    access_token=access,
                    new_refresh_plaintext=None,
                    user_id=current.user_id,
                    reason_log="case_b",
                )
            # Terminal exists but isn't live (revoked / expired / mid-rotation
            # by a concurrent logout or password rotation).
            raise errors.refresh_failed("bad_refresh_chain")

        next_id = current.successor_id
        if next_id in visited:
            # Cycle detected.
            raise errors.refresh_failed("bad_refresh_chain")
        visited.add(next_id)

        # Walk to successor — re-lock it before reading state.
        sresult = await db.execute(
            select(RefreshToken)
            .where(RefreshToken.id == next_id)
            .with_for_update()
        )
        nxt = sresult.scalar_one_or_none()
        if nxt is None:
            # successor_id pointed somewhere that's gone (the self-FK
            # cascade is SET NULL, so this means a row was deleted out
            # from under us — corrupt chain).
            raise errors.refresh_failed("bad_refresh_chain")
        current = nxt

    # Fell out of the loop — exceeded MAX_HOPS.
    raise errors.refresh_failed("bad_refresh_chain")


# =============================================================================
# Logout
# =============================================================================

async def logout(db: AsyncSession, user_id: int) -> None:
    """Revoke all sessions for the user.

    Caller MUST validate the access token before calling — we trust user_id is
    derived from a fully-validated bearer (session_version checked, exp
    verified). Bumping session_version invalidates already-minted access JWTs
    in other tabs/devices instead of leaving them live until exp.
    The one intentional exception is ``rotate_password`` (the M8 operator CLI),
    which is authenticated by ``fly ssh``, not by a JWT.

    Holds the session-issue lock exclusive, like a rotation, so a login or refresh in
    flight on another device commits first and its row is revoked here, rather than
    surviving a sign-out that promises every device (final review, M8 PR1b). Taken after
    the caller's bearer check, never before: an unauthenticated request must not queue
    behind or hold off sign-ins. Re-entrant, so ``rotate_password``, which already holds
    it, is unaffected.
    """
    await _hold_session_issue_lock(db, exclusive=True)
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(session_version=User.session_version + 1)
    )
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    await db.commit()


# =============================================================================
# Operator password rotation (M8 item 6)
# =============================================================================

class RotationRejected(Exception):
    """The rotation was refused before anything was written. The message is safe to print."""


@dataclass(frozen=True)
class RotationSummary:
    user_id: int
    tokens_revoked: int
    session_version: int


async def rotate_password(db: AsyncSession, email: str, new_password: str) -> RotationSummary:
    """Set a new household password and revoke every session, in one transaction.

    The hash is set on ``db`` and left for ``logout`` to commit: ``logout`` is the only
    commit, so the new hash, the ``session_version`` bump and the refresh-token revocation
    land together or not at all. It holds the session-issue lock exclusive from after hashing
    until that commit, so no login or refresh is in flight while it revokes (a session one
    of them committed afterwards would survive). Overlong input is refused before any hashing (argon2's
    128-character limit, ``PASSWORD_MAX_LENGTH``): a password login can never accept would
    lock the household out with the one tool that exists to let it back in.
    """
    if not new_password:
        raise RotationRejected("the new password is empty")
    if len(new_password) > PASSWORD_MAX_LENGTH:
        raise RotationRejected(f"the new password is longer than {PASSWORD_MAX_LENGTH} characters")
    # CITEXT column: case-insensitive, the same lookup login uses.
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        raise RotationRejected("no user with that email")

    new_hash = await passwords.hash_password(new_password)
    # Hashed first, so sign-ins wait only for the writes below. From here to logout()'s
    # commit no login or refresh can be in flight (see "Concurrency invariants").
    await _hold_session_issue_lock(db, exclusive=True)
    user.password_hash = new_hash
    live = await db.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    )
    await logout(db, user.id)
    version = await db.scalar(select(User.session_version).where(User.id == user.id))
    return RotationSummary(user_id=user.id, tokens_revoked=live, session_version=version)


# =============================================================================
# Status
# =============================================================================

async def auth_status(db: AsyncSession) -> bool:
    """Return whether the singleton account exists. Public — no auth."""
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one() > 0
