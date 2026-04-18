"""URL-safety / SSRF gate for the recipe-import fetch path.

Every outbound fetch in the recipe extraction pipeline runs through
``validate_url_for_fetch(url)`` BEFORE issuing an HTTP request. The same check
is re-run on every redirect ``Location`` header — not just the initial URL —
because a public URL can 302 to an internal IP and bypass a one-shot check.

The validation has two layers:

1. **Scheme / shape.** Only ``http`` and ``https``. Reject everything else
   (``file://``, ``gopher://``, ``ftp://``, ``javascript:``, etc.).

2. **Resolved address.** Resolve the hostname through ``socket.getaddrinfo``
   and reject any result that falls into a disallowed range:

   - Loopback (127.0.0.0/8, ::1)
   - Private (10/8, 172.16/12, 192.168/16, plus IPv6 ULA fc00::/7)
   - Link-local (169.254/16, fe80::/10)
   - Multicast / unspecified / reserved
   - The IPv4-mapped-IPv6 form of any of the above (``::ffff:127.0.0.1``)

   Hostnames that resolve to multiple addresses (round-robin DNS) have EVERY
   resolved address checked — one disallowed hit rejects the URL.

3. **Literal-hostname denylist.** Some hostnames don't need DNS to be unsafe:
   the compose-internal service names (``db``, ``api``, ``redis``,
   ``celery_worker``, ``celery_beat``, ``frontend``) and common
   loopback/metadata aliases (``localhost``, ``0.0.0.0``,
   ``metadata.google.internal``). Reject these by name regardless of DNS.

Raised exception: :class:`SSRFBlocked`. Caller catches it and translates to
the ``ssrf_blocked`` error code from ``app.constants.import_errors``.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class SSRFBlocked(Exception):
    """Raised when a URL (or redirect hop) resolves to a disallowed address.

    The message is safe to surface to the user — but the common case is to map
    it to the ``ssrf_blocked`` error code and show the canonical user-facing
    message from ``import_errors.ERROR_CATALOG``.
    """


class URLResolutionFailed(Exception):
    """Raised when a URL's hostname cannot be resolved via DNS.

    Distinct from :class:`SSRFBlocked` so callers can surface the correct
    ``fetch_failed`` error code (not ``ssrf_blocked``) — a typo'd domain
    is not a security event and deserves the "Couldn't reach that website"
    message, not "This URL cannot be imported."
    """


# Compose-internal service names that must never be fetched from a user-supplied URL.
# Match the service names in backend/docker-compose.yml.
_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "0.0.0.0",
        "0",
        "ip6-localhost",
        "ip6-loopback",
        "metadata.google.internal",
        # Docker compose service names — never a legitimate import target
        "db",
        "api",
        "redis",
        "celery_worker",
        "celery_beat",
        "frontend",
    }
)


def _is_disallowed_ip(addr: str) -> bool:
    """Return True if the given resolved IP (v4 or v6) is in a disallowed range."""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        # Unparseable — safer to reject than to assume public
        return True

    # Strip IPv4-mapped-IPv6 so ``::ffff:127.0.0.1`` is caught as loopback.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_all_addresses(hostname: str) -> list[str]:
    """Return every IP address the hostname resolves to. Raises on resolution failure."""
    # socket.getaddrinfo with family=0 returns both IPv4 and IPv6 results.
    # Filter to the unique addresses so round-robin DNS with duplicate entries
    # is deduplicated.
    results = socket.getaddrinfo(hostname, None)
    addrs: list[str] = []
    seen: set[str] = set()
    for _family, _type, _proto, _canonname, sockaddr in results:
        addr = sockaddr[0]
        if addr not in seen:
            seen.add(addr)
            addrs.append(addr)
    return addrs


def validate_url_for_fetch(url: str) -> None:
    """Validate a URL against the SSRF gate.

    Call this BEFORE issuing an outbound HTTP request, and call it again on
    every redirect ``Location`` hop AND right before every ``client.get`` so
    a flipped DNS resolution (rebinding attack) is caught between checks.

    On success, returns None. On rejection, raises :class:`SSRFBlocked`
    (private/reserved address) or :class:`URLResolutionFailed` (DNS lookup
    failed).

    DNS-rebinding note: re-calling this function right before each outbound
    fetch shrinks the TOCTOU between validation and connection to the OS
    resolver's cache window. A full httpx transport-level IP pin would close
    the window completely but requires non-trivial TLS/SNI surgery — the
    re-validation approach is 99% effective at family-app scale.
    """
    if not isinstance(url, str) or not url:
        raise SSRFBlocked("empty_url")

    parsed = urlparse(url)

    # 1. Scheme gate — only http / https
    if parsed.scheme not in ("http", "https"):
        raise SSRFBlocked(f"scheme_not_allowed:{parsed.scheme!r}")

    # 2. Hostname presence
    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlocked("missing_hostname")

    # 3. Literal hostname denylist (case-insensitive)
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise SSRFBlocked(f"blocked_hostname:{hostname!r}")

    # 4. Reject any IP-literal hostname that's in a disallowed range before DNS.
    #    Also catches accidental IPv6-bracketed literals in the URL.
    try:
        literal_ip = ipaddress.ip_address(hostname)
        if _is_disallowed_ip(str(literal_ip)):
            raise SSRFBlocked(f"disallowed_literal_ip:{hostname!r}")
        # Public IP literal — DNS step below is a no-op for these.
        return
    except ValueError:
        # Not an IP literal — fall through to DNS resolution.
        pass

    # 5. Resolve and check every returned address.
    try:
        addrs = _resolve_all_addresses(hostname)
    except socket.gaierror as exc:
        # DNS failure is NOT an SSRF event — raise a distinct exception so the
        # caller maps it to ``fetch_failed``, not ``ssrf_blocked``.
        raise URLResolutionFailed(f"dns_failure:{exc!s}") from exc

    if not addrs:
        raise URLResolutionFailed("dns_no_results")

    for addr in addrs:
        if _is_disallowed_ip(addr):
            raise SSRFBlocked(f"disallowed_resolved_ip:{addr!r}")
