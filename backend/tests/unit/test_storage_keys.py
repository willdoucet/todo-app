"""Unit tests for `app.storage.keys` — the storage-key contract.

Why these are unit tests and not route tests: a conforming HTTP client
normalizes literal `../` dot-segments out of a URL path before the request is
sent (verified against httpx), so `GET /uploads/item-icons/../../app/main.py`
never arrives at the server as a traversal — it arrives as a different path
entirely and 404s on no route match. A route-level test for that shape would
pass without the validator existing at all.

The traversal defense is therefore pinned HERE, where nothing normalizes the
input, and the route tests cover only the shapes that genuinely survive
transport (percent-encoded traversal, leading-slash absolute keys, unknown
subdirs, malformed names). Both halves are needed; neither is redundant.
"""

from __future__ import annotations

import pytest

from app.storage import keys as k

VALID_UUID = "0190a1b2-c3d4-4e5f-8a9b-0c1d2e3f4a5b"


# =============================================================================
# is_managed_key
# =============================================================================

@pytest.mark.parametrize("subdir", sorted(k.MANAGED_SUBDIRS))
@pytest.mark.parametrize("ext", k.MANAGED_EXTENSIONS)
def test_every_allowlisted_subdir_and_extension_is_valid(subdir, ext):
    assert k.is_managed_key(f"{subdir}/{VALID_UUID}.{ext}")


@pytest.mark.parametrize(
    "key",
    [
        pytest.param(f"item-icons/../../app/main.py", id="traversal"),
        pytest.param(f"item-icons/../{VALID_UUID}.png", id="traversal-single"),
        pytest.param(f"../{VALID_UUID}.png", id="traversal-bare"),
        pytest.param(f"/etc/passwd", id="absolute"),
        pytest.param(f"/item-icons/{VALID_UUID}.png", id="absolute-leading-slash"),
        pytest.param(f"item-icons//{VALID_UUID}.png", id="empty-segment"),
        pytest.param(f"stock_icons/{VALID_UUID}.png", id="stock-is-not-managed"),
        pytest.param(f"unknown-subdir/{VALID_UUID}.png", id="unknown-subdir"),
        pytest.param(f"item-icons/{VALID_UUID}.gif", id="gif-rejected"),
        pytest.param(f"item-icons/{VALID_UUID}.svg", id="svg-rejected"),
        pytest.param(f"item-icons/{VALID_UUID}", id="no-extension"),
        pytest.param("item-icons/not-a-uuid.png", id="non-uuid"),
        pytest.param(f"item-icons/{VALID_UUID.upper()}.png", id="uppercase-uuid"),
        pytest.param(f"item-icons/{VALID_UUID}.png.png", id="double-extension"),
        pytest.param(f"item-icons/{VALID_UUID}.png ", id="trailing-space"),
        pytest.param(f"item-icons/{VALID_UUID}.png\n", id="trailing-newline"),
        pytest.param(f"item-icons/sub/{VALID_UUID}.png", id="nested"),
        pytest.param("", id="empty"),
    ],
)
def test_malformed_keys_are_not_managed(key):
    """Each of these, if it classified as managed, would reach `storage.get`
    or `storage.delete` — the latter being the arbitrary-file-delete CRITICAL
    that PR1's pre-landing review found."""
    assert not k.is_managed_key(key)


@pytest.mark.asyncio
async def test_store_upload_refuses_a_subdir_outside_the_allowlist():
    """The other half of the coupling above. `store_upload` fails at the write
    site rather than minting a key the media route would 404 forever — and it
    fails BEFORE reading the file or touching storage, so `db`/`file` can be
    None."""
    from app.uploads import store_upload

    with pytest.raises(ValueError, match="MANAGED_SUBDIRS"):
        await store_upload(None, None, "not-a-real-subdir", max_bytes=1024)


def test_managed_subdirs_matches_the_upload_call_sites():
    """The allowlist is closed. If an upload type is added without extending
    this set, `store_upload` raises and the media route 404s — this test names
    the coupling so the failure is understood, not just observed."""
    assert k.MANAGED_SUBDIRS == {
        "item-icons",
        "family_photos",
        "responsibility_icons",
        "recipe_images",
    }


# =============================================================================
# is_stock_icon_key / stock_icon_path
# =============================================================================

@pytest.mark.parametrize(
    "name", ["homework", "brush-teeth", "get-dressed", "make-bed", "take-bath"]
)
def test_bundled_stock_icon_names_are_valid(name):
    assert k.is_stock_icon_key(f"stock_icons/{name}.png")


@pytest.mark.parametrize(
    "key",
    [
        pytest.param("stock_icons/../../app/main.py", id="traversal"),
        pytest.param("stock_icons/../secrets.png", id="traversal-single"),
        pytest.param("stock_icons/sub/dir.png", id="nested"),
        pytest.param("stock_icons/homework.jpg", id="non-png"),
        pytest.param("stock_icons/homework", id="no-extension"),
        pytest.param("stock_icons/", id="empty-name"),
        pytest.param("stock_icons/-leading-dash.png", id="leading-dash"),
        pytest.param("stock_icons/UPPER.png", id="uppercase"),
        pytest.param("stock_icons/homework.png\n", id="trailing-newline"),
        pytest.param("stock_icons/homework.png ", id="trailing-space"),
        pytest.param("stock_icons/with_underscore.png", id="underscore"),
        pytest.param("/stock_icons/homework.png", id="absolute"),
        pytest.param(f"item-icons/{VALID_UUID}.png", id="managed-is-not-stock"),
    ],
)
def test_malformed_stock_keys_are_rejected(key):
    assert not k.is_stock_icon_key(key)


def test_stock_icon_path_resolves_inside_the_bundle_dir():
    path = k.stock_icon_path("stock_icons/homework.png")
    assert path.name == "homework.png"
    assert path.is_relative_to(k.STOCK_ICONS_DIR.resolve())


@pytest.mark.parametrize(
    "key", ["stock_icons/../../app/main.py", "item-icons/x.png", "", "stock_icons/"]
)
def test_stock_icon_path_refuses_invalid_keys(key):
    """Defense-in-depth: even if a caller skipped `is_stock_icon_key`, the path
    resolver refuses rather than reading an arbitrary file."""
    with pytest.raises(ValueError):
        k.stock_icon_path(key)


def test_managed_and_stock_key_spaces_are_disjoint():
    """A key must never be both — the route branches on stock first, so an
    overlap would let a stock-shaped key skip the manifest lookup."""
    samples = [
        f"item-icons/{VALID_UUID}.png",
        "stock_icons/homework.png",
        f"stock_icons/{VALID_UUID}.png",
    ]
    for key in samples:
        assert not (k.is_managed_key(key) and k.is_stock_icon_key(key)), key
