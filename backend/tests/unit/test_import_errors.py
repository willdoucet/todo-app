"""Structural tests for the canonical import error catalog.

The catalog is the single source of truth for ``error_code`` strings
returned by the recipe-import flow. Tests below assert that the catalog is
internally consistent (every code is registered, every entry has a non-empty
user-facing message) and that the specific codes the frontend / pipeline
depends on are present with the expected ``retryable`` flag.
"""
from __future__ import annotations

from app.constants import import_errors as codes


class TestCatalogStructure:
    def test_every_catalog_key_appears_in_all_codes(self):
        catalog_keys = set(codes.ERROR_CATALOG.keys())
        listed = set(codes.all_codes())
        assert catalog_keys == listed, (
            f"all_codes() drift: missing={catalog_keys - listed}, extra={listed - catalog_keys}"
        )

    def test_every_entry_has_non_empty_user_facing_message(self):
        offenders = [
            code
            for code, info in codes.ERROR_CATALOG.items()
            if not info.user_facing_message or not info.user_facing_message.strip()
        ]
        assert offenders == [], f"codes with empty messages: {offenders}"

    def test_every_entry_has_int_http_status(self):
        for code, info in codes.ERROR_CATALOG.items():
            assert isinstance(info.http_status, int), code
            assert 100 <= info.http_status <= 599, code

    def test_every_entry_has_bool_retryable(self):
        for code, info in codes.ERROR_CATALOG.items():
            assert isinstance(info.retryable, bool), code

    def test_both_retryable_and_non_retryable_codes_exist(self):
        retryables = {c for c, info in codes.ERROR_CATALOG.items() if info.retryable}
        non_retryables = {c for c, info in codes.ERROR_CATALOG.items() if not info.retryable}
        assert retryables, "expected at least one retryable error code"
        assert non_retryables, "expected at least one non-retryable error code"


class TestKnownCriticalCodes:
    def test_ssrf_blocked_present_and_non_retryable(self):
        info = codes.ERROR_CATALOG[codes.SSRF_BLOCKED]
        assert info.retryable is False
        assert info.http_status == 400

    def test_llm_auth_present_and_non_retryable(self):
        info = codes.ERROR_CATALOG[codes.LLM_AUTH]
        assert info.retryable is False

    def test_not_recipe_present_and_non_retryable(self):
        info = codes.ERROR_CATALOG[codes.NOT_RECIPE]
        assert info.retryable is False

    def test_broker_unavailable_present_and_retryable(self):
        info = codes.ERROR_CATALOG[codes.BROKER_UNAVAILABLE]
        assert info.retryable is True
        assert info.http_status == 503

    def test_unknown_or_expired_task_present_and_retryable(self):
        info = codes.ERROR_CATALOG[codes.UNKNOWN_OR_EXPIRED_TASK]
        assert info.retryable is True

    def test_string_constants_match_dict_keys(self):
        # Spot-check that the named constants line up with the dict keys.
        assert codes.SSRF_BLOCKED in codes.ERROR_CATALOG
        assert codes.NOT_RECIPE in codes.ERROR_CATALOG
        assert codes.UNKNOWN_OR_EXPIRED_TASK in codes.ERROR_CATALOG
        assert codes.BROKER_UNAVAILABLE in codes.ERROR_CATALOG
        assert codes.LLM_AUTH in codes.ERROR_CATALOG
        assert codes.LLM_RATE_LIMITED in codes.ERROR_CATALOG
