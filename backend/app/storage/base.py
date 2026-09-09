"""Storage backend abstraction (M7 — object-storage productionization).

A deliberately minimal object-store protocol, sized for a single-family
instance (a handful of ≤5 MB images, ever). Two implementations:

  - ``LocalDiskBackend`` — files under ``UPLOAD_DIR``. Used by dev, test, and
    (through M7 PR1) production.
  - ``R2Backend`` — Cloudflare R2 (S3-compatible) via boto3. Enabled in
    production in PR2 (``STORAGE_BACKEND=r2``).

Keys are *logical* paths like ``item-icons/{uuid4}.png``. One key is
simultaneously:
  - the storage object key,
  - the primary key of the ``assets`` manifest row, and
  - the tail of the public ``/uploads/{key}`` URL.

    put(key, data, content_type)   store bytes (idempotent overwrite)
    get(key) -> bytes              read bytes; raises ObjectNotFound if absent
    delete(key)                    remove; idempotent (missing key is OK)

``content_type`` is accepted on ``put`` for a uniform interface, but the
authoritative content-type lives in the ``assets`` manifest, not in storage
(``LocalDiskBackend`` stores none). The PR2 read proxy reads content-type from
the manifest, never from the backend.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class ObjectNotFound(Exception):
    """Raised by ``get`` when a key has no stored object.

    The PR2 media read proxy maps this to a 404, distinct from a
    storage-unreachable error (boto3 / network failure) which surfaces as a
    5xx. ``delete`` never raises this — it is idempotent by contract.
    """


@runtime_checkable
class StorageBackend(Protocol):
    """The object-store contract. Async throughout because the backend is
    async SQLAlchemy and boto3 (sync) must be bounced through a threadpool."""

    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...
