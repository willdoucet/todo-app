"""Structured logging for /auth/* endpoints.

Each request emits exactly one line at completion via :func:`emit_log_line`.
Tests assert on the LogRecord attributes (event, outcome, reason, user_id,
ip, request_id, latency_ms) using pytest's caplog fixture.

Sanitization rules:

- ``CF-Connecting-IP`` precedence (Cloudflare's edge IP)
- otherwise first comma-separated entry of ``X-Forwarded-For`` (Fly's LB)
- otherwise the direct socket peer
- truncate to 128 chars (defends against attacker-bloated XFF headers)

- Request IDs must match a strict allowlist (ASCII alnum + ``._:-``,
  length 1-128) or are replaced with a fresh UUID4 — never propagate
  raw attacker-controlled request-id values into log records.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Optional

from fastapi import Request

logger = logging.getLogger("app.auth")

# Bound the resolved IP string. 128 chars survives any sane IPv6 + zone ID.
IP_MAX_LENGTH = 128

# Request-id allowlist — alphanumerics + ``.``, ``_``, ``:``, ``-`` ; bounded length.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:\-]{1,128}\Z")


def resolve_client_ip(request: Request) -> str:
    """Resolve the client IP using the priority chain documented above."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()[:IP_MAX_LENGTH]

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        first = xff.split(",", 1)[0].strip()
        return first[:IP_MAX_LENGTH]

    if request.client and request.client.host:
        return request.client.host[:IP_MAX_LENGTH]

    return "unknown"


def resolve_request_id(request: Request) -> str:
    """Pass-through if X-Request-Id matches the safe allowlist, else
    generate a fresh UUID4 hex. Never propagate raw oversized,
    control-character, or unsafe-character request IDs into logs."""
    incoming = request.headers.get("X-Request-Id")
    if incoming and REQUEST_ID_PATTERN.match(incoming):
        return incoming
    return uuid.uuid4().hex


def emit_log_line(
    request: Request,
    *,
    event: str,
    outcome: str,
    reason: Optional[str],
    user_id: Optional[int],
    latency_ms: int,
) -> None:
    """Emit one structured log line for a completed /auth/* request.

    Level: ``INFO`` on success, ``WARNING`` on failure. The ``extra`` dict
    is attached to the :class:`logging.LogRecord` so caplog assertions
    can verify event/outcome/reason/user_id/ip/request_id/latency_ms
    independently of the formatted message string.
    """
    payload = {
        "event": event,
        "outcome": outcome,
        "reason": reason,
        "user_id": user_id,
        "ip": resolve_client_ip(request),
        "request_id": resolve_request_id(request),
        "latency_ms": latency_ms,
    }
    if outcome == "success":
        logger.info(event, extra=payload)
    else:
        logger.warning(event, extra=payload)
