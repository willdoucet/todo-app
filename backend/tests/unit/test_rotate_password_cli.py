"""``python -m app.cli.rotate_password`` — prompts, refusals and exit codes (M8 item 6).

The rotation itself has integration tests (``tests/integration/auth/test_rotate_password.py``);
here it is replaced, so these tests check only what the operator sees and the exit code.
"""

from __future__ import annotations

import io

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError, StatementError

from app.auth.service import RotationRejected, RotationSummary
from app.cli import rotate_password as cli

SECRET_PASSWORD = "brand-new-household-password"


def run(argv, answers, rotate=None):
    prompts, calls = iter(answers), []

    async def fake_rotate(email, password):
        calls.append((email, password))
        if rotate is not None:
            return await rotate(email, password)
        return RotationSummary(user_id=1, tokens_revoked=3, session_version=5)

    out, err = io.StringIO(), io.StringIO()
    code = cli.main(argv, prompt=lambda _: next(prompts), rotate=fake_rotate, out=out, err=err)
    return code, out.getvalue(), err.getvalue(), calls


def test_success_prints_the_summary_and_never_the_password():
    code, out, err, calls = run(["household@example.com"], [SECRET_PASSWORD, SECRET_PASSWORD])
    assert code == 0
    assert calls == [("household@example.com", SECRET_PASSWORD)]
    assert "user 1; 3 refresh token(s) revoked; session version is now 5" in out
    assert out.rstrip().endswith("all sessions revoked; the household must sign in with the new password")
    assert SECRET_PASSWORD not in out + err


def test_a_confirmation_mismatch_writes_nothing():
    code, out, err, calls = run(["household@example.com"], [SECRET_PASSWORD, SECRET_PASSWORD + "x"])
    assert (code, calls) == (1, [])
    assert "do not match; nothing was changed" in err


@pytest.mark.parametrize(("password", "message"), [("z" * 129, "longer than 128"), ("", "empty")])
def test_an_unusable_password_is_refused_before_the_database(password, message):
    code, _, err, calls = run(["household@example.com"], [password, password])
    assert (code, calls) == (1, [])
    assert message in err


def test_an_unknown_email_exits_1():
    async def refuse(email, password):
        raise RotationRejected("no user with that email")

    code, _, err, _ = run(["nobody@example.com"], [SECRET_PASSWORD, SECRET_PASSWORD], rotate=refuse)
    assert code == 1
    assert "no user with that email; nothing was changed" in err


@pytest.mark.parametrize(
    "error",
    [
        OperationalError("SELECT 1", {}, ConnectionRefusedError()),
        ProgrammingError("SELECT users", {}, Exception('relation "users" does not exist')),
        ConnectionRefusedError(),
        TimeoutError(),
    ],
)
def test_a_database_error_exits_2(error):
    async def down(email, password):
        raise error

    code, _, err, _ = run(["household@example.com"], [SECRET_PASSWORD, SECRET_PASSWORD], rotate=down)
    assert code == 2
    assert "the database call failed" in err
    # Never "did not complete": the connection can drop around the commit (review, M8 PR1b).
    assert "the rotation may not have completed: try signing in with the new password" in err


@pytest.mark.parametrize(
    "error",
    [
        StatementError("UPDATE users SET password_hash=%(h)s", "UPDATE users", {"h": "$argon2id$v=19$m=secret-hash"}, ValueError()),
        RuntimeError("argon2 hashing failed"),
    ],
)
def test_an_unanticipated_error_exits_2_with_its_type_only(error):
    """REVIEW_CHECKLIST → Operator scripts: Python's own crash exit is 1, which this tool
    documents as "refused, nothing written", and the error can come after logout()'s commit.
    A StatementError's text also carries the statement's parameters (final review, M8 PR1b)."""
    async def boom(email, password):
        raise error

    code, out, err, _ = run(["household@example.com"], [SECRET_PASSWORD, SECRET_PASSWORD], rotate=boom)
    assert code == 2
    assert f"unexpected {type(error).__name__}" in err
    assert "the rotation may not have completed: try signing in with the new password" in err
    assert "secret-hash" not in out + err and "password_hash" not in out + err


def test_a_failed_pool_dispose_after_a_rotation_still_reports_it_rotated(monkeypatch):
    """The real database path: the rotation returned, then the pool refused to close. That
    is not a failed rotation, and exit 2 would tell the operator the old password still works."""
    import app.database as database

    class Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *exc):
            return False

    class Engine:
        disposed = False

        async def dispose(self):
            Engine.disposed = True
            raise OSError("socket closed")

    async def rotated(db, email, password):
        return RotationSummary(user_id=1, tokens_revoked=2, session_version=7)

    monkeypatch.setattr(database, "AsyncSessionLocal", Session)
    monkeypatch.setattr(database, "engine", Engine())
    monkeypatch.setattr(cli, "rotate_password", rotated)
    out, err = io.StringIO(), io.StringIO()
    prompts = iter([SECRET_PASSWORD, SECRET_PASSWORD])
    code = cli.main(["household@example.com"], prompt=lambda _: next(prompts), out=out, err=err)
    assert Engine.disposed  # negative control: the failing dispose really ran
    assert (code, err.getvalue()) == (0, "")
    assert "session version is now 7" in out.getvalue()


def test_the_password_is_never_an_argument():
    """An argument is visible in `ps`; the parser accepts the email and nothing else."""
    with pytest.raises(SystemExit):
        cli.main(["household@example.com", SECRET_PASSWORD], prompt=lambda _: "", rotate=None)
