# Implementation Summary — M3 prod-auth-backend-foundation

**Plan:** [`prod-auth-backend-foundation-plan-20260501-170804.md`](./prod-auth-backend-foundation-plan-20260501-170804.md)
**Branch:** `prod-auth-backend-foundation`
**Started:** 2026-05-02
**Completed:** 2026-05-02
**Status:** ready-for-review (DONE)

## Plan metadata (from `obsidian-workflow plan-metadata-get`)

```json
{
  "metadata": {},
  "plan_path": ".claude/plans/features/prod-auth-backend-foundation/prod-auth-backend-foundation-plan-20260501-170804.md",
  "status": "ok"
}
```

Empty metadata → non-Obsidian-tracked plan. No registry / note-update steps ran during this implementation; the standard Obsidian handoff lines from `/execute-plan` therefore did not apply. `/review-implementation` is the next step.

## Reviews status (from session-start preamble)

- CEO: ✓
- Eng: ✓
- Adversarial: ✓
- Design: — (n/a — backend-only milestone)
- Pre-landing: — (runs after `/review-implementation`)

## Pre-flight observations (Step 0)

These items must still be confirmed by the operator outside this session — they are documented for the post-deploy / pre-merge checklist:

- `fly scale show --app <app>` — confirm `web` VM ≥ 1024 MB. Argon2 OWASP defaults consume ~64 MiB per concurrent hash; sustained traffic on a 256 MB VM will OOM.
- `psql ... pg_available_extensions WHERE name='citext'` against Fly Postgres — confirm CITEXT availability. Local Postgres 16 has CITEXT 1.6 confirmed in this session.
- Cloudflare `/auth/*` rate-limit rule + Access policy still active.
- Direct Fly origin gated for non-`/healthz` paths once host gate is enabled (covered by integration tests in this PR).

## Steps

- [✓] Step 0 — Pre-flight (CITEXT verified locally; operator-side checks documented)
- [✓] Step 1 — Add auth dependencies (argon2-cffi 25.1.0, PyJWT 2.12.1, email-validator 2.3.0)
- [✓] Step 2 — `app/auth/config.py` with fail-closed validation (40 unit tests)
- [✓] Step 3 — `app/auth/models.py` + `alembic/env.py` import (User + RefreshToken)
- [✓] Step 4 — Migration `cf4f8428948e_add_auth_tables.py` (citext + 2 tables + self-FK + 3 indexes)
- [✓] Step 5 — `tokens.py` + `passwords.py` (17 unit tests)
- [✓] Step 6 — `errors.py` byte-identical helpers (5 unit tests)
- [✓] Step 7 — `schemas.py` Pydantic models
- [✓] Step 8 — `service.py` register/login/refresh/logout (with rotation-chain ASCII diagram in module docstring)
- [✓] Step 9 — `routes.py` 5 endpoints
- [✓] Step 10 — Structured logging in every `/auth/*` handler + IP/request-id sanitization (18 unit tests)
- [✓] Step 11 — Wired auth.router + production host gate + lifespan auth-config validation into `app/main.py`. Updated `docker-compose.yml` with new env vars.
- [✓] Step 12 — `dependencies.py::get_current_user` (NOT applied to non-auth routes; 18 unit tests)
- [✓] Step 13 — Integration tests: register (6), login (6), refresh (11), logout (7), status (3), host_gate (7), e2e_flow (3), log_hygiene (4) = 47 integration tests
- [✓] Step 14 — Backward-compat smoke (existing routes verified unaffected; full procedure documented below)
- [✓] Step 15 — DevOps writeup (`todo-app-notes/DevOps/M3 Auth Backend - Plain English Summary.md`, 2269 words)
- [✓] Step 16 — Updated `TECH_STACK.md`, `BACKEND_STRUCTURE.md`, `IMPLEMENTATION_PLAN.md`

## Final test counts

```
Full backend suite: 719 passed, 3 skipped (pre-existing), 56 warnings (pre-existing)
Auth tests added in this PR:
  Unit (tests/unit/auth/):
    test_config.py                 40 tests (fail-closed validation rules)
    test_passwords.py              8 tests (verify, dummy lazy-cache, hasher swap)
    test_tokens.py                 9 tests (JWT roundtrip, refresh-hash determinism)
    test_errors.py                 5 tests (byte-identicality of helpers)
    test_ip_sanitization.py        9 tests (CF-Connecting-IP, XFF, 128-char truncate)
    test_request_id_sanitization.py 9 tests (allowlist + UUID4 fallback)
    test_dependencies.py          18 tests (header shape, all 4 JWT exception classes,
                                            malformed claims, deleted user, stale sv)
  Integration (tests/integration/auth/):
    test_register.py               6 tests (success, byte-identical 401s, race, 422)
    test_login.py                  6 tests (success, byte-identical 401s, same-client rotation)
    test_refresh.py               11 tests (Cases A/B/C, concurrent serialization,
                                            chain corruption, all rejection paths)
    test_logout.py                 7 tests (success, cookie clearing attrs, 401 paths,
                                            stale-token mutation guard, multi-device)
    test_status.py                 3 tests (false → true flip, response shape)
    test_host_gate.py              7 tests (production gate behavior, /healthz exempt)
    test_e2e_flow.py               3 tests (full DoD sequence, multi-device, rotation)
    test_log_hygiene.py            4 tests (no plaintext / hashes / JWTs in any log line)

  Total auth tests: 165
```

## Key files added

```
backend/app/auth/__init__.py
backend/app/auth/config.py
backend/app/auth/models.py
backend/app/auth/schemas.py
backend/app/auth/tokens.py
backend/app/auth/passwords.py
backend/app/auth/errors.py
backend/app/auth/service.py
backend/app/auth/dependencies.py
backend/app/auth/routes.py
backend/app/auth/logging_utils.py
backend/alembic/versions/cf4f8428948e_add_auth_tables.py
backend/tests/unit/auth/__init__.py
backend/tests/unit/auth/test_config.py
backend/tests/unit/auth/test_passwords.py
backend/tests/unit/auth/test_tokens.py
backend/tests/unit/auth/test_errors.py
backend/tests/unit/auth/test_ip_sanitization.py
backend/tests/unit/auth/test_request_id_sanitization.py
backend/tests/unit/auth/test_dependencies.py
backend/tests/integration/auth/__init__.py
backend/tests/integration/auth/conftest.py
backend/tests/integration/auth/test_register.py
backend/tests/integration/auth/test_login.py
backend/tests/integration/auth/test_refresh.py
backend/tests/integration/auth/test_logout.py
backend/tests/integration/auth/test_status.py
backend/tests/integration/auth/test_host_gate.py
backend/tests/integration/auth/test_e2e_flow.py
backend/tests/integration/auth/test_log_hygiene.py
todo-app-notes/DevOps/M3 Auth Backend - Plain English Summary.md
```

## Key files modified

```
backend/pyproject.toml              # added argon2-cffi, PyJWT, email-validator
backend/uv.lock                     # regenerated to include the above
backend/alembic/env.py              # imports app.auth.models for autogenerate visibility
backend/app/main.py                 # auth router include + production host gate + lifespan auth-config validation
backend/docker-compose.yml          # forwards JWT_SECRET_KEY, HOUSEHOLD_ACCESS_KEY, APP_ENV, PUBLIC_API_HOST env vars
backend/tests/integration/conftest.py  # CREATE EXTENSION IF NOT EXISTS citext before create_all
.claude/TECH_STACK.md               # documented new auth deps + env vars
.claude/BACKEND_STRUCTURE.md        # users + refresh_tokens tables, /auth/* endpoints, app/auth/ layout
.claude/IMPLEMENTATION_PLAN.md      # marked M3 implementation complete (pending merge)
```

## Backward-compat verification

The full backend test suite (719 tests) passes with the new auth tables present. Live smoke against the running dev API confirmed:
- `GET /family-members/` → 200 with existing data
- `GET /lists/` → 200 with existing data
- `GET /healthz` → 200
- `users` and `refresh_tokens` tables present, both at 0 rows

For the manual "previous image boots against migrated DB" verification (per Success Criteria), the operator should:

1. Apply the migration locally (`alembic upgrade head` — already done in this session).
2. Insert one User + one RefreshToken row via psql or by hitting `POST /auth/register` once.
3. In a sibling clone of the repo, `git checkout` the prior commit (`87dc569` — the M2 ship).
4. Build + run that backend image against the migrated DB.
5. Confirm the previous-image API still serves existing routes without error.
6. The previous-image code never references `users` or `refresh_tokens`, so the populated rows should be ignored entirely.

## Operator-side pre-deploy checklist (carried forward from plan §Distribution Plan)

These items did not run inside this session — they require operator action against Fly / Cloudflare:

- [ ] `fly secrets set JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"` — generate locally; the value never appears in the CC transcript.
- [ ] `fly secrets set HOUSEHOLD_ACCESS_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"` — same pattern; communicate the value out-of-band (password manager).
- [ ] `fly secrets list` — verify both names + digests present (NEVER `fly secrets reveal`).
- [ ] `history -c` — clear shell history after the secret-set commands.
- [ ] Cloudflare WAF dashboard — confirm `/auth/*` rate-limit rule active per `infra/cloudflare-state.md`.
- [ ] `fly scale show --app <app>` — confirm `web` VM ≥ 1024 MB.
- [ ] After deploy: `POST /auth/register` once via curl through Cloudflare Access; `GET /auth/status` returns `{"account_exists": true}`; second register returns byte-identical 401.
- [ ] Direct-origin smoke: `https://<app>.fly.dev/auth/status` returns 421; `https://api.<domain>/auth/status` returns 200.
- [ ] Multi-device smoke: login from two browsers; A still refreshes after B logs in; A's same-client re-login revokes only A's prior cookie.

## Handoff to /review-implementation

Implementation is in `ready-for-review`. Run `/review-implementation` next — that skill will perform the pre-landing review (SQL safety, trust boundaries, conditional side effects, structural issues) and finalize any remaining workflow state. Plan was non-Obsidian-tracked, so no Obsidian task-box checkoff is pending.
