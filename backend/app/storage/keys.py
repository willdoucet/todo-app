"""The storage-key contract — one canonical definition, three consumers.

A storage key is the logical path inside `/uploads/{key}`. Two disjoint kinds:

  **managed**  ``{subdir}/{uuid4}.{png|jpg|webp}`` — uploaded by a user, has an
               ``assets`` manifest row, lives in the storage backend
               (local disk or R2), and is deleted when nothing references it.

  **stock**    ``stock_icons/{name}.png`` — bundled in the container image at
               ``/app/stock_icons_src``. NO manifest row, never in R2, never
               deleted. Kept at the same ``/uploads/*`` URL scheme so entity
               columns that adopted a stock icon before M7 keep resolving.

Anything else is neither, and every consumer must refuse it.

Why this module exists (M7 PR2). Three call sites need "is this key valid?":

  1. ``services.asset_lifecycle.managed_key`` — before ``storage.delete``.
  2. ``routes.media`` — before ``storage.get``.
  3. ``uploads.store_upload`` — when minting a key.

The pre-landing review of PR1 found a CRITICAL here: unvalidated
``icon_url``/``photo_url``/``image_url`` (client-controlled strings) reaching
``storage.delete``, so ``/uploads/../../app/main.py`` deleted arbitrary files.
The fix was a regex in ``asset_lifecycle``. PR2 adds a SECOND path to storage
(the read proxy) — and per eng review CQ1's lesson about the session-validity
predicate, a security check copied into two modules drifts and silently
re-opens the hole. So the definition lives here, once.

The subdir allowlist is closed on purpose: ``store_upload`` has only ever
produced these four (stable since before M7 — verified against
``23d02ef~1``), so an unknown subdir is either a typo or an attack, never
legitimate data.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

#: Every subdir `store_upload` can produce. Closed set — adding an upload type
#: means adding it here, and the media route will 404 it until you do.
MANAGED_SUBDIRS = frozenset(
    {
        "item-icons",
        "family_photos",
        "responsibility_icons",
        "recipe_images",
    }
)

#: Extensions the magic-byte validator can emit (PNG / JPEG / WebP; GIF and
#: SVG are rejected at upload).
MANAGED_EXTENSIONS = ("png", "jpg", "webp")

STOCK_ICON_PREFIX = "stock_icons/"

#: Where bundled stock icons live in the image. The Dockerfile copies
#: `./stock_icons` here in the `builder` stage, so both `dev` and `prod` have
#: it. Overridable for tests.
STOCK_ICONS_DIR = Path(os.getenv("STOCK_ICONS_DIR", "/app/stock_icons_src"))

# `{subdir}/{uuid4}.{ext}` and nothing else. The subdir alternation is the
# allowlist; the uuid4 group is lowercase-hex only (what `uuid.uuid4()`
# stringifies to). Because neither group admits `.` or `/`, traversal (`../`),
# absolute keys (`/etc/passwd` — pathlib would discard the storage root), and
# empty segments all fail to match.
# NOTE the `\Z` terminator, not `$`: in Python `$` ALSO matches just before a
# trailing newline, so `item-icons/{uuid}.png\n` would classify as a valid
# managed key and be handed to storage as a key that cannot exist. `\Z` is
# true end-of-string. (Caught by tests/unit/test_storage_keys.py.)
_MANAGED_KEY_RE = re.compile(
    r"^(?:" + "|".join(sorted(re.escape(s) for s in MANAGED_SUBDIRS)) + r")/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"\.(?:" + "|".join(MANAGED_EXTENSIONS) + r")\Z"
)

# `stock_icons/{name}.png`. The name class excludes `.` and `/`, so this
# cannot escape STOCK_ICONS_DIR.
_STOCK_KEY_RE = re.compile(r"^stock_icons/[a-z0-9][a-z0-9-]*\.png\Z")


def is_managed_key(key: str) -> bool:
    """True for a well-formed uploaded-object key (has an ``assets`` row)."""
    return bool(_MANAGED_KEY_RE.match(key))


def is_stock_icon_key(key: str) -> bool:
    """True for a well-formed bundled-stock-icon key (no ``assets`` row)."""
    return bool(_STOCK_KEY_RE.match(key))


def stock_icon_path(key: str) -> Path:
    """Resolve a stock-icon key to its on-disk path in the image.

    Raises ``ValueError`` for a key that is not a valid stock-icon key, and
    again (defense-in-depth) if the resolved path somehow escapes
    ``STOCK_ICONS_DIR``.
    """
    if not is_stock_icon_key(key):
        raise ValueError(f"not a stock-icon key: {key!r}")
    root = STOCK_ICONS_DIR.resolve()
    path = (root / key[len(STOCK_ICON_PREFIX):]).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"stock-icon key escapes root: {key!r}")
    return path
