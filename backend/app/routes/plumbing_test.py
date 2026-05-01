# M2-only split-origin cookie verification. POST sets a fresh opaque probe
# in __Host-plumbing-refresh; GET echoes the cookie value back. The probe
# is throwaway transport-verification state — never auth/session state,
# never persisted server-side. Only "safe" to echo because it is not a
# credential. Both responses set Cache-Control: no-store so browser/proxy
# caching can't make the round-trip look healthy when it isn't.
#
# Deleted in M5 PR #2 along with the bypass policy + the test file. Single
# git rm + one router-include line removed from main.py.

import secrets

from fastapi import APIRouter, Request, Response

router = APIRouter()

# Source of truth for the SameSite policy on the M2 probe cookie. Lowercase
# matches both FastAPI's set_cookie() input contract AND Starlette's wire
# emission (`SameSite=lax`), so this single constant drives the endpoint
# AND the drift test. Browser matrix in Slice 5 may force a flip to "none"
# (e.g., Safari's strict third-party-cookie heuristics blocking lax across
# the eTLD+1 split). The flip is a 1-line edit; the test auto-follows.
PROBE_SAMESITE = "lax"

# __Host- prefix is browser-enforced: requires Path=/, Secure, no Domain.
# Browsers silently reject cookies with the prefix that violate any of
# those — exactly the failure mode this test exists to detect.
COOKIE_NAME = "__Host-plumbing-refresh"


@router.post("/plumbing-test")
async def set_plumbing_cookie(response: Response) -> dict:
    probe = secrets.token_urlsafe(32)
    response.set_cookie(
        key=COOKIE_NAME,
        value=probe,
        httponly=True,
        secure=True,
        samesite=PROBE_SAMESITE,
        path="/",
        # No domain= argument — __Host- prefix forbids it.
    )
    response.headers["Cache-Control"] = "no-store"
    return {"set": True, "probe": probe}


@router.get("/plumbing-test/read")
async def read_plumbing_cookie(request: Request, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {"value": request.cookies.get(COOKIE_NAME)}
