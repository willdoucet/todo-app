# M2 — Production Deploy Skeleton — Implementation Summary

**Plan:** `.claude/plans/features/prod-deploy-skeleton/prod-deploy-skeleton-plan-20260422-214657.md`
**Branch:** `prod-deploy-skeleton`
**Approach chosen:** Per-slice handoff (Option A) — Claude implements the code per slice; user runs platform actions, deploys, and verifies DONE-WHEN; Claude then proceeds to the next slice's code.
**Started:** 2026-04-30

## Domain change log

**2026-04-30** — Operator switched the production domain mid-implementation: `williamdoucet.dev` → `mealy.dev`. Operator also renamed the Fly app from the plan's example `todo-app-prod` → `mealy-app-prod` directly in `backend/fly.toml`.

URL layout chosen (literal substitution of subdomain prefixes preserved):
- Frontend (Vercel): `mealy.dev`
- Backend (Fly): `api.mealy.dev`
- eTLD+1: both subdomains share `mealy.dev` → SameSite=Lax cross-subdomain cookie behavior preserved → no plan changes needed for cookie shape.

Files updated by substitution (in order: `api.todo.X` → `todo.X` → bare `X`):
- `.claude/plans/features/prod-deploy-skeleton/prod-deploy-skeleton-plan-20260422-214657.md` (33 references)
- `.claude/plans/testing/prod-deploy-skeleton-test-artifact.md` (15 references)
- `.claude/IMPLEMENTATION_PLAN.md` (3 references — locked architecture + v1.1 deferral note)
- `backend/tests/unit/test_cors_config.py` (production fail-fast test value)

Files NOT changed because the operator already updated them or they don't reference the domain:
- `backend/fly.toml` — operator renamed `app =` to `mealy-app-prod`; no domain literal in toml.
- `backend/app/main.py` — CORS uses env vars, no hardcoded domain.

Alternative collapse-to-apex layout (`mealy.dev` apex frontend + `api.mealy.dev` backend) was considered and **not chosen** to avoid the apex-CNAME complication in Slice 4 DNS setup. Substitution preserves the plan's tested CNAME-at-subdomain DNS pattern.

**2026-05-01 (later same day) — operator changed mind:** switched FROM `todo.mealy.dev` + `api.todo.mealy.dev` TO **apex layout** `mealy.dev` + `api.mealy.dev`. The `mealy.dev` domain is dedicated to this app, so the `todo.` prefix is redundant. Cloudflare CNAME flattening handles the apex constraint cleanly.

Cascade of changes from this swap:
- File substitutions (~50 references across 7 plan/note/test files): `api.todo.mealy.dev` → `api.mealy.dev`, then `todo.mealy.dev` → `mealy.dev`. Done; `pytest TestProductionFailFast` 3/3 passes after.
- Fly cert: removed pending `api.todo.mealy.dev`, added `api.mealy.dev`. New CNAME target: `emldxj1.mealy-app-prod.fly.dev` (same Fly project ID, different hostname).
- Vercel: in progress — env var `VITE_API_BASE_URL` updated to `https://api.mealy.dev`; custom-domain swap (remove `todo.mealy.dev`, add `mealy.dev` apex) pending operator UI step (Vercel apex setup wizard shows the recipe).
- Fly secret: pending — `CORS_ALLOW_ORIGINS` to be updated to `https://mealy.dev` (operator runs the secret-set so the value never enters Claude's session log).
- Cloudflare DNS: NOT yet added (operator paused before the records went in — net-positive timing).

**Pending operator decision — Vercel project rename:** operator wants to rename the Vercel project from `todo-app` to `mealy` to match the rest of the "mealy"-ification. The rename is a one-command operation (`vercel project rename todo-app mealy`); does NOT affect the custom-domain attachment or any DNS records. Holding until operator confirms timing.

## Slice 5 — code DONE 2026-05-01

**Files created/modified:**

| File | Change |
|------|--------|
| `backend/app/routes/plumbing_test.py` (new) | Two endpoints. `POST /plumbing-test` sets `__Host-plumbing-refresh` cookie (HttpOnly, Secure, Path=/, no Domain, SameSite=lax) with a fresh `secrets.token_urlsafe(32)` probe value, returns `{"set": true, "probe": "<value>"}` with `Cache-Control: no-store`. `GET /plumbing-test/read` echoes the cookie value (or null) with the same no-store header. Module-level `PROBE_SAMESITE = "lax"` and `COOKIE_NAME = "__Host-plumbing-refresh"` exported as the single source of truth — Slice 5 browser-matrix flip to "none" is a 1-line edit. |
| `backend/app/main.py` (modified) | Added `plumbing_test` to the routes import + `app.include_router(plumbing_test.router)`. CORSMiddleware already had `allow_credentials=True`, `max_age=3600` from Slice 1. |
| `backend/tests/unit/test_plumbing_test.py` (new) | 4 tests — cookie attribute drift guard (HttpOnly, Secure, Path=/, no Domain, SameSite=PROBE_SAMESITE, Cache-Control: no-store), fresh-probe-per-call, GET-null-when-no-cookie, GET-echoes-cookie-value. Imports the constants so SameSite flips stay lockstep. |
| `frontend/src/PlumbingShell.jsx` (modified) | Added "Test plumbing" button + state-machine handler. POST then GET with `credentials: 'include'`; renders idle, loading, success (exact-match), mismatch, cookie_missing (null), post_failed, post_malformed, get_failed, network_error states. Reads `import.meta.env.VITE_API_BASE_URL` inside the handler so vitest's `vi.stubEnv` per-test takes effect. |
| `frontend/tests/components/PlumbingSmoke.test.jsx` (new) | 4 tests — exact-match success, probe mismatch, cookie missing (`value: null`), and network error. Uses MSW's `http.post`/`http.get` handlers per-test plus `HttpResponse.error()` for the network-failure branch. **Deleted in M5 PR #2.** |

**Local verification:**
- `docker-compose exec api uv run pytest tests/unit/test_plumbing_test.py tests/unit/test_healthz.py tests/unit/test_cors_config.py -v` → 15/15 passed.
- `docker-compose exec frontend npm test -- tests/components/PlumbingSmoke.test.jsx tests/components/App.shell-toggle.test.jsx --run` → 6/6 passed.
- Live `curl` against dev API confirmed: POST sets the cookie with all required attrs (`SameSite=lax; Secure; HttpOnly; Path=/`, no Domain) + Cache-Control: no-store + non-empty probe; GET returns null with no cookie; round-trip via cookie jar echoes the exact probe.

**One bug caught + fixed during local test run:** initially had `PROBE_SAMESITE = "Lax"` (capitalized) per the plan literal text; Starlette emits the wire format as lowercase (`SameSite=lax`), so the cookie-attribute test failed. Fixed by changing the constant to lowercase to match what's actually on the wire — both endpoint and test use the same source of truth. Plan's Slice 5 spec accepts both casings (browsers parse SameSite case-insensitively per RFC 6265bis); the choice is purely cosmetic, but the constant should match the wire emission so the drift test stays meaningful.

## Plan metadata (from `obsidian-workflow plan-metadata-get`)

```json
{
  "metadata": {},
  "plan_path": ".claude/plans/features/prod-deploy-skeleton/prod-deploy-skeleton-plan-20260422-214657.md",
  "status": "ok"
}
```

Empty metadata → not an Obsidian-workflow plan. No Obsidian sync required at start, mid-run, or finish.

## Review state at execute time

Plan REVIEW REPORT (in plan body) verdict: **CLEARED**.

- Eng review: 3 runs, all CLEAR (initial + post-adversarial second pass + 2026-04-30 targeted Cloudflare-drift third pass)
- Adversarial review: 2 runs, all CLEAR (initial + second pass after eng rerun)
- CEO review: skipped — parent plan locked strategic scope; child plan inherited
- Design review: skipped — backend/infra plan, no UI surface beyond throwaway plumbing-test button
- Pre-landing review: deferred to `/review-implementation` after all slices ship

Session-start hook flagged "reviews incomplete" because it counts "—" entries; verified by reading the plan body that the dashes are intentional skips, not gaps.

## Slice progress

- [✓] Slice 0 — Pre-flight inventory (USER) — region picked: `sjc`; rest captured/deferred
- [✓] Slice 1 — Fly app + Postgres + `/healthz` + first deploy — DONE 2026-04-30 after 3-error debug cycle (logged in LESSONS.md as "Fly Postgres + asyncpg setup")
- [✓] Slice 2 — Upstash Redis + Celery worker + beat — DONE 2026-05-01 04:32 UTC. Beat fired first scheduled tasks at exact +600s interval; worker picked them up cleanly. Two new LESSONS.md entries: "Celery + Upstash Redis (rediss://) on Fly" and "Celery beat schedule file location under non-root containers".
- [✓] Slice 3 — R2 secrets + bucket — DONE 2026-05-01 ~04:50 UTC after a fly-secrets propagation hiccup (vault said `Deployed` but process env was missing R2_*). Resolved by re-running `fly secrets set` for R2 vars + `fly deploy --strategy immediate`. Final verification via `printenv R2_* | wc -l = 4` on web AND beat machines.
- [✓] Slice 4 — Vercel + DNS + Cloudflare Access edge gate — DONE 2026-05-01. End-to-end verified: apex (`mealy.dev`) and `api.mealy.dev/healthz` both 302 to `mealyapp.cloudflareaccess.com`; `api.mealy.dev/plumbing-test` and `/plumbing-test/read` bypass to Fly cleanly. New LESSONS.md entry: "Cloudflare Access — path-based bypass requires a SEPARATE Application" (the runbook's original Step 5d was wrong; corrected in place). `infra/cloudflare-state.md` updated to reflect the two-Application structure; 3 user-fillable TODOs left (Cloudflare account ID, zone ID, two Application names).

## Slice 4 — code DONE 2026-05-01

| File | Change |
|------|--------|
| `frontend/src/PlumbingShell.jsx` (new) | M2-only placeholder. Tailwind-styled, no fetches, no providers required. Slice 5 adds the "Test plumbing" button + cookie round-trip logic. |
| `frontend/src/App.jsx` (modified) | 3-line guard at top: `if (import.meta.env.VITE_M2_SHELL === 'true') return <PlumbingShell />`. Preserves existing Routes tree for dev/CI/visual-tests where the env is unset. |
| `frontend/tests/components/App.shell-toggle.test.jsx` (new) | Pins both branches: `=true` → PlumbingShell renders + CalendarPage stub does NOT; unset → CalendarPage stub renders + PlumbingShell does NOT. Page imports stubbed via `vi.mock` so the test doesn't need DarkModeProvider/ToastProvider context. **Deleted in M5 PR #2.** |
| `frontend/vercel.json` (new) | SPA rewrites + cache headers (`index.html` → no-cache + must-revalidate; `/assets/*` → 1-year immutable). Located in `frontend/` to match the typical Vite-SPA Vercel project root. |
| `infra/cloudflare-state.md` (new — also creates `infra/` directory) | Canonical intent file with the schema from plan Constraints. TODO placeholders for actual zone/account IDs, IDP choice, session duration — operator fills in during platform actions. Bypass section pre-populated with the two exact `/plumbing-test*` regexes. |

**`frontend/src/main.jsx` audit:** clean — no boot-time API calls, only Provider wiring. No change needed.

**Tests (via Docker):** `docker-compose exec frontend npm test -- tests/components/App.shell-toggle.test.jsx --run` → 2/2 passed.

**Dev sanity:** `curl http://localhost:5173/src/App.jsx` returns 200, Vite-transformed JSX shows the new `PlumbingShell` import resolving.

**Judgment calls flagged:**
1. `vercel.json` location: `frontend/vercel.json` (assumes Vercel project Root Directory is `frontend/`). If you set Vercel root to `.` (repo root), move the file to repo root and the Vercel build command needs `--cwd frontend` or similar.
2. PlumbingShell uses Tailwind utilities (already in `index.css`). Still self-contained — no other module references styles defined here, so M5 PR #2 deletion is still a single `git rm`.
3. `infra/cloudflare-state.md` Bypass section pre-populated with both regex variants noted in the plan; you can pick one when configuring Cloudflare Access.

**⚠️ Open security item from Slice 3:** Four secret values exposed via unfiltered `printenv` early in Slice 3 verification. Rotation pending operator decision: `DATABASE_URL` Postgres password, `JWT_SECRET_KEY`, `HOUSEHOLD_ACCESS_KEY`, `REDIS_URL` token (FERNET_KEY excluded — rotation breaks stored iCloud creds per LESSONS.md / parent plan line 152). LESSONS.md updated with hard rule against unfiltered env dumps + the safe-pattern catalog.
- [✓] Slice 5 — `/plumbing-test` + cookie round-trip + browser matrix — DONE 2026-05-01. Production cookie round-trip verified end-to-end through Cloudflare proxy: `__Host-plumbing-refresh` cookie set on `api.mealy.dev` with `HttpOnly; Path=/; SameSite=lax; Secure` (no Domain), `cache-control: no-store`, exact-value echo on the read. **Browser matrix all 5 cells PASS with SameSite=Lax** → Lax is the canonical M3 value (no fallback to None needed). One bug fixed during Slice 5 dev: `PROBE_SAMESITE` constant changed `"Lax"` → `"lax"` to match Starlette's wire emission, so the drift test stays meaningful.
- [✓] Slice 6 — Cloudflare rate-limit + `migration-upgrade` CI job — DONE 2026-05-01. WAF rule active on `(starts_with(http.request.uri.path, "/auth/"))` with 5 req/10s/IP threshold (free-tier max — see `infra/cloudflare-state.md` for the deviation note). Burst-test 10 requests via `slice6-rate-limit-burst-test.sh` returned 5×404 + 5×429 — exactly the expected pattern. Migration-upgrade CI job lands on the PR (Slice 7). Backend-tests Postgres bumped 15→16 to match prod.
- [~] **Slice 7 — Final sweep + PR to master** — pending

## Slice 0 — Pre-flight inventory (USER) — DONE

**Status:** User confirmed inventory captured (or deferred to relevant slice).
**Region pick:** `sjc` (San Jose).
**Decisions deferred:**
- Cloudflare Access IDP: defaulting to **OTP** unless user changes mind in Slice 4 (Open Question #2).
- Vercel project ID: deferred to Slice 4 (project may be created at that point).
- R2 + Upstash provisioning: deferred to Slices 2/3 platform-action steps.
**Confirmed:**
- `JWT_SECRET_KEY` + `HOUSEHOLD_ACCESS_KEY` generated via `openssl rand -hex 32`, captured locally (NOT shared with assistant).
- `FERNET_KEY` captured byte-identical from local `backend/.env` for Slice 1 secrets-set step.

## Slice 1 — Fly app + Postgres + /healthz — code DONE, awaiting platform actions

**Status:** Code complete and verified locally. Platform actions + first deploy are user's.
**Files created/modified:**

| File | Change |
|------|--------|
| `backend/fly.toml` (new) | `web` process group only, `primary_region = "sjc"`, `build_target = "prod"` pinned, `release_command = "alembic upgrade head"`, `auto_stop_machines = false`, `min_machines_running = 1`, `[[services.http_checks]]` against `/healthz`, `[[vm]] shared-cpu-1x / 512mb`. App name defaulted to `todo-app-prod` — user can override at `fly apps create` time and edit toml to match. |
| `backend/app/main.py` (modified) | (a) `_parse_cors_origins(raw, app_env=None)` now raises `RuntimeError("CORS_ALLOW_ORIGINS must be set when APP_ENV=production")` at import time when `APP_ENV=production` and origins are unset/empty (dev path preserved). (b) New `GET /healthz` returns `{"status": "ok"}` unconditionally — shallow probe, plain dict, no Pydantic. (c) `CORSMiddleware` gained `max_age=3600` (Constraints carryover; Slice 5 verification will trivially pass). |
| `backend/tests/unit/test_healthz.py` (new) | Pins exact-equality body shape `{"status": "ok"}` so future drift adding hostname/version/env/db-status fields fails this test. |
| `backend/tests/unit/test_cors_config.py` (extended) | `TestProductionFailFast` class with three cases: unset-in-prod raises; set-in-prod returns the list; unset-in-dev (and unset-in-`development`) returns localhost defaults. |

**Local verification:**
- `docker-compose exec api uv run pytest tests/unit/test_healthz.py tests/unit/test_cors_config.py -v` → 11/11 passed (1 healthz + 7 existing CORS + 3 new fail-fast).
- `curl http://localhost:8000/healthz` → `200 {"status":"ok"}` (live dev container).
- `curl http://localhost:8000/` → still `200 {"message":"To-Do + Recipe API is running!"}` (no regression).

**Judgment calls flagged for review:**
1. App name `todo-app-prod` in `fly.toml` — plan's example. User can change both the toml `app =` and the `fly apps create <name>` command in lockstep if a different name is wanted.
2. VM size `shared-cpu-1x` / `512mb` — plan didn't specify. 512mb gives async-Python + asyncpg-pool headroom. Cheaper option is 256mb; risk is OOM under request bursts.
3. `auto_start_machines = true` — explicit even though it's the Fly default; redundant with `min_machines_running = 1` but documents intent.
4. `max_age=3600` added to `CORSMiddleware` in Slice 1 even though the plan files-modified inventory phrases it as `(c) max_age confirmation` (a verification, not a Slice 1 add). Reasoning: I'm already in the middleware block; bundling avoids a Slice 5 backtrack. If you want it deferred to Slice 5, say so and I'll revert the one line.

**Deploy debug log:** First three `fly deploy` attempts failed at `release_command` (alembic upgrade) due to compounding Fly Postgres + asyncpg URL footguns:

1. `gaierror: Name or service not known` — placeholder host left unsubstituted in `DATABASE_URL`.
2. `TypeError: connect() got an unexpected keyword argument 'sslmode'` — asyncpg rejects `sslmode=` URL kwarg (psycopg2-only).
3. `ConnectionResetError` in `_create_ssl_connection` — asyncpg's default `ssl=prefer` tried TLS handshake; Fly internal Postgres reset mid-stream → had to add `?ssl=disable` explicitly.

Final working URL form: `postgresql+asyncpg://USER:PASS@<app>-db.flycast:5432/DB?ssl=disable`. Captured to `.claude/LESSONS.md` as a single canonical reference for future Fly setup work.

**DONE-WHEN proven:**
- `curl -i https://mealy-app-prod.fly.dev/healthz` → HTTP/2 200, content-length 15 (= length of `{"status":"ok"}`, exact body match)
- `fly status` → 2× web machines in sjc, both `started`, both passing health checks (Fly defaulted to 2 for redundancy; floor of 1 satisfied)
- Alembic ran cleanly (deploy reached "started" — release_command success implied)

## Slice 2 — Upstash Redis + Celery worker + beat — code DONE, awaiting platform actions

**Files modified:**

| File | Change |
|------|--------|
| `backend/fly.toml` | Added `worker` and `beat` to `[processes]` (each runs `celery -A app.celery_app worker/beat --loglevel=info`). Added `[[vm]]` blocks: worker = 512mb, beat = 256mb (lightweight scheduler). Web `[[services]]` block unchanged. Beat singleton invariant comment added; enforcement is via `fly scale count beat=1` at deploy time. |

**Verified in place (no change needed):**
- `backend/app/celery_app.py:4` already reads `REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")` — direct env-var read, no scheme rewriting. Both `redis://` (local docker) and `rediss://` (Upstash TLS) work env-only. Plan's Slice 2 audit requirement ("verify REDIS_URL env is read directly without scheme rewriting") satisfied as-is.

**Subsequent code changes during deploy debug** (logged in LESSONS.md as canonical reference):
- `backend/app/celery_app.py` — added gated `broker_use_ssl` / `redis_backend_use_ssl` config that activates only when `REDIS_URL.startswith("rediss://")`. Celery rejects either direction without scheme-config match: `rediss://` without ssl_cert_reqs raises `E_REDIS_SSL_CERT_REQS_MISSING_INVALID`; `redis://` with ssl options raises `E_REDIS_SSL_PARAMS_AND_SCHEME_MISMATCH`. Gating on the URL scheme satisfies both paths from one codebase.
- `backend/fly.toml` — beat command extended with `--schedule=/tmp/celerybeat-schedule`. The default `celerybeat-schedule` shelve location is the cwd (`/app`), which is owned by root in the prod image; running as `appuser` (per Dockerfile) means beat can't open the shelve and crashes inside `setup_schedule()`. `/tmp` is writable to all users; loss-on-restart is fine because beat re-derives entries from `celery_app.conf.beat_schedule` on boot.

**Deploy debug log:** Three `fly deploy` attempts to ship Slice 2 cleanly — each surfaced a real Celery+Upstash+container gotcha:

1. v5 (broken `broker_use_ssl` absent) → `E_REDIS_SSL_CERT_REQS_MISSING_INVALID`. Fix: add `broker_use_ssl` / `redis_backend_use_ssl`.
2. v6 (unconditional `broker_use_ssl`) → broke local docker-compose with `E_REDIS_SSL_PARAMS_AND_SCHEME_MISMATCH`. Fix: gate on URL scheme.
3. v7 (gated SSL but default beat schedule path) → beat crashes on shelve open in `/app` (appuser can't write). Fix: `--schedule=/tmp/celerybeat-schedule`.

v8 (final) deployed clean. Worker booted and connected to Upstash. Beat process verified alive (PID 634 via SSH), shelve file written to `/tmp/celerybeat-schedule` (16KB), `beat: Starting...` logged.

**DONE-WHEN status:**
- ✅ `fly machine list` — all machines started: 2× web + 1× worker + 1× beat in sjc.
- ✅ `fly scale show` — `web=2, worker=1, beat=1` (load-bearing `beat=1` invariant satisfied).
- ✅ Worker boot — connected to `rediss://default:**@helped-gibbon-71427.upstash.io:6379//`, 14 tasks registered, `celery@<id> ready`.
- ⏳ Beat scheduler tick — beat process is alive but first scheduled task fires at startup+600s (Celery `last_run_at = now()` initialization for fresh shelve entries). Polling in background until first `Sending due task` line lands.

## Lessons cross-reference for upcoming slices

From `.claude/LESSONS.md`:

- **Use Docker Compose for app commands** — when Slice 1 tests run locally, use `docker-compose exec api uv run pytest tests/unit/test_healthz.py -v` (not host `pytest`).
- **Verify behavior, not declarations** — every slice has explicit DONE-WHEN checkpoints; treat them as load-bearing, not boilerplate. "Compiles" / "deployed" / "logs look quiet" is not enough; each item in DONE-WHEN must be observed.
- **Verify current state before claiming status** — for slice handoffs, DONE-WHEN is the authority. Don't proceed to next slice's code until the user explicitly confirms the prior slice's DONE-WHEN passed.
