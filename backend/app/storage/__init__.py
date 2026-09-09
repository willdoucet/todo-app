"""Storage backend selection.

``get_storage()`` returns the backend chosen by the ``STORAGE_BACKEND`` env
var (``local`` | ``r2``), defaulting to ``local`` so an unset dev/test env
never reaches for R2. Callers (upload endpoints, the asset-lifecycle hooks,
the abandoned-upload sweep) depend only on the ``StorageBackend`` protocol.

  STORAGE_BACKEND unset / "local"  →  LocalDiskBackend(UPLOAD_DIR)
  STORAGE_BACKEND == "r2"          →  R2Backend()  (prod, PR2)

The env is read on every call so a test can flip it per-case; the R2 client
(the only expensive-to-build backend) is cached across calls. Unknown values
raise rather than silently falling back to local disk (a typo at the PR2
``STORAGE_BACKEND=r2`` flip would otherwise write to ephemeral disk).
"""

from __future__ import annotations

import os

from .base import ObjectNotFound, StorageBackend
from .local import LocalDiskBackend

__all__ = ["StorageBackend", "ObjectNotFound", "LocalDiskBackend", "get_storage"]

_r2_singleton: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Return the configured storage backend (FastAPI-dependency compatible)."""
    backend = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend == "r2":
        global _r2_singleton
        if _r2_singleton is None:
            from .r2 import R2Backend

            _r2_singleton = R2Backend()
        return _r2_singleton
    if backend in ("", "local"):
        # LocalDiskBackend is cheap to construct. UPLOAD_DIR is captured at
        # `local.py` import time; tests that need a tmp root either set
        # UPLOAD_DIR before import (integration conftest) or inject `root=`.
        return LocalDiskBackend()
    raise ValueError(
        f"Unknown STORAGE_BACKEND={backend!r}; expected 'local' or 'r2'"
    )
