"""Integration tests for the /upload API endpoints (M7 rewrite).

Post-Fork-3 reality: validation is magic-byte based, GIF is rejected, icons
cap at 1 MB and photos/recipe images at 5 MB, and every successful upload
writes an `assets` manifest row (referenced=false). The default `client`
fixture runs on LocalDiskBackend with UPLOAD_DIR pointed at a tmp dir by the
integration conftest.
"""

import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app import models
from app.storage import ObjectNotFound


def _mock_upload(content: bytes) -> MagicMock:
    """Mock UploadFile with async chunked .read() and no Content-Length."""
    f = MagicMock()
    f.size = None
    pos = {"i": 0}

    async def _read(n: int = -1) -> bytes:
        start = pos["i"]
        chunk = content[start:] if n < 0 else content[start:start + n]
        pos["i"] = start + len(chunk)
        return chunk

    f.read = AsyncMock(side_effect=_read)
    return f

# Valid magic-byte payloads (content after the signature is opaque).
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 64
GIF = b"GIF89a" + b"\x00" * 64


def _file(name: str, content: bytes, ctype: str = "image/png"):
    return {"file": (name, io.BytesIO(content), ctype)}


def _fail_nth_commit(session, n: int, exc: BaseException | None = None):
    """Let the first n-1 commits through, then raise.

    `store_upload` commits once to release the auth-dependency connection
    before `storage.put`, then again to persist the assets row. Compensating-
    delete tests must fail only that second commit, or put never runs.
    """
    remaining = {"i": n}
    real_commit = session.commit
    if exc is None:
        exc = RuntimeError("simulated DB failure")

    async def _commit():
        remaining["i"] -= 1
        if remaining["i"] <= 0:
            raise exc
        await real_commit()

    return _commit


# =============================================================================
# GET /upload/stock-icons
# =============================================================================

class TestListStockIcons:
    async def test_returns_stock_icons_list(self, client):
        response = await client.get("/upload/stock-icons")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5

    async def test_stock_icon_urls_keep_uploads_scheme(self, client):
        """M7: the /uploads/stock_icons/*.png scheme is UNCHANGED so
        already-adopted stock references keep resolving in PR2."""
        data = (await client.get("/upload/stock-icons")).json()
        for icon in data:
            assert icon["url"].startswith("/uploads/stock_icons/")
            assert icon["url"].endswith(".png")


# =============================================================================
# POST /upload/family-photo (5 MB cap)
# =============================================================================

class TestUploadFamilyPhoto:
    @pytest.mark.parametrize(
        "content,ext",
        [(PNG, ".png"), (JPEG, ".jpg"), (WEBP, ".webp")],
    )
    async def test_uploads_supported_formats(self, client, content, ext):
        resp = await client.post(
            "/upload/family-photo", files=_file(f"p{ext}", content)
        )
        assert resp.status_code == 200
        url = resp.json()["url"]
        assert url.startswith("/uploads/family_photos/")
        assert url.endswith(ext)

    async def test_rejects_gif_now(self, client):
        """M7 Fork 3 behavior change: GIF was accepted pre-M7, now 415."""
        resp = await client.post(
            "/upload/family-photo", files=_file("a.gif", GIF, "image/gif")
        )
        assert resp.status_code == 415

    async def test_rejects_faked_extension_binary(self, client):
        """A .png filename with non-image bytes is rejected on bytes (415),
        not the pre-M7 400-by-extension."""
        resp = await client.post(
            "/upload/family-photo", files=_file("evil.png", b"not an image")
        )
        assert resp.status_code == 415

    async def test_rejects_pdf(self, client):
        resp = await client.post(
            "/upload/family-photo",
            files=_file("doc.pdf", b"%PDF-1.4 fake", "application/pdf"),
        )
        assert resp.status_code == 415

    async def test_rejects_over_5mb(self, client):
        big = PNG + b"\x00" * (6 * 1024 * 1024)
        resp = await client.post(
            "/upload/family-photo", files=_file("huge.png", big)
        )
        assert resp.status_code == 413

    async def test_writes_assets_manifest_row(self, client, db_session):
        """Every successful upload records an unreferenced assets row."""
        resp = await client.post(
            "/upload/family-photo", files=_file("p.png", PNG)
        )
        key = resp.json()["url"].removeprefix("/uploads/")
        row = (
            await db_session.execute(
                select(models.Asset).where(models.Asset.key == key)
            )
        ).scalar_one()
        assert row.content_type == "image/png"
        assert row.size_bytes == len(PNG)
        assert row.referenced is False

    async def test_unique_filenames(self, client):
        u1 = (await client.post("/upload/family-photo", files=_file("a.png", PNG))).json()["url"]
        u2 = (await client.post("/upload/family-photo", files=_file("a.png", PNG))).json()["url"]
        assert u1 != u2


# =============================================================================
# POST /upload/responsibility-icon (1 MB icon cap)
# =============================================================================

class TestUploadResponsibilityIcon:
    async def test_uploads_valid_image(self, client):
        resp = await client.post(
            "/upload/responsibility-icon", files=_file("i.png", PNG)
        )
        assert resp.status_code == 200
        assert resp.json()["url"].startswith("/uploads/responsibility_icons/")

    async def test_icon_cap_is_1mb_not_5mb(self, client):
        """M7 per-type caps: icons cap at 1 MB. A 2 MB icon that would have
        passed the old shared 5 MB limit is now rejected."""
        two_mb = PNG + b"\x00" * (2 * 1024 * 1024)
        resp = await client.post(
            "/upload/responsibility-icon", files=_file("big.png", two_mb)
        )
        assert resp.status_code == 413


# =============================================================================
# POST /upload/recipe-image (5 MB cap)
# =============================================================================

class TestUploadRecipeImage:
    async def test_uploads_valid_image(self, client):
        resp = await client.post(
            "/upload/recipe-image", files=_file("r.webp", WEBP, "image/webp")
        )
        assert resp.status_code == 200
        assert resp.json()["url"].startswith("/uploads/recipe_images/")
        assert resp.json()["url"].endswith(".webp")


# =============================================================================
# Compensating transaction (no orphan on DB failure after a successful put)
# =============================================================================

class TestCompensatingDelete:
    async def test_db_failure_after_put_triggers_compensating_delete(
        self, db_session, monkeypatch, tmp_path
    ):
        """If the assets commit fails after storage.put succeeds, the
        just-written object must be deleted (no orphan). Tested by calling
        store_upload directly — avoids ASGITransport's raise_app_exceptions
        ambiguity, and asserts the object is actually gone from storage."""
        from app import uploads as uploads_mod
        from app.storage.local import LocalDiskBackend

        backend = LocalDiskBackend(root=tmp_path)
        put_keys: list[str] = []
        deleted: list[str] = []

        class SpyStorage:
            async def put(self, key, data, content_type):
                put_keys.append(key)
                await backend.put(key, data, content_type)

            async def get(self, key):
                return await backend.get(key)

            async def delete(self, key):
                deleted.append(key)
                await backend.delete(key)

        monkeypatch.setattr(uploads_mod, "get_storage", lambda: SpyStorage())

        # store_upload now commits twice: once to end the auth txn before
        # put, once to persist the assets row. Fail only the second.
        monkeypatch.setattr(db_session, "commit", _fail_nth_commit(db_session, 2))

        with pytest.raises(RuntimeError):
            await uploads_mod.store_upload(
                db_session, _mock_upload(PNG), "family_photos", max_bytes=5 * 1024 * 1024
            )

        assert len(put_keys) == 1
        # the compensating delete removed exactly the key that was put
        assert deleted == put_keys
        # and the object is actually gone from storage (no orphan)
        with pytest.raises(ObjectNotFound):
            await backend.get(put_keys[0])

    async def test_compensating_delete_failure_is_logged(
        self, db_session, monkeypatch, tmp_path, caplog
    ):
        """Mandated: if compensating delete ALSO fails, the original DB
        error still surfaces and the residual orphan is logged."""
        import logging

        from app import uploads as uploads_mod
        from app.storage.local import LocalDiskBackend

        backend = LocalDiskBackend(root=tmp_path)
        put_keys: list[str] = []

        class SpyStorage:
            async def put(self, key, data, content_type):
                put_keys.append(key)
                await backend.put(key, data, content_type)

            async def delete(self, key):
                raise RuntimeError("simulated storage delete failure")

        monkeypatch.setattr(uploads_mod, "get_storage", lambda: SpyStorage())
        monkeypatch.setattr(db_session, "commit", _fail_nth_commit(db_session, 2))

        caplog.set_level(logging.ERROR)
        with pytest.raises(RuntimeError, match="simulated DB failure"):
            await uploads_mod.store_upload(
                db_session, _mock_upload(PNG), "family_photos", max_bytes=5 * 1024 * 1024
            )

        assert len(put_keys) == 1
        assert "compensating delete FAILED" in caplog.text
        # residual orphan — object remains because delete also failed
        assert await backend.get(put_keys[0]) == PNG

    async def test_cancellation_after_put_still_compensates(
        self, db_session, monkeypatch, tmp_path
    ):
        """Client disconnect / task cancel after put must still delete the
        object — CancelledError is BaseException, not Exception."""
        import asyncio

        from app import uploads as uploads_mod
        from app.storage.local import LocalDiskBackend

        backend = LocalDiskBackend(root=tmp_path)
        put_keys: list[str] = []
        deleted: list[str] = []

        class SpyStorage:
            async def put(self, key, data, content_type):
                put_keys.append(key)
                await backend.put(key, data, content_type)

            async def delete(self, key):
                deleted.append(key)
                await backend.delete(key)

        monkeypatch.setattr(uploads_mod, "get_storage", lambda: SpyStorage())
        monkeypatch.setattr(
            db_session, "commit", _fail_nth_commit(db_session, 2, asyncio.CancelledError())
        )

        with pytest.raises(asyncio.CancelledError):
            await uploads_mod.store_upload(
                db_session, _mock_upload(PNG), "family_photos", max_bytes=5 * 1024 * 1024
            )

        assert deleted == put_keys
        with pytest.raises(ObjectNotFound):
            await backend.get(put_keys[0])

    async def test_db_transaction_ends_before_the_storage_put(
        self, db_session, monkeypatch, tmp_path
    ):
        """PR2 puts `storage.put` on R2. The auth-dependency SELECT must not
        hold a pooled connection across that call — same pool-starvation path
        the media read route closed. Call order, not transaction-state, because
        the test session runs in SAVEPOINT mode."""
        from app import uploads as uploads_mod
        from app.storage.local import LocalDiskBackend

        backend = LocalDiskBackend(root=tmp_path)
        calls: list[str] = []
        real_commit = db_session.commit

        async def spy_commit():
            calls.append("commit")
            await real_commit()

        monkeypatch.setattr(db_session, "commit", spy_commit)

        class SpyStorage:
            async def put(self, key, data, content_type):
                calls.append("storage.put")
                await backend.put(key, data, content_type)

            async def delete(self, key):
                raise AssertionError("delete must not run on the happy path")

        monkeypatch.setattr(uploads_mod, "get_storage", lambda: SpyStorage())

        url = await uploads_mod.store_upload(
            db_session, _mock_upload(PNG), "family_photos", max_bytes=5 * 1024 * 1024
        )
        assert url.startswith("/uploads/family_photos/")
        assert calls == ["commit", "storage.put", "commit"], calls
