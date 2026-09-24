"""Structured logging for the production host gate (M8 item 5).

One ``app.gate`` WARNING per rejection, naming the check that failed, and one per
admitted request while the break-glass flag is on. The six reasons below map onto the
gate's real branches in ``app.main.gate_reason``; tests import them from here.

What the emitter does to its host:

    gate_reason(request) ──reason──▶ emit_gate_rejection(request, reason) ──▶ log, return
                                               │ raises (hostile header, handler bug)
                                               ▼
                         app.main swallows it; the 421 and its body are unchanged

This is a separate emitter, not a wrapper around ``app.auth.logging_utils.emit_log_line``:
that function resolves the IP from ``CF-Connecting-IP`` / ``X-Forwarded-For``, and on a
request that went around the edge (the only interesting rejection) both are
attacker-controlled. The IP here is the hop Fly's proxy saw (``_hop_ip``). It reuses the
payload's field names and ``resolve_request_id`` (allowlist-validated), nothing else.

Never logged: the secret, or any presented ``Host`` / ``X-Origin-Verify`` value. Presence
and length only.

The payload is the message itself, as one JSON object (``{"event": "host_gate", …}``), and
also rides on the record as ``extra``. The app installs no logging config, so under uvicorn
this logger reaches Python's last-resort handler, which prints ``%(message)s`` alone: a bare
``"host_gate"`` message would reach ``fly logs`` with no reason in it (found by
/review-implementation, M8 PR1b). JSON escaping also keeps an attacker-chosen path from
writing a second log line.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import Request

from app.auth.logging_utils import IP_MAX_LENGTH, resolve_request_id

logger = logging.getLogger("app.gate")

# In decision-tree order (app.main.gate_reason returns the first that applies).
PUBLIC_API_HOST_UNCONFIGURED = "public_api_host_unconfigured"
HOST_ABSENT = "host_absent"
HOST_MISMATCH = "host_mismatch"
ORIGIN_VERIFY_SECRET_EMPTY = "origin_verify_secret_empty"
ORIGIN_VERIFY_ABSENT = "origin_verify_absent"
ORIGIN_VERIFY_MISMATCH = "origin_verify_mismatch"
REASONS = (
    PUBLIC_API_HOST_UNCONFIGURED,
    HOST_ABSENT,
    HOST_MISMATCH,
    ORIGIN_VERIFY_SECRET_EMPTY,
    ORIGIN_VERIFY_ABSENT,
    ORIGIN_VERIFY_MISMATCH,
)

PATH_MAX_LENGTH = 128


def _hop_ip(request: Request) -> str:
    """The address Fly's proxy accepted the connection from: the last ``X-Forwarded-For``
    entry, across every copy of the header. The last entry is the one Fly's proxy writes,
    whether it appends to a client-sent header or replaces it: the attacker's own address on
    a direct request, a Cloudflare edge address otherwise.

    Not ``request.client.host``: production runs uvicorn with ``--proxy-headers
    --forwarded-allow-ips=*``, which sets that to the FIRST entry, the one the sender writes
    (found by /review-implementation's adversarial pass, M8 PR1b). Without the header (dev,
    tests) the socket peer is the only address there is.
    """
    entries = [e.strip() for value in request.headers.getlist("x-forwarded-for") for e in value.split(",")]
    entries = [e for e in entries if e]
    if entries:
        return entries[-1]
    return request.client.host if request.client and request.client.host else "unknown"


def _payload(request: Request, outcome: str, reason: Optional[str]) -> dict:
    host = request.headers.get("host")
    origin = request.headers.get("x-origin-verify")
    peer = _hop_ip(request)
    return {
        "event": "host_gate",
        "outcome": outcome,
        "reason": reason,
        "ip": peer[:IP_MAX_LENGTH],
        "request_id": resolve_request_id(request),
        "path": request.scope.get("path", "")[:PATH_MAX_LENGTH],
        "host_present": host is not None,
        "host_length": len(host) if host is not None else 0,
        "origin_verify_present": origin is not None,
        "origin_verify_length": len(origin) if origin is not None else 0,
    }


def _emit(payload: dict) -> None:
    logger.warning(json.dumps(payload), extra=payload)


def emit_gate_rejection(request: Request, reason: str) -> None:
    """Log one rejection. The caller swallows anything this raises."""
    _emit(_payload(request, "rejected", reason))


def emit_gate_bypass(request: Request) -> None:
    """Log one request admitted without the origin check (``GATE_BREAK_GLASS=1``)."""
    _emit(_payload(request, "bypassed", None))
