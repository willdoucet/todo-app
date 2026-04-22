"""Tests for the CORS_ALLOW_ORIGINS parser in app.main.

The visual-regression test stack needs to inject
`http://frontend-preview:4173` into the allowlist via env var. These tests
pin that contract so the prod default (unset env var → localhost dev
servers only) stays unchanged as the parser evolves.
"""

from app.main import _parse_cors_origins


class TestDefaults:
    def test_none_returns_default_localhost_list(self):
        assert _parse_cors_origins(None) == [
            "http://localhost:5173",
            "http://localhost:3000",
        ]

    def test_empty_string_returns_empty_list(self):
        # Explicit empty env var ≠ unset. The operator set it to nothing,
        # which means "allow no origins" — different from the default.
        assert _parse_cors_origins("") == []


class TestParsing:
    def test_single_origin(self):
        assert _parse_cors_origins("http://example.com") == ["http://example.com"]

    def test_comma_separated(self):
        result = _parse_cors_origins(
            "http://localhost:5173,http://frontend-preview:4173"
        )
        assert result == [
            "http://localhost:5173",
            "http://frontend-preview:4173",
        ]

    def test_whitespace_stripped(self):
        result = _parse_cors_origins(
            "  http://a.com  ,  http://b.com  ,http://c.com"
        )
        assert result == ["http://a.com", "http://b.com", "http://c.com"]

    def test_trailing_comma_produces_no_empty_origin(self):
        # Regression: split(",") on "a,b," gives ["a", "b", ""] — an empty
        # entry passed to CORSMiddleware would be rejected as an invalid
        # origin (or worse, matched against an empty Origin header).
        assert _parse_cors_origins("http://a.com,http://b.com,") == [
            "http://a.com",
            "http://b.com",
        ]

    def test_internal_empty_entries_skipped(self):
        assert _parse_cors_origins("http://a.com,,http://b.com") == [
            "http://a.com",
            "http://b.com",
        ]
