"""Unit tests for app.utils.url_safety.validate_url_for_fetch.

The validator is a pure function — no real network is touched. Where the
implementation calls ``socket.getaddrinfo`` for hostname resolution we patch
it via ``monkeypatch`` so tests are fully deterministic.
"""
from __future__ import annotations

import socket

import pytest

from app.utils.url_safety import SSRFBlocked, URLResolutionFailed, validate_url_for_fetch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_getaddrinfo_factory(addr: str):
    """Build a fake ``socket.getaddrinfo`` that resolves any hostname to ``addr``.

    Returns the same shape as the real call: a list of 5-tuples with the IP at
    ``sockaddr[0]``.
    """

    def _fake(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (addr, 0))]

    return _fake


def _fake_getaddrinfo_multi(addrs: list[str]):
    """Same idea but returns multiple sockaddr entries (round-robin DNS)."""

    def _fake(host, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", (a, 0)) for a in addrs
        ]

    return _fake


# ---------------------------------------------------------------------------
# Scheme + shape rejection
# ---------------------------------------------------------------------------


class TestSchemeAndShape:
    def test_empty_url_rejected(self):
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("")

    def test_file_scheme_rejected(self):
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("file:///etc/passwd")

    def test_ftp_scheme_rejected(self):
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("ftp://example.com/recipe.txt")

    def test_javascript_scheme_rejected(self):
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("javascript:alert(1)")

    def test_missing_hostname_rejected(self):
        # http:///path has empty hostname after the scheme — not fetchable.
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("http:///path")


# ---------------------------------------------------------------------------
# Literal IPv4 rejections (no DNS needed)
# ---------------------------------------------------------------------------


class TestLiteralPrivateIPv4:
    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",       # loopback
            "10.0.0.1",        # RFC1918 / 10.0.0.0/8
            "192.168.1.1",     # RFC1918 / 192.168.0.0/16
            "172.16.5.5",      # RFC1918 / 172.16.0.0/12
            "169.254.169.254", # link-local (cloud metadata)
            "0.0.0.0",         # unspecified — also in literal denylist
        ],
    )
    def test_disallowed_ipv4_literal(self, ip):
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch(f"http://{ip}/recipe")


# ---------------------------------------------------------------------------
# Literal IPv6 rejections
# ---------------------------------------------------------------------------


class TestLiteralIPv6:
    def test_ipv6_loopback_rejected(self):
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("http://[::1]/")

    def test_ipv4_mapped_loopback_rejected(self):
        # ``::ffff:127.0.0.1`` — IPv6-mapped IPv4 loopback, classic SSRF bypass.
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("http://[::ffff:127.0.0.1]/")


# ---------------------------------------------------------------------------
# Literal hostname denylist
# ---------------------------------------------------------------------------


class TestHostnameDenylist:
    @pytest.mark.parametrize(
        "host",
        [
            "localhost",
            "db",
            "redis",
            "api",
            "celery_worker",
            "celery_beat",
            "frontend",
            "metadata.google.internal",
            "ip6-localhost",
        ],
    )
    def test_blocked_hostname(self, host):
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch(f"http://{host}/x")

    def test_blocked_hostname_case_insensitive(self):
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("http://LocalHost/x")


# ---------------------------------------------------------------------------
# Public IPs and hostnames pass
# ---------------------------------------------------------------------------


class TestPublicAddresses:
    def test_public_ipv4_literal_passes(self):
        # Literal public IPs short-circuit DNS, so no patching needed.
        validate_url_for_fetch("http://1.1.1.1/")
        validate_url_for_fetch("https://8.8.8.8/")

    def test_public_hostname_passes_with_mocked_dns(self, monkeypatch):
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            _fake_getaddrinfo_factory("93.184.216.34"),  # example.com
        )
        validate_url_for_fetch("https://example.com/recipe")

    def test_public_hostname_with_multiple_public_ips_passes(self, monkeypatch):
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            _fake_getaddrinfo_multi(["93.184.216.34", "1.1.1.1"]),
        )
        validate_url_for_fetch("https://example.com/")


# ---------------------------------------------------------------------------
# Hostname resolves to a private address — DNS-rebind protection
# ---------------------------------------------------------------------------


class TestDnsResolution:
    def test_hostname_resolving_to_loopback_rejected(self, monkeypatch):
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            _fake_getaddrinfo_factory("127.0.0.1"),
        )
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("http://attacker.example/recipe")

    def test_hostname_resolving_to_private_rejected(self, monkeypatch):
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            _fake_getaddrinfo_factory("10.0.0.5"),
        )
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("http://attacker.example/")

    def test_hostname_with_one_private_one_public_rejected(self, monkeypatch):
        # Round-robin DNS: any disallowed result rejects the URL.
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            _fake_getaddrinfo_multi(["1.1.1.1", "10.0.0.1"]),
        )
        with pytest.raises(SSRFBlocked):
            validate_url_for_fetch("http://mixed.example/")

    def test_dns_failure_raises_url_resolution_failed_not_ssrf_blocked(self, monkeypatch):
        """A typo'd or unregistered domain is not a security event.

        DNS failures must raise URLResolutionFailed (→ mapped to ``fetch_failed``
        at the API boundary) not SSRFBlocked (→ ``ssrf_blocked``), otherwise
        users see "This URL cannot be imported" instead of
        "Couldn't reach that website."
        """
        def _boom(*a, **kw):
            raise socket.gaierror("name or service not known")

        monkeypatch.setattr(socket, "getaddrinfo", _boom)
        with pytest.raises(URLResolutionFailed):
            validate_url_for_fetch("http://does-not-exist.invalid/")
        # And confirm the negative — must NOT be caught by SSRFBlocked.
        monkeypatch.setattr(socket, "getaddrinfo", _boom)
        with pytest.raises(Exception) as exc_info:
            validate_url_for_fetch("http://does-not-exist.invalid/")
        assert not isinstance(exc_info.value, SSRFBlocked)
