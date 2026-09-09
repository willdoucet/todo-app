"""Cloudflare R2 storage backend (S3-compatible, via boto3).

Built in PR1 and covered by ``moto`` tests, but NOT enabled until PR2 flips
``STORAGE_BACKEND=r2`` in production. The four ``R2_*`` Fly secrets were
provisioned in M2 (Slice 3): ``R2_ENDPOINT``, ``R2_ACCESS_KEY_ID``,
``R2_SECRET_ACCESS_KEY``, ``R2_BUCKET_NAME``.

boto3 is synchronous, so every S3 call is bounced through
``run_in_threadpool`` to avoid blocking the async event loop (the backend is
async SQLAlchemy throughout).
"""

from __future__ import annotations

import os

from botocore.exceptions import ClientError
from fastapi.concurrency import run_in_threadpool

from .base import ObjectNotFound

# S3-compatible stores (incl. R2) surface a missing object as ClientError
# with one of these codes — not always the modeled NoSuchKey exception.
_MISSING_OBJECT_CODES = {"NoSuchKey", "404", "NotFound"}


class R2Backend:
    """S3-compatible client against the R2 endpoint.

    Construction args default to the ``R2_*`` env vars so production wires
    itself from Fly secrets; tests pass explicit values (moto intercepts the
    boto3 client, so the endpoint/creds are dummies)."""

    def __init__(
        self,
        *,
        endpoint_url: str | None = None,
        bucket: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str = "auto",
    ) -> None:
        # Imported lazily so the dev/test image never imports boto3 unless R2
        # is actually constructed (it is not in PR1 — STORAGE_BACKEND=local).
        import boto3

        self._bucket = bucket or os.environ["R2_BUCKET_NAME"]
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or os.environ["R2_ENDPOINT"],
            aws_access_key_id=access_key_id or os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=(
                secret_access_key or os.environ["R2_SECRET_ACCESS_KEY"]
            ),
            region_name=region,
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await run_in_threadpool(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        def _get() -> bytes:
            try:
                resp = self._client.get_object(Bucket=self._bucket, Key=key)
                body = resp["Body"]
                try:
                    return body.read()
                finally:
                    body.close()
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                if code in _MISSING_OBJECT_CODES:
                    raise ObjectNotFound(key) from exc
                raise

        return await run_in_threadpool(_get)

    async def delete(self, key: str) -> None:
        # S3/R2 delete_object is idempotent — no error on a missing key.
        await run_in_threadpool(
            self._client.delete_object, Bucket=self._bucket, Key=key
        )
