"""Unit tests for the M7 storage abstraction.

LocalDiskBackend is exercised against a tmp dir. R2Backend is exercised
against `moto`'s in-process S3 mock (@mock_aws) — no network, no container,
so the docker-compose test stack stays R2-free per the M7 constraint, while
the REAL R2Backend code path (boto3 serialization, run_in_threadpool, the
NoSuchKey→ObjectNotFound mapping, idempotent delete) is covered.
"""

import boto3
import pytest
from moto import mock_aws

from app.storage import ObjectNotFound
from app.storage.local import LocalDiskBackend
from app.storage.r2 import R2Backend

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class TestLocalDiskBackend:
    async def test_put_get_roundtrip(self, tmp_path):
        backend = LocalDiskBackend(root=tmp_path)
        await backend.put("item-icons/a.png", PNG, "image/png")
        assert await backend.get("item-icons/a.png") == PNG
        # bytes landed at {root}/{key}
        assert (tmp_path / "item-icons" / "a.png").read_bytes() == PNG

    async def test_get_missing_raises_object_not_found(self, tmp_path):
        backend = LocalDiskBackend(root=tmp_path)
        with pytest.raises(ObjectNotFound):
            await backend.get("item-icons/missing.png")

    async def test_delete_is_idempotent(self, tmp_path):
        backend = LocalDiskBackend(root=tmp_path)
        await backend.put("x/y.png", PNG, "image/png")
        await backend.delete("x/y.png")
        # second delete of an already-gone key must not raise
        await backend.delete("x/y.png")
        with pytest.raises(ObjectNotFound):
            await backend.get("x/y.png")

    @pytest.mark.parametrize("bad_key", ["../escape.png", "../../etc/passwd", "/etc/passwd"])
    async def test_path_traversal_key_is_rejected(self, tmp_path, bad_key):
        """Defense-in-depth: a key that would escape the storage root must
        raise on every operation, never touch the real filesystem target."""
        backend = LocalDiskBackend(root=tmp_path)
        with pytest.raises(ValueError):
            await backend.put(bad_key, PNG, "image/png")
        with pytest.raises(ValueError):
            await backend.get(bad_key)
        with pytest.raises(ValueError):
            await backend.delete(bad_key)


class TestR2Backend:
    """`mock_aws` is used as a context manager INSIDE each async test (not as a
    class decorator — the class-decorator form wraps the async methods and
    breaks pytest-asyncio collection). moto patches botocore, so R2Backend's
    boto3 client is intercepted regardless of endpoint_url. Each test creates
    the bucket first (moto starts empty)."""

    @staticmethod
    def _backend():
        boto3.client("s3", region_name="us-east-1").create_bucket(
            Bucket="test-bucket"
        )
        # moto's request-mock matches AWS S3 hostnames, so the test points at
        # the AWS S3 endpoint; the hostname is irrelevant to the put/get/delete
        # logic under test (prod uses the real *.r2.cloudflarestorage.com
        # endpoint via the R2_ENDPOINT env var).
        return R2Backend(
            endpoint_url="https://s3.amazonaws.com",
            bucket="test-bucket",
            access_key_id="test",
            secret_access_key="test",
            region="us-east-1",
        )

    async def test_put_get_roundtrip(self):
        with mock_aws():
            backend = self._backend()
            await backend.put("item-icons/a.png", PNG, "image/png")
            assert await backend.get("item-icons/a.png") == PNG

    async def test_get_missing_raises_object_not_found(self):
        with mock_aws():
            backend = self._backend()
            with pytest.raises(ObjectNotFound):
                await backend.get("item-icons/missing.png")

    async def test_delete_is_idempotent(self):
        with mock_aws():
            backend = self._backend()
            await backend.put("x/y.png", PNG, "image/png")
            await backend.delete("x/y.png")
            # S3 delete_object never errors on a missing key
            await backend.delete("x/y.png")
            with pytest.raises(ObjectNotFound):
                await backend.get("x/y.png")

    async def test_get_maps_clienterror_404_to_object_not_found(self):
        """R2/S3 missing objects often arrive as ClientError(Code=404),
        not the modeled NoSuchKey exception. PR2's read proxy must 404."""
        from botocore.exceptions import ClientError

        with mock_aws():
            backend = self._backend()
            error = ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}},
                "GetObject",
            )

            def _boom(**_kwargs):
                raise error

            backend._client.get_object = _boom
            with pytest.raises(ObjectNotFound):
                await backend.get("item-icons/missing.png")


class TestGetStorageFactory:
    def test_default_is_local_disk(self, monkeypatch):
        from app.storage import get_storage
        from app.storage.local import LocalDiskBackend

        monkeypatch.delenv("STORAGE_BACKEND", raising=False)
        assert isinstance(get_storage(), LocalDiskBackend)

    def test_unknown_backend_raises(self, monkeypatch):
        from app.storage import get_storage

        monkeypatch.setenv("STORAGE_BACKEND", "s3")
        with pytest.raises(ValueError, match="Unknown STORAGE_BACKEND"):
            get_storage()
