"""Canonical error codes for the recipe URL import flow.

Every stable `error_code` value that can be returned by
`GET /items/import-status/{task_id}` — or surfaced through observability logs
for the import pipeline — lives here. The frontend keeps a matching
`error_code` → friendly message map; a parity test asserts that every code
defined in this module has a corresponding frontend entry so new codes cannot
ship without a user-visible message.

DO NOT introduce ad-hoc string literals in the endpoint, the Celery task, the
recipe_extractor, the ai_client, or the URL-safety utility. Add the constant
here first, then use it.

The dict value is a small 3-tuple:
    (http_status, retryable, user_facing_message)

- `http_status`: the status code to return at the HTTP boundary (synchronous
  paths only — the async task surfaces these via the status endpoint JSON).
- `retryable`: whether the frontend should show a "Try Again" button as the
  primary recovery CTA. Non-retryable codes get "Enter Manually" as primary.
- `user_facing_message`: the exact copy the user sees (also the value the
  frontend's map must match for the taxonomy parity test to pass).
"""
from typing import NamedTuple


class ImportErrorInfo(NamedTuple):
    http_status: int
    retryable: bool
    user_facing_message: str


# Submit-time (synchronous) errors
UNKNOWN_OR_EXPIRED_TASK = "unknown_or_expired_task"
INVALID_URL = "invalid_url"
SSRF_BLOCKED = "ssrf_blocked"
BROKER_UNAVAILABLE = "broker_unavailable"

# Fetch-stage errors (async, reported via status endpoint)
FETCH_FAILED = "fetch_failed"
FETCH_TIMEOUT = "fetch_timeout"
FETCH_BLOCKED = "fetch_blocked"
FETCH_NOT_FOUND = "fetch_not_found"
FETCH_TOO_LARGE = "fetch_too_large"
NOT_HTML = "not_html"

# LLM-stage errors
LLM_UNAVAILABLE = "llm_unavailable"
LLM_AUTH = "llm_auth"
LLM_RATE_LIMITED = "llm_rate_limited"
LLM_REFUSED = "llm_refused"

# Validation / semantic failure
NOT_RECIPE = "not_recipe"

# Task-level
TASK_TIMEOUT = "task_timeout"
INTERNAL_ERROR = "internal_error"


ERROR_CATALOG: dict[str, ImportErrorInfo] = {
    UNKNOWN_OR_EXPIRED_TASK: ImportErrorInfo(
        http_status=404,
        retryable=True,
        user_facing_message="Import not found. Please try again.",
    ),
    INVALID_URL: ImportErrorInfo(
        http_status=422,
        retryable=True,
        user_facing_message="Please enter a valid URL.",
    ),
    SSRF_BLOCKED: ImportErrorInfo(
        http_status=400,
        retryable=False,
        user_facing_message="This URL cannot be imported.",
    ),
    BROKER_UNAVAILABLE: ImportErrorInfo(
        http_status=503,
        retryable=True,
        user_facing_message="Service temporarily unavailable. Try again in a moment.",
    ),
    FETCH_FAILED: ImportErrorInfo(
        http_status=200,
        retryable=True,
        user_facing_message="Couldn't reach that website. Try again?",
    ),
    FETCH_TIMEOUT: ImportErrorInfo(
        http_status=200,
        retryable=True,
        user_facing_message="Website took too long to respond. Try again?",
    ),
    FETCH_BLOCKED: ImportErrorInfo(
        http_status=200,
        retryable=False,
        user_facing_message="Website blocked our request. Enter the recipe manually.",
    ),
    FETCH_NOT_FOUND: ImportErrorInfo(
        http_status=200,
        retryable=False,
        user_facing_message="Page not found. Check the URL or enter the recipe manually.",
    ),
    FETCH_TOO_LARGE: ImportErrorInfo(
        http_status=200,
        retryable=False,
        user_facing_message="Page too large to process. Enter the recipe manually.",
    ),
    NOT_HTML: ImportErrorInfo(
        http_status=200,
        retryable=False,
        user_facing_message="Not a recipe page. Enter the recipe manually.",
    ),
    LLM_UNAVAILABLE: ImportErrorInfo(
        http_status=200,
        retryable=True,
        user_facing_message="AI service unavailable. Try again in a moment.",
    ),
    LLM_AUTH: ImportErrorInfo(
        http_status=200,
        retryable=False,
        user_facing_message="AI service is misconfigured. Enter the recipe manually.",
    ),
    LLM_RATE_LIMITED: ImportErrorInfo(
        http_status=200,
        retryable=True,
        user_facing_message="Try again in a moment.",
    ),
    LLM_REFUSED: ImportErrorInfo(
        http_status=200,
        retryable=False,
        user_facing_message="Couldn't extract a recipe from this page.",
    ),
    NOT_RECIPE: ImportErrorInfo(
        http_status=200,
        retryable=False,
        user_facing_message="Couldn't extract a recipe from this page.",
    ),
    TASK_TIMEOUT: ImportErrorInfo(
        http_status=200,
        retryable=True,
        user_facing_message="Import timed out. Try again?",
    ),
    INTERNAL_ERROR: ImportErrorInfo(
        http_status=200,
        retryable=True,
        user_facing_message="Something went wrong. Try again?",
    ),
}


def all_codes() -> list[str]:
    """Every registered error code. Used by the taxonomy parity test."""
    return sorted(ERROR_CATALOG.keys())
