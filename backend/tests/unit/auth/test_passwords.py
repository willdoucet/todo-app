"""Unit tests for app.auth.passwords.

Covers:
- hash + verify roundtrip (async via asyncio.to_thread)
- verify_or_dummy returns False on wrong-password / invalid-hash / unknown-user
- Dummy-hash lazy-cache mechanism (Eng review 3):
  * first unknown-email call generates the dummy via the currently-active hasher
  * subsequent calls reuse the cached dummy (hash() not called again)
  * set_password_hasher invalidates the cache and the next call regenerates
"""

from __future__ import annotations

import pytest
from argon2 import PasswordHasher

from app.auth import passwords


def _make_fast_hasher() -> PasswordHasher:
    """Tiny argon2 params for fast tests. Production uses OWASP defaults."""
    return PasswordHasher(memory_cost=8, time_cost=1, parallelism=1)


@pytest.fixture
def fast_hasher() -> PasswordHasher:
    return _make_fast_hasher()


@pytest.fixture(autouse=True)
def reset_hasher_state(fast_hasher):
    """Each test gets a fresh fast hasher and a clean dummy cache."""
    passwords.set_password_hasher(fast_hasher)
    yield
    # Restore default OWASP-params hasher between tests.
    passwords.set_password_hasher(PasswordHasher())


@pytest.mark.asyncio
async def test_hash_and_verify_roundtrip(fast_hasher):
    h = await passwords.hash_password("correct-horse-battery-staple")
    assert await passwords.verify_or_dummy(h, "correct-horse-battery-staple") is True


@pytest.mark.asyncio
async def test_verify_returns_false_on_wrong_password(fast_hasher):
    h = await passwords.hash_password("password-one")
    assert await passwords.verify_or_dummy(h, "password-two") is False


@pytest.mark.asyncio
async def test_verify_returns_false_on_invalid_hash():
    """argon2.exceptions.InvalidHashError must collapse to False (Eng review 1)."""
    assert await passwords.verify_or_dummy("not-a-valid-argon2-phc-string", "anything") is False


@pytest.mark.asyncio
async def test_verify_returns_false_on_unknown_user():
    """When stored_hash is None, the dummy code path runs but always returns False."""
    assert await passwords.verify_or_dummy(None, "anything") is False


class _SpyHasher:
    """Test-only wrapper that records ``hash()`` calls. We can't monkeypatch
    PasswordHasher.hash directly because argon2-cffi marks it read-only, so
    swap in a wrapper instead. Tests duck-type — passwords.py only calls
    ``hash()`` and ``verify()`` on the active hasher."""

    def __init__(self, inner: PasswordHasher):
        self._inner = inner
        self.hash_calls: list[str] = []

    def hash(self, value: str) -> str:
        self.hash_calls.append(value)
        return self._inner.hash(value)

    def verify(self, stored_hash: str, plaintext: str) -> bool:
        return self._inner.verify(stored_hash, plaintext)


@pytest.mark.asyncio
async def test_dummy_hash_lazy_generation():
    """First unknown-email call generates the dummy with the currently-active
    hasher. Subsequent calls reuse the cached dummy."""
    spy = _SpyHasher(_make_fast_hasher())
    passwords.set_password_hasher(spy)

    # First unknown-user verify — generates the dummy lazily.
    await passwords.verify_or_dummy(None, "any-password")
    assert len(spy.hash_calls) == 1, (
        "Dummy hash should be generated lazily on first verify_or_dummy(None, ...)"
    )

    # Second unknown-user verify — reuses cached dummy.
    await passwords.verify_or_dummy(None, "another-password")
    assert len(spy.hash_calls) == 1, (
        "Cached dummy hash should be reused; hasher.hash should not be called again"
    )


@pytest.mark.asyncio
async def test_set_password_hasher_invalidates_dummy_cache(fast_hasher):
    """Replacing the hasher invalidates the cache; next verify regenerates."""
    # Populate cache with fast_hasher's dummy.
    await passwords.verify_or_dummy(None, "anything")
    assert passwords._dummy_hash_cache is not None
    cached_before = passwords._dummy_hash_cache

    # Replace hasher.
    new_hasher = _make_fast_hasher()
    passwords.set_password_hasher(new_hasher)
    assert passwords._dummy_hash_cache is None, "Cache must be invalidated on hasher swap"

    # Next call regenerates with the new hasher.
    await passwords.verify_or_dummy(None, "anything")
    assert passwords._dummy_hash_cache is not None
    # The PHC string includes a random salt, so two argon2 hashes of the same
    # plaintext are virtually guaranteed to differ.
    assert passwords._dummy_hash_cache != cached_before


def test_get_password_hasher_returns_module_instance(fast_hasher):
    assert passwords.get_password_hasher() is fast_hasher


@pytest.mark.asyncio
async def test_hash_password_uses_currently_active_hasher(fast_hasher):
    """hash_password() must read through to the live module-level hasher
    (so a set_password_hasher swap takes effect immediately)."""
    new_hasher = _make_fast_hasher()
    passwords.set_password_hasher(new_hasher)
    h = await passwords.hash_password("plaintext")
    # Verifying with the new hasher should succeed.
    assert new_hasher.verify(h, "plaintext")


@pytest.mark.asyncio
async def test_argon2_calls_run_off_event_loop(fast_hasher, monkeypatch):
    """asyncio.to_thread is what keeps the event loop responsive — verify
    we're using it for both hash and verify so a future refactor that
    accidentally calls argon2 directly fails this regression test."""
    import asyncio

    to_thread_calls: list[str] = []
    real_to_thread = asyncio.to_thread

    async def spy_to_thread(func, *args, **kwargs):
        to_thread_calls.append(getattr(func, "__name__", repr(func)))
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", spy_to_thread)

    # hash_password should dispatch via to_thread.
    await passwords.hash_password("plaintext")
    assert any("hash" in name or "PasswordHasher" in name for name in to_thread_calls), (
        f"hash_password must run argon2 via asyncio.to_thread; got {to_thread_calls}"
    )

    # verify_or_dummy with real hash should dispatch via to_thread.
    h = await passwords.hash_password("plaintext")
    to_thread_calls.clear()
    await passwords.verify_or_dummy(h, "plaintext")
    assert to_thread_calls, "verify_or_dummy must run argon2 via asyncio.to_thread"
