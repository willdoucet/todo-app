"""Shared bits for design-sync-check and design-sync-mark."""

from __future__ import annotations

from pathlib import Path

import _lib

MARKER_NAME = "design-system-synced.json"
DISABLED_MESSAGE = "design-sync: module disabled"


def enabled(cfg: dict) -> bool:
    return bool(cfg.get("modules", {}).get("design_sync", False))


def marker_path(root: Path, cfg: dict) -> Path:
    return _lib.state_dir(root, cfg) / MARKER_NAME


def watched_files(cfg: dict) -> list[str]:
    files = cfg.get("design_watched_files") or []
    if not files:
        raise _lib.FrameworkError("config design_watched_files is empty; nothing to watch", code=2)
    return list(files)


def design_sha(root: Path, files: list[str]) -> str:
    """Last commit touching any watched file, else HEAD."""
    sha = _lib.git(root, "log", "-1", "--format=%H", "--", *files)
    return sha or _lib.git(root, "rev-parse", "HEAD")
