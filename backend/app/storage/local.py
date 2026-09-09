"""Local-disk storage backend.

Wraps the pre-M7 ``/app/uploads`` disk writes behind the ``StorageBackend``
protocol. Used by dev + the visual-regression test stack (which must never
gain an R2 dependency), and by production through PR1 (the R2 flip is PR2).

``content_type`` is ignored on ``put`` — local disk stores no content-type;
the ``assets`` manifest is the authority (see ``storage/base.py``).
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import ObjectNotFound

# Same env var + default the pre-M7 upload code used, so PR1 keeps writing to
# the exact same location and the existing StaticFiles mount keeps serving it
# (no intermediate 404 window — mount removal is PR2).
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))


class LocalDiskBackend:
    """Objects are files at ``{root}/{key}``. ``root`` defaults to
    ``UPLOAD_DIR`` but is injectable so tests can point at a tmp dir."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = Path(root) if root is not None else UPLOAD_DIR

    def _path(self, key: str) -> Path:
        # Defense-in-depth: never let a key escape the storage root, even if a
        # caller passes an unvalidated key. `(root / key)` with an absolute or
        # `..`-laden key would otherwise resolve outside root (pathlib discards
        # the root when the right operand is absolute). Callers that reach the
        # delete hook are already filtered by `asset_lifecycle.managed_key`;
        # this is the backstop.
        root = self._root.resolve()
        path = (root / key).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"storage key escapes root: {key!r}")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def get(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError as exc:
            raise ObjectNotFound(key) from exc

    async def delete(self, key: str) -> None:
        # Idempotent by contract — a missing key is not an error.
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            pass
