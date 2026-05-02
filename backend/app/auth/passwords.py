"""Password hashing + the timing-oracle defense.

The module-level ``_password_hasher`` is the canonical argon2 instance.
Production keeps the OWASP defaults; tests swap it for a fast-params
instance via :func:`set_password_hasher`.

:func:`verify_or_dummy` is the timing-oracle defense: on login for an
unknown email we still call argon2.verify against a lazily-cached dummy
hash so "wrong-email" and "wrong-password" share a latency profile. The
dummy is generated **on first miss using the currently-active hasher**,
so production timing matches production params and test timing matches
test params. The cache invalidates whenever the hasher is replaced.

Async via thread pool: ``hash_password`` and ``verify_or_dummy`` await
``asyncio.to_thread`` so the CPU-bound argon2 work doesn't block the
asyncio event loop. Without the thread offload, a single in-flight
argon2 verify (~50ms with OWASP defaults) freezes every other request
on the same worker — under a distributed burst that bypasses Cloudflare's
per-IP rate limit, this becomes a household-scale DoS amplifier.
Adversarial review (post-implementation, 2026-05-02).
"""

from __future__ import annotations

import asyncio
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

# Module-level injectable. Production defaults; tests replace via set_password_hasher.
_password_hasher: PasswordHasher = PasswordHasher()
_dummy_hash_cache: Optional[str] = None
# Track which hasher generated the cached dummy so we can detect overrides.
_dummy_hash_cache_hasher_id: Optional[int] = None

# Constant string used for the dummy hash — never logged, never user-visible.
_DUMMY_PLAINTEXT = "dummy-plaintext-for-timing-oracle-defense"


def get_password_hasher() -> PasswordHasher:
    """FastAPI dependency. Endpoint code calls
    ``Depends(get_password_hasher)`` so test code can override via
    ``app.dependency_overrides``."""
    return _password_hasher


def set_password_hasher(hasher: PasswordHasher) -> None:
    """Replace the module-level hasher. Invalidates the dummy-hash cache so
    the next :func:`verify_or_dummy` call regenerates with the new hasher's
    parameters."""
    global _password_hasher, _dummy_hash_cache, _dummy_hash_cache_hasher_id
    _password_hasher = hasher
    _dummy_hash_cache = None
    _dummy_hash_cache_hasher_id = None


def _get_dummy_hash_sync() -> str:
    """Lazily compute the dummy hash (synchronous; runs inside the thread
    pool). Regenerates whenever the active hasher object changes."""
    global _dummy_hash_cache, _dummy_hash_cache_hasher_id
    hasher = _password_hasher
    if _dummy_hash_cache is None or _dummy_hash_cache_hasher_id != id(hasher):
        _dummy_hash_cache = hasher.hash(_DUMMY_PLAINTEXT)
        _dummy_hash_cache_hasher_id = id(hasher)
    return _dummy_hash_cache


async def hash_password(plaintext: str) -> str:
    """Hash a plaintext password with the currently-active hasher. Argon2
    is CPU-bound — runs in the default thread pool via
    :func:`asyncio.to_thread` so it doesn't block the event loop."""
    return await asyncio.to_thread(_password_hasher.hash, plaintext)


async def verify_or_dummy(stored_hash: Optional[str], plaintext: str) -> bool:
    """Constant-shape password check.

    - ``stored_hash is None`` (unknown email path) → verify against the
      cached dummy hash; always returns False, but spends real argon2 time.
    - ``stored_hash`` is a real argon2 PHC string → verify normally.

    All three argon2 failure exceptions
    (:class:`VerifyMismatchError`, :class:`VerificationError`,
    :class:`InvalidHashError`) collapse to ``False``. The login handler
    therefore can't distinguish them in its log line, which is the whole
    point — anything more granular leaks user existence.

    Both the dummy-hash compute (on first miss) and the verify call run
    inside :func:`asyncio.to_thread` so the event loop stays responsive
    under burst load.
    """
    if stored_hash is None:
        target = await asyncio.to_thread(_get_dummy_hash_sync)
    else:
        target = stored_hash

    def _verify_sync() -> bool:
        try:
            return _password_hasher.verify(target, plaintext)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    return await asyncio.to_thread(_verify_sync)
