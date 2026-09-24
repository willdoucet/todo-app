"""Rotate the household password and sign every session out (M8 item 6).

Run it on a **web** machine, which has the app's secrets and dependencies::

    fly ssh console -a mealy-app-prod --select      # choose a `web` machine
    cd /app && /app/.venv/bin/python -m app.cli.rotate_password <email>

Two traps: use ``--select``, not ``-C "..."`` — the password prompt needs a TTY, which ``-C``
does not reliably allocate; and spell the interpreter absolutely — the prod image's
``PATH`` entry (``.venv/bin``) is relative, so a shell outside ``/app`` finds the system
``python``, which has none of the app's packages.

The new password is read from a prompt, twice, never from the command line (an argument is
visible in ``ps``). Every household session ends: each open tab is sent to the sign-in page
on its next request, so tell the household first — unless the rotation is because the
password leaked, in which case rotate first and tell them after (infra/RUNBOOK.md).

Exit codes: ``0`` rotated · ``1`` refused, nothing written (no such user, too long, empty,
confirmation mismatch) · ``2`` a database error (unreachable, or it refused the query), or any
error nobody anticipated (reported by its type only). After exit 2 the rotation may or may not
have landed: the connection can drop around the commit, or
the summary's read can fail after it. Try signing in with the new password before retrying.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from typing import Awaitable, Callable, Optional, Sequence, TextIO

from sqlalchemy.exc import DBAPIError, OperationalError

from app.auth.schemas import PASSWORD_MAX_LENGTH
from app.auth.service import RotationRejected, RotationSummary, rotate_password

# Any database-layer failure: unreachable (OperationalError, OSError, a timeout) or a refused
# query (ProgrammingError when a table is missing). Nothing was committed before it.
DATABASE_ERRORS = (DBAPIError, OSError, asyncio.TimeoutError)

Rotate = Callable[[str, str], Awaitable[RotationSummary]]


async def _rotate_with_app_database(email: str, new_password: str) -> RotationSummary:
    from app.database import AsyncSessionLocal, engine

    if AsyncSessionLocal is None:
        raise OperationalError("connect", {}, RuntimeError("DATABASE_URL is not set"))
    try:
        async with AsyncSessionLocal() as db:
            return await rotate_password(db, email, new_password)
    finally:
        # Pooled asyncpg connections must not outlive this event loop (REVIEW_CHECKLIST →
        # SQLAlchemy → Background jobs). A failed dispose must not replace the outcome: a
        # rotation that committed is not a failure because the pool would not close.
        if engine is not None:
            try:
                await engine.dispose()
            except Exception:
                pass


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    prompt: Callable[[str], str] = getpass.getpass,
    rotate: Rotate = _rotate_with_app_database,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.rotate_password",
        description="Set a new household password and revoke every session.",
    )
    parser.add_argument("email", help="the household account's email")
    args = parser.parse_args(argv)
    email = getattr(args, "email")

    first = prompt("New password: ")
    second = prompt("Repeat the new password: ")
    if first != second:
        print("error: the two passwords do not match; nothing was changed", file=err)
        return 1
    if not first:
        print("error: the new password is empty; nothing was changed", file=err)
        return 1
    if len(first) > PASSWORD_MAX_LENGTH:
        print(
            f"error: the new password is longer than {PASSWORD_MAX_LENGTH} characters, "
            "the most login accepts; nothing was changed",
            file=err,
        )
        return 1

    try:
        summary = asyncio.run(rotate(email, first))
    except RotationRejected as exc:
        print(f"error: {exc}; nothing was changed", file=err)
        return 1
    except DATABASE_ERRORS as exc:
        print(
            f"error: the database call failed ({type(exc).__name__}); the rotation may not have "
            "completed: try signing in with the new password before retrying",
            file=err,
        )
        return 2
    except Exception as exc:
        # REVIEW_CHECKLIST → Operator scripts: an error nobody anticipated is not exit 1
        # ("refused, nothing written", which is also Python's own crash code). It can come
        # after logout()'s commit, and a traceback can print the statement's parameters,
        # the new hash among them. The type only.
        print(
            f"error: unexpected {type(exc).__name__}; the rotation may not have completed: "
            "try signing in with the new password before retrying",
            file=err,
        )
        return 2

    print(
        f"rotated: user {summary.user_id}; {summary.tokens_revoked} refresh token(s) revoked; "
        f"session version is now {summary.session_version}",
        file=out,
    )
    print("all sessions revoked; the household must sign in with the new password", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
