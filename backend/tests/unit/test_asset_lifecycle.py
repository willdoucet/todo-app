"""Unit tests for the asset-lifecycle key classifier (M7).

`managed_key` decides what gets cleaned up. Its correctness IS the stock-icon
carve-out: stock icons and external URLs must classify as unmanaged so they're
never deleted.
"""

import uuid

import pytest

from app.services.asset_lifecycle import managed_key

_UUID = "12345678-1234-1234-1234-123456789abc"  # canonical uuid4 shape


class TestManagedKey:
    @pytest.mark.parametrize(
        "url,expected",
        [
            # Well-formed managed uploads → the key (url minus /uploads/).
            (f"/uploads/item-icons/{_UUID}.png", f"item-icons/{_UUID}.png"),
            (f"/uploads/family_photos/{_UUID}.jpg", f"family_photos/{_UUID}.jpg"),
            (f"/uploads/responsibility_icons/{_UUID}.webp", f"responsibility_icons/{_UUID}.webp"),
            (f"/uploads/recipe_images/{_UUID}.png", f"recipe_images/{_UUID}.png"),
        ],
    )
    def test_wellformed_managed_uploads_return_key(self, url, expected):
        assert managed_key(url) == expected

    def test_real_uuid_key_from_store_upload_classifies_managed(self):
        key = f"item-icons/{uuid.uuid4()}.png"
        assert managed_key(f"/uploads/{key}") == key

    @pytest.mark.parametrize(
        "url",
        [
            None,
            "",
            # Stock icons — bundled, unmanaged, must NEVER be deleted.
            "/uploads/stock_icons/homework.png",
            "/uploads/stock_icons/brush-teeth.png",
            # External URLs (e.g. scraped recipe images).
            "https://example.com/some/recipe.jpg",
            "http://cdn.example.com/a.png",
            # Not an uploads path.
            "/static/logo.png",
            "just-a-string",
            # Malformed managed shapes (no uuid / wrong ext) → unmanaged.
            "/uploads/item-icons/abc.png",
            f"/uploads/item-icons/{_UUID}.gif",
            f"/uploads/item-icons/{_UUID}.svg",
            "/uploads/item-icons/",
        ],
    )
    def test_unmanaged_return_none(self, url):
        assert managed_key(url) is None

    @pytest.mark.parametrize(
        "url",
        [
            # PATH TRAVERSAL — must classify as unmanaged so release() never
            # calls storage.delete() on them (arbitrary-file-delete regression).
            "/uploads/../../etc/passwd",
            "/uploads/../../../app/app/main.py",
            "/uploads//etc/passwd",                 # leading slash → pathlib would drop root
            f"/uploads/../{_UUID}.png",
            f"/uploads/item-icons/../../{_UUID}.png",
        ],
    )
    def test_traversal_keys_are_unmanaged(self, url):
        assert managed_key(url) is None
