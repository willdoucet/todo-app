"""Tests for the production storage-backend bootstrap in app.main.

M7 PR2 puts Cloudflare R2 on the byte path for every private image, switched
on by `STORAGE_BACKEND=r2` in `backend/fly.toml`. `get_storage()` is lazy, so
without a startup check a deploy missing one of the four `R2_*` secrets would
pass `release_command`, pass `/healthz`, take traffic, and only then 503 every
image — invisible at the edge, total at the app layer.

Same contract `_parse_cors_origins` already enforces for CORS, and what
REVIEW_CHECKLIST → FastAPI → Secrets & config requires: fail closed at boot so
Fly keeps the previous image serving.
"""

import pytest

from app.main import _initialize_storage_backend


class TestOutsideProduction:
    def test_unset_app_env_is_a_noop(self, monkeypatch):
        """Dev and test default to `local`; the R2 client must never be built
        there, so this must not touch the factory at all."""
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.setenv("STORAGE_BACKEND", "r2")
        monkeypatch.delenv("R2_BUCKET_NAME", raising=False)
        _initialize_storage_backend()  # must not raise

    def test_development_is_a_noop(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("STORAGE_BACKEND", "r2")
        monkeypatch.delenv("R2_BUCKET_NAME", raising=False)
        _initialize_storage_backend()  # must not raise


class TestProduction:
    def test_missing_r2_secret_crashes_the_boot(self, monkeypatch):
        """THE point of this hook. A missing credential must stop the deploy,
        not produce a healthy machine that 503s every family photo."""
        import app.storage as storage

        monkeypatch.setattr(storage, "_r2_singleton", None)
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("STORAGE_BACKEND", "r2")
        for name in (
            "R2_BUCKET_NAME",
            "R2_ENDPOINT",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
        ):
            monkeypatch.delenv(name, raising=False)

        with pytest.raises(KeyError):
            _initialize_storage_backend()

    def test_unknown_backend_value_crashes_the_boot(self, monkeypatch):
        """A typo in the fly.toml flip must not silently write user uploads to
        the ephemeral container disk."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("STORAGE_BACKEND", "R2 ")  # trailing space is fine
        monkeypatch.setenv("R2_BUCKET_NAME", "b")
        monkeypatch.setenv("R2_ENDPOINT", "https://example.invalid")
        monkeypatch.setenv("R2_ACCESS_KEY_ID", "k")
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "s")
        import app.storage as storage

        monkeypatch.setattr(storage, "_r2_singleton", None)
        _initialize_storage_backend()  # "R2 " normalizes to r2 — must succeed

        monkeypatch.setattr(storage, "_r2_singleton", None)
        monkeypatch.setenv("STORAGE_BACKEND", "s3")
        with pytest.raises(ValueError, match="Unknown STORAGE_BACKEND"):
            _initialize_storage_backend()

    def test_local_backend_in_production_still_boots(self, monkeypatch):
        """The hook validates whatever is configured; it does not mandate r2.
        PR1's production ran `local` and must remain bootable on a rollback."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("STORAGE_BACKEND", "local")
        _initialize_storage_backend()
