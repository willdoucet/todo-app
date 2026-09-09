## FastAPI

### API & trust boundaries
- Every new router is included on the protected router (or its auth dependency is explicit); the public surface is enumerable with one grep of `include_router` in `main.py`.
- `/docs`, `/redoc`, and `/openapi.json` are disabled or explicitly gated; router-level dependencies do not cover them.
- Credential and token failures return one status with a byte-identical body; only body-shape errors return 422.
- Validation `detail` is an array of `{loc, msg, type}`; no caller renders it raw.
- New write paths send the same required fields as the established path for that entity (no shortcut endpoint that 422s).
- CORS origins come from env; never `*` when `APP_ENV=production`.
- Production-only host or origin gate returns a distinct status (e.g. 421) and is disabled in dev and test.

### Query efficiency
- List endpoints eager-load every relationship the `response_model` touches; no lazy load fires during serialization.
- Any list that can grow unbounded has pagination or a hard cap.

### Error handling
- 404 for missing, 409 for unique-constraint conflicts (catch `IntegrityError`), 400 for business-rule rejections, 422 left to Pydantic.
- Custom exceptions map to statuses in one place; handlers never leak stack traces.

### Secrets & config
- Lifespan fails closed in production when a required secret is missing and logs a clear bootstrap warning in development.
- Settings are loaded once from env; tests configure them directly instead of reading the process environment.

### Operations
- `/healthz` is public, cheap, and reports the deployed version.
- Every auth-related request emits exactly one structured log line with event, outcome, reason, sanitized ip, request id, and latency; never a credential.

### Testing
- A structural test walks `app.routes` and asserts every non-allowlisted route carries the auth dependency and the docs routes are absent.
- A behavioral test asserts 401 without a token and with a malformed bearer, and 200 on the public surface.
