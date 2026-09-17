"""Integration tests for the M7 asset lifecycle: adopt / replace / delete
hooks across entity write paths, the stock-icon carve-out, and the
abandoned-upload sweep. Exercised end-to-end via the real endpoints + storage.
"""

import io
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, update

from app import models
from app.services import asset_lifecycle
from app.storage import ObjectNotFound, get_storage

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def _upload(client, endpoint="/upload/responsibility-icon"):
    """Upload a PNG, return (url, key). Creates an object + assets row."""
    resp = await client.post(
        endpoint, files={"file": ("i.png", io.BytesIO(PNG), "image/png")}
    )
    assert resp.status_code == 200, resp.text
    url = resp.json()["url"]
    return url, url.removeprefix("/uploads/")


def _resp_payload(fm_id, icon_url=None):
    return {
        "title": "Tidy room",
        "categories": ["MORNING"],
        "assigned_to": fm_id,
        "frequency": ["monday"],
        "icon_url": icon_url,
    }


async def _asset(db, key):
    return (
        await db.execute(select(models.Asset).where(models.Asset.key == key))
    ).scalar_one_or_none()


class TestAdopt:
    async def test_create_flips_referenced_true(self, client, db_session, test_family_member):
        url, key = await _upload(client)
        assert (await _asset(db_session, key)).referenced is False  # unadopted

        resp = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, url)
        )
        assert resp.status_code == 201, resp.text
        assert (await _asset(db_session, key)).referenced is True

    async def test_unknown_managed_key_rejects_create(
        self, client, test_family_member
    ):
        """Fail-closed: a well-formed URL with no assets row must not
        silently save a dead image link (e.g. upload then save after the
        24h abandoned-upload sweep already reclaimed it)."""
        fake = f"/uploads/responsibility_icons/{uuid.uuid4()}.png"
        resp = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, fake)
        )
        assert resp.status_code == 400
        assert "upload" in resp.json()["detail"].lower()


class TestReplace:
    async def test_replacing_icon_deletes_old_object_and_row(
        self, client, db_session, test_family_member
    ):
        old_url, old_key = await _upload(client)
        new_url, new_key = await _upload(client)

        created = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, old_url)
        )
        rid = created.json()["id"]

        patch = await client.patch(f"/responsibilities/{rid}", json={"icon_url": new_url})
        assert patch.status_code == 200, patch.text

        # old object + row reclaimed
        assert await _asset(db_session, old_key) is None
        with pytest.raises(ObjectNotFound):
            await get_storage().get(old_key)
        # new object adopted + still present
        assert (await _asset(db_session, new_key)).referenced is True
        assert await get_storage().get(new_key) == PNG

    async def test_unchanged_icon_is_not_released(
        self, client, db_session, test_family_member
    ):
        url, key = await _upload(client)
        created = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, url)
        )
        rid = created.json()["id"]
        # PATCH something else; icon_url unchanged → object must survive.
        await client.patch(f"/responsibilities/{rid}", json={"title": "Renamed"})
        assert (await _asset(db_session, key)).referenced is True
        assert await get_storage().get(key) == PNG


class TestDelete:
    async def test_delete_releases_icon(self, client, db_session, test_family_member):
        url, key = await _upload(client)
        created = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, url)
        )
        rid = created.json()["id"]

        resp = await client.delete(f"/responsibilities/{rid}")
        assert resp.status_code == 204
        assert await _asset(db_session, key) is None
        with pytest.raises(ObjectNotFound):
            await get_storage().get(key)

    async def test_release_keeps_row_when_storage_delete_fails(
        self, client, db_session, test_family_member, monkeypatch
    ):
        """If storage.delete fails, keep the unreferenced row so sweep retries."""
        url, key = await _upload(client)
        created = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, url)
        )
        rid = created.json()["id"]

        real = get_storage()

        class BoomDelete:
            async def delete(self, _key):
                raise RuntimeError("simulated storage delete failure")

            async def get(self, key):
                return await real.get(key)

        monkeypatch.setattr(asset_lifecycle, "get_storage", lambda: BoomDelete())

        resp = await client.delete(f"/responsibilities/{rid}")
        assert resp.status_code == 204
        row = await _asset(db_session, key)
        assert row is not None
        assert row.referenced is False
        # object still on disk — sweep can retry
        assert await real.get(key) == PNG


class TestStockIconCarveOut:
    STOCK = "/uploads/stock_icons/homework.png"

    async def test_stock_icon_create_makes_no_assets_row(
        self, client, db_session, test_family_member
    ):
        resp = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, self.STOCK)
        )
        assert resp.status_code == 201
        # Stock icons are unmanaged — no assets row exists for them.
        assert await _asset(db_session, "stock_icons/homework.png") is None

    async def test_stock_icon_is_not_deleted_on_entity_delete(
        self, client, test_family_member
    ):
        """The bundled stock file must survive an entity delete (release is a
        no-op for stock_icons/*) — otherwise it would vanish for every other
        entity still using it. Simulate the bundled file, then confirm it
        survives (the integration UPLOAD_DIR is a fresh tmp dir with no stock
        files, so we seed one)."""
        stock_key = "stock_icons/homework.png"
        await get_storage().put(stock_key, PNG, "image/png")

        created = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, self.STOCK)
        )
        rid = created.json()["id"]
        await client.delete(f"/responsibilities/{rid}")

        # release() must NOT have touched the bundled stock object.
        assert await get_storage().get(stock_key) == PNG


class TestAbandonedUploadSweep:
    async def test_sweeps_only_aged_unreferenced(self, db_session):
        storage = get_storage()
        old = f"family_photos/{uuid.uuid4()}.png"      # unreferenced, aged → swept
        fresh = f"family_photos/{uuid.uuid4()}.png"    # unreferenced, fresh → kept
        ref = f"family_photos/{uuid.uuid4()}.png"      # referenced, aged → kept

        aged_ts = datetime.utcnow() - timedelta(hours=25)
        for k in (old, fresh, ref):
            await storage.put(k, PNG, "image/png")
        db_session.add_all([
            models.Asset(key=old, content_type="image/png", size_bytes=len(PNG),
                         referenced=False, created_at=aged_ts),
            models.Asset(key=fresh, content_type="image/png", size_bytes=len(PNG),
                         referenced=False),  # created_at defaults to now()
            models.Asset(key=ref, content_type="image/png", size_bytes=len(PNG),
                         referenced=True, created_at=aged_ts),
        ])
        await db_session.commit()

        deleted = await asset_lifecycle.sweep_abandoned_uploads(db_session)
        assert deleted == 1

        assert await _asset(db_session, old) is None
        with pytest.raises(ObjectNotFound):
            await storage.get(old)
        assert await _asset(db_session, fresh) is not None      # too fresh
        assert await _asset(db_session, ref) is not None        # referenced
        assert await storage.get(ref) == PNG

    async def test_sweep_keeps_row_when_storage_delete_fails(self, db_session, monkeypatch):
        storage = get_storage()
        key = f"family_photos/{uuid.uuid4()}.png"
        aged_ts = datetime.utcnow() - timedelta(hours=25)
        await storage.put(key, PNG, "image/png")
        db_session.add(
            models.Asset(
                key=key,
                content_type="image/png",
                size_bytes=len(PNG),
                referenced=False,
                created_at=aged_ts,
            )
        )
        await db_session.commit()

        class BoomDelete:
            async def delete(self, _key):
                raise RuntimeError("simulated storage delete failure")

            async def get(self, k):
                return await storage.get(k)

        monkeypatch.setattr(asset_lifecycle, "get_storage", lambda: BoomDelete())

        deleted = await asset_lifecycle.sweep_abandoned_uploads(db_session)
        assert deleted == 0
        assert await _asset(db_session, key) is not None
        assert await storage.get(key) == PNG


class TestA1DuplicatedKeyOutOfScope:
    """A1 (M7 eng review): the 1:1 key→entity invariant is ACCEPTED, not
    enforced. This test documents the known limitation — two entities sharing
    one managed key means deleting one erases the shared object. If this test
    ever needs to change, revisit the refcount decision."""

    async def test_shared_key_deletion_is_known_limitation(
        self, client, db_session, test_family_member
    ):
        url, key = await _upload(client)
        # Two responsibilities deliberately pointing at the SAME key (only
        # reachable by copy-pasting a URL — not a normal UI flow).
        r1 = (await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, url)
        )).json()["id"]
        await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, url)
        )

        # Deleting r1 releases the shared object — r2 now dangles (documented).
        await client.delete(f"/responsibilities/{r1}")
        assert await _asset(db_session, key) is None
        with pytest.raises(ObjectNotFound):
            await get_storage().get(key)


class TestTraversalNeutralized:
    """Regression (pre-landing review Finding 1): a crafted traversal URL in a
    user-controlled image field must classify as unmanaged, so the entity
    lifecycle completes without release() ever calling storage.delete on it."""

    @pytest.mark.parametrize(
        "poison",
        [
            "/uploads/../../../app/app/main.py",
            "/uploads//etc/passwd",  # leading slash — pathlib would drop the root
        ],
    )
    async def test_poison_icon_url_lifecycle_is_clean(
        self, client, test_family_member, poison
    ):
        created = await client.post(
            "/responsibilities/", json=_resp_payload(test_family_member.id, poison)
        )
        assert created.status_code == 201  # adopt is a no-op (unmanaged)
        rid = created.json()["id"]
        # delete must not raise — release() is a no-op for the unmanaged key.
        resp = await client.delete(f"/responsibilities/{rid}")
        assert resp.status_code == 204


class TestItemHooks:
    """Item wiring: recipe `image_url` adoption + capture-before-hard-delete
    (the item on-delete path runs through the hard-delete sweeper, not DELETE)."""

    async def _upload_pair(self, client):
        icon = (await client.post(
            "/uploads/item-icon", files={"file": ("i.png", io.BytesIO(PNG), "image/png")}
        )).json()["url"]
        image = (await client.post(
            "/upload/recipe-image", files={"file": ("r.png", io.BytesIO(PNG), "image/png")}
        )).json()["url"]
        return icon, image

    @staticmethod
    def _recipe_payload(icon_url, image_url):
        return {
            "name": f"Recipe {uuid.uuid4().hex[:8]}",
            "item_type": "recipe",
            "icon_url": icon_url,
            "recipe_detail": {
                "description": "d",
                "ingredients": [
                    {"name": "pasta", "quantity": 1, "unit": "lb", "category": "Pantry"}
                ],
                "instructions": "cook",
                "servings": 4,
                "image_url": image_url,
            },
        }

    async def test_create_adopts_icon_and_recipe_image(self, client, db_session):
        icon, image = await self._upload_pair(client)
        icon_key, image_key = icon.removeprefix("/uploads/"), image.removeprefix("/uploads/")
        resp = await client.post("/items/", json=self._recipe_payload(icon, image))
        assert resp.status_code == 201, resp.text
        assert (await _asset(db_session, icon_key)).referenced is True
        assert (await _asset(db_session, image_key)).referenced is True

    async def test_recipe_form_shares_one_key_across_icon_and_image(
        self, client, db_session
    ):
        """The recipe form sends ONE upload as both `icon_url` and
        `recipe_detail.image_url` (ItemFormModal). Same item, two columns, one
        key — inside the A1 invariant (one key → one ENTITY), and safe only
        because `adopt` and `storage.delete` are idempotent. A `referenced=false`
        precondition on adopt would 400 this flow."""
        url, key = await _upload(client, endpoint="/upload/recipe-image")
        resp = await client.post("/items/", json=self._recipe_payload(url, url))
        assert resp.status_code == 201, resp.text
        assert (await _asset(db_session, key)).referenced is True

        # Replace both columns together, as the form does: the old key is
        # released twice (second call a no-op); the new key stays live.
        new_url, new_key = await _upload(client, endpoint="/upload/recipe-image")
        patch = self._recipe_payload(new_url, new_url)
        del patch["name"], patch["item_type"]
        resp = await client.patch(f"/items/{resp.json()['id']}", json=patch)
        assert resp.status_code == 200, resp.text
        assert await _asset(db_session, key) is None
        with pytest.raises(ObjectNotFound):
            await get_storage().get(key)
        assert (await _asset(db_session, new_key)).referenced is True
        assert await get_storage().get(new_key) == PNG

    async def test_hard_delete_releases_icon_and_recipe_image(self, client, db_session):
        from app.crud_items import hard_delete_expired_soft_deletes_async

        icon, image = await self._upload_pair(client)
        icon_key, image_key = icon.removeprefix("/uploads/"), image.removeprefix("/uploads/")
        item_id = (
            await client.post("/items/", json=self._recipe_payload(icon, image))
        ).json()["id"]

        # Soft-delete, then age it past the 24h soak so the sweeper hard-deletes.
        del_resp = await client.delete(f"/items/{item_id}")
        assert del_resp.status_code in (200, 204)
        await db_session.execute(
            update(models.Item)
            .where(models.Item.id == item_id)
            .values(deleted_at=datetime.utcnow() - timedelta(hours=25))
        )
        await db_session.commit()

        result = await hard_delete_expired_soft_deletes_async(db_session)
        assert result["items_deleted"] == 1
        # both managed objects + manifest rows reclaimed
        assert await _asset(db_session, icon_key) is None
        assert await _asset(db_session, image_key) is None
        with pytest.raises(ObjectNotFound):
            await get_storage().get(icon_key)
        with pytest.raises(ObjectNotFound):
            await get_storage().get(image_key)
