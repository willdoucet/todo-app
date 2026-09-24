# Tech Stack Documentation

> Every package, dependency, API, and tool locked to exact versions.

---

## Table of Contents

1. [Frontend Dependencies](#1-frontend-dependencies)
2. [Backend Dependencies](#2-backend-dependencies)
3. [Development Tools](#3-development-tools)
4. [Infrastructure](#4-infrastructure)
5. [Version Constraints](#5-version-constraints)
6. [API Contracts](#6-api-contracts)
7. [Browser Support](#7-browser-support)
8. [File Structure Reference](#8-file-structure-reference)

---

## 1. Frontend Dependencies

Versions below are the resolved entries in `frontend/package-lock.json` (what actually installs); the semver ranges that *allow* them live in `frontend/package.json`.

### Core Framework

| Package | Locked version | Purpose |
|---------|---------|---------|
| `react` | 19.2.3 | UI framework |
| `react-dom` | 19.2.3 | React DOM renderer |
| `react-router-dom` | 7.12.0 | Client-side routing |
| `vite` | 7.3.1 | Build tool and dev server |

### UI Libraries

| Package | Locked version | Purpose |
|---------|---------|---------|
| `tailwindcss` | 4.1.18 | Utility-first CSS framework |
| `@tailwindcss/vite` | 4.1.18 | Vite plugin for Tailwind |
| `@headlessui/react` | 2.2.9 | Unstyled accessible UI components (modals, dialogs) |
| `@heroicons/react` | 2.2.0 | SVG icon library |
| `emoji-mart` | 5.6.0 | Emoji picker (lazy-loaded in `components/shared/EmojiPicker.jsx`) |
| `@emoji-mart/data` | 1.2.1 | Emoji dataset for `emoji-mart` |
| `@formkit/auto-animate` | 0.9.0 | Drop-in list/mount animations |

### Data & State

| Package | Locked version | Purpose |
|---------|---------|---------|
| `axios` | 1.13.2 | HTTP client for API calls |
| `@tanstack/react-query` | 5.90.19 | Server state management (available, not fully integrated) |

### Utilities

| Package | Locked version | Purpose |
|---------|---------|---------|
| `react-swipeable` | 7.0.2 | Touch swipe gestures |

### Dev Dependencies

| Package | Locked version | Purpose |
|---------|---------|---------|
| `@vitejs/plugin-react` | 5.1.2 | React plugin for Vite |
| `@types/react` | 19.2.9 | TypeScript types for React |
| `@types/react-dom` | 19.2.3 | TypeScript types for React DOM |
| `eslint` | 9.39.2 | JavaScript linter |
| `@eslint/js` | 9.39.2 | ESLint JavaScript rules |
| `eslint-plugin-react-hooks` | 7.0.1 | React Hooks linting rules |
| `eslint-plugin-react-refresh` | 0.4.26 | React Refresh linting |
| `globals` | 16.5.0 | Global variables for ESLint |
| `prettier` | 3.8.1 | Code formatter |
| `knip` | 6.4.0 | Dead-code / unused-export detection (`npm run hygiene`) |

### Testing

| Package | Locked version | Purpose |
|---------|---------|---------|
| `vitest` | 2.1.9 | Test runner |
| `@vitest/coverage-v8` | 2.1.9 | Code coverage |
| `@testing-library/react` | 16.3.2 | React testing utilities |
| `@testing-library/jest-dom` | 6.9.1 | Jest DOM matchers |
| `@testing-library/user-event` | 14.6.1 | User event simulation |
| `jsdom` | 24.1.3 | DOM environment for tests |
| `msw` | 2.12.7 | API mocking (Mock Service Worker) |
| `@playwright/test` | 1.49.0 | Visual-regression runner; pinned to match the `mcr.microsoft.com/playwright` base image ARG in `frontend/Dockerfile` |

---

## 2. Backend Dependencies

Versions below are the resolved entries in `backend/uv.lock`; the lower-bound constraints that *allow* them live in `backend/pyproject.toml`.

### Core Framework

| Package | Locked version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.128.0 | Async web framework |
| `uvicorn` | 0.40.0 | ASGI server |
| `pydantic` | 2.12.5 | Data validation and serialization |

### Database

| Package | Locked version | Purpose |
|---------|---------|---------|
| `sqlalchemy` | 2.0.45 | ORM and database toolkit |
| `asyncpg` | 0.31.0 | Async PostgreSQL driver |
| `psycopg[binary]` | 3.3.2 | PostgreSQL adapter |
| `greenlet` | 3.3.0 | Async support for SQLAlchemy |
| `alembic` | 1.18.0 | Database migrations |

### Background Jobs & Messaging

| Package | Locked version | Purpose |
|---------|---------|---------|
| `celery[redis]` | 5.6.2 | Distributed task queue with Redis broker |
| `redis` | 6.4.0 | Redis client for Celery broker/backend |

### Calendar Integration

| Package | Locked version | Purpose |
|---------|---------|---------|
| `caldav` | 2.2.6 | CalDAV protocol client (iCloud calendar access) |
| `icalendar` | 6.3.2 | ICS/iCalendar parsing and generation |
| `cryptography` | 46.0.5 | Fernet encryption for stored app-specific passwords |

### AI & Web Extraction

| Package | Locked version | Purpose |
|---------|---------|---------|
| `anthropic` | 0.96.0 | Anthropic Python SDK for Claude API (AI recipe extraction + suggest-icon) |
| `recipe-scrapers` | 15.11.0 | Recipe structured data extraction from 631+ cooking sites |
| `beautifulsoup4` | 4.14.3 | HTML cleaning before LLM extraction |
| `httpx` | 0.28.1 | HTTP client for fetching web pages (prod dep; also used by the test suite) |

### Auth (M3)

| Package | Locked version | Purpose |
|---------|---------|---------|
| `argon2-cffi` | 25.1.0 | OWASP-recommended password hashing for the singleton household login |
| `PyJWT` | 2.12.1 | HS256 JWT encode/decode for short-lived access tokens |
| `email-validator` | 2.3.0 | Backs Pydantic's `EmailStr` field on `RegisterIn` / `LoginIn` |

Related env vars: `JWT_SECRET_KEY` (required at runtime in production — must be ≥32 chars and pass the placeholder deny-list), `HOUSEHOLD_ACCESS_KEY` (required at runtime in production — gates first-run register), `APP_ENV` (set to `production` to enable the production host gate + fail-closed secret validation), `PUBLIC_API_HOST` (used by the host gate to identify the legitimate public API domain in production), `ORIGIN_VERIFY_SECRET` (required at runtime in production — ≥32 chars; the host gate also requires a matching `X-Origin-Verify` header, which Cloudflare's origin-lock Transform Rule adds).

Related env vars: `ANTHROPIC_API_KEY` (required at runtime for `/items/import-from-url` worker + `/items/suggest-icon`), `AI_MODEL_NAME` (default `claude-haiku-4-5-20251001`). Both are read by `app/services/ai_client.py`.

Build note: the `Dockerfile` builder stage installs `libxml2-dev`, `libxslt-dev`, and `gcc` so `lxml` (transitive dep of `recipe-scrapers`) compiles on `python:3.12-slim`.

### Utilities

| Package | Locked version | Purpose |
|---------|---------|---------|
| `python-multipart` | 0.0.22 | File upload handling |
| `boto3` | 1.43.90 | S3-compatible client for Cloudflare R2 object storage (M7). `R2Backend` selected via `STORAGE_BACKEND=r2`; default `local` keeps dev/test on disk. |
| `tzdata` | 2025.3 | IANA timezone database (required for `zoneinfo` on slim Docker images) |

### Development

| Package | Locked version | Purpose |
|---------|---------|---------|
| `ipykernel` | 7.1.0 | Jupyter notebook support |

### Testing

| Package | Locked version | Purpose |
|---------|---------|---------|
| `pytest` | 9.0.2 | Test framework |
| `pytest-asyncio` | 1.3.0 | Async test support |
| `pytest-cov` | 7.0.0 | Code coverage |
| `httpx` | 0.28.1 | Async HTTP client for tests |
| `factory-boy` | 3.3.3 | Test data factories |
| `testcontainers[postgres]` | 4.14.1 | Containerized test databases |
| `aiosqlite` | 0.22.1 | Async SQLite driver for isolated unit-level DB tests |
| `moto[s3]` | 5.2.3 | In-process S3 mock (`@mock_aws`) for `R2Backend` tests — keeps the docker-compose test stack R2-free (M7) |

---

## 3. Development Tools

### Package Managers

| Tool | Version | Purpose |
|------|---------|---------|
| `uv` | 0.5.24 (pinned in `backend/Dockerfile`) | Python package manager (NOT pip) |
| `npm` | bundled with Node 20 | JavaScript package manager |
| Node.js | 20 (`node:20-slim` in `frontend/Dockerfile`; `node-version: '20'` in CI). Vite 7 requires ≥ 20.19 | JavaScript runtime |
| Python | >=3.12 | Python runtime |

### Containerization

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | Latest | Containerization |
| Docker Compose | Latest | Multi-container orchestration |

### Database

| Tool | Version | Purpose |
|------|---------|---------|
| PostgreSQL | 16 | Primary database (docker-compose) |

---

## 4. Infrastructure

### Docker Services

```yaml
# docker-compose.yml services

db:
  image: postgres:16
  ports: "5433:5432"

redis:
  image: redis:7-alpine
  ports: "6379:6379"

api:
  build:
    context: ./backend
    target: dev          # Multi-target: 'dev' (test deps + uv) or 'prod' (slim)
  ports: "8000:8000"
  depends_on: db, redis

celery_worker:
  # Same image as api, runs: celery -A app.celery_app worker
  depends_on: db, redis

celery_beat:
  # Same image as api, runs: celery -A app.celery_app beat
  # 10-min periodic sync for all active iCloud integrations
  depends_on: redis

frontend:
  build:
    context: ../frontend
    target: dev         # Multi-target: 'dev' (Vite HMR) | 'preview' (vite preview) | 'visual-test' (Playwright)
  ports: "5173:5173"

# --profile visual-test (off by default; see development-commands.md)
api-test:
  build: { context: ., target: dev }   # NO bind-mount for app/ — bakes the backend in at build time
  # DATABASE_URL → todo_app_test; runs alembic upgrade head + seeds on boot

frontend-preview:
  build: { context: ../frontend, target: preview, args: { VITE_API_BASE_URL: http://api-test:8000 } }
  ports: "4173:4173"

frontend-visual:
  build: { context: ../frontend, target: visual-test }   # Playwright + Chromium, pinned base image
```

**Multi-target Dockerfile:** The backend Dockerfile has three stages:
- `builder` — installs prod deps with uv
- `dev` — extends builder, adds test extras (pytest, httpx, testcontainers), keeps uv available
- `prod` — slim runtime image, no test deps, no uv

### Environment Variables

**Backend (.env)**
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/todo_app
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/todo_app_test
UPLOAD_DIR=/app/uploads
REDIS_URL=redis://redis:6379/0
FERNET_KEY=<base64-encoded-fernet-key>   # For encrypting stored iCloud passwords
ANTHROPIC_API_KEY=<optional>             # AI recipe import (/items/import-from-url) + suggest-icon; empty disables
AI_MODEL_NAME=claude-haiku-4-5-20251001  # Model for the above (compose default)
STORAGE_BACKEND=local                    # local | r2 (unknown values raise). Prod runs r2.
SQLALCHEMY_ECHO=false                    # true opts into SQL logging; default off
STOCK_ICONS_DIR=/app/stock_icons_src     # Bundled stock icons; served by the media read route
```

**Production-only (Fly)** — `APP_ENV=production`, `PUBLIC_API_HOST`, `ORIGIN_VERIFY_SECRET`, `CORS_ALLOW_ORIGINS`,
and the four R2 credentials (`R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
`R2_BUCKET_NAME`) are set as Fly secrets. (The SQLAlchemy engine pool is not env-tunable —
`app/database.py` uses the SQLAlchemy defaults plus `pool_pre_ping` and `pool_recycle`.) `STORAGE_BACKEND=r2` is the one exception: it lives in `backend/fly.toml` `[env]`
rather than a secret, because it is not secret and versioning it with the code makes a
rollback revert the storage flip atomically. See
[Object storage](#object-storage-cloudflare-r2) below. `GATE_BREAK_GLASS` (M8) lives there too,
as `"0"`, for the same reason: only the exact string `"1"` turns the host gate's origin check
off during a Cloudflare outage, it is enabled per release with `fly deploy -e`, and a secret
would survive the clearing redeploy (`infra/incident-diagnostics.md` → Break-glass). `GIT_COMMIT`
is not a runtime variable either: it is the Dockerfile `prod` stage's build arg
(`fly deploy --build-arg GIT_COMMIT=<sha>`, RUNBOOK §2), which `/healthz` reports as `version`.

**Frontend (.env.local)**
```
VITE_API_BASE_URL=http://localhost:8000
```

`VITE_GIT_COMMIT` is build-time only and never set by hand: Vercel's `buildCommand` passes
`VERCEL_GIT_COMMIT_SHA`, and CI passes `GITHUB_SHA`. Vite writes it into `index.html`'s
`<meta name="build-commit">`; a local or visual-test build leaves the literal
`%VITE_GIT_COMMIT%`, which smoke check 8 treats as a failure. It is a commit SHA of this public
repository, so nothing secret reaches the bundle.

**Operator-only (never an app runtime variable)** — `CLOUDFLARE_API_TOKEN`: a read-only token
held in the operator's shell for `infra/cloudflare-drift.py`; its scopes are listed in the
[`infra/RUNBOOK.md`](../../infra/RUNBOOK.md) header. Never in CI (scheduling the drift script
is a v1.1 item). `FLY_API_TOKEN` (M8): a GitHub Actions secret for `ops-check.yml` only — a
`fly tokens create readonly` token (org-scoped, read-only, one-year expiry, rotation date in the
RUNBOOK header); nothing else in CI holds a Fly credential.

### Ports

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5433 (external) / 5432 (internal) | Database |
| Redis | 6379 | Celery broker and result backend |
| FastAPI | 8000 | Backend API |
| Vite Dev | 5173 | Frontend development |
| Vite Preview | 4173 | `frontend-preview` (visual-test profile only) |

### CI/CD Pipeline

| Tool | Purpose |
|------|---------|
| GitHub Actions | CI/CD automation |
| `.github/workflows/test.yml` | Run tests on push/PR |
| `.github/workflows/doc-guard.yml` | On pull requests: `.agents/bin/doc-guard --range` refuses merges that change a documented code area without updating its owning doc (see `.agents/WORKFLOW.md`) |
| `.github/workflows/ops-check.yml` | M8: the check between releases — daily at 14:17 UTC and on `workflow_dispatch` (`self_test` input), runs `python3 infra/release-smoke.py --only=liveness,recoverability,edge` with flyctl `0.4.102` (the setup action installs only a `flyctl` binary, so a step links it as `fly`, the name the script runs) and the `FLY_API_TOKEN` secret, which only the two smoke steps receive; retries once after 60 s, then fails the job (GitHub's failure email is the alert; the failing lines and the `exit 1 production:` / `exit 2 tooling:` summary become error annotations, because the email never carries step output). `timeout-minutes: 25` covers both attempts at their worst, and the output streams to the log. Scheduled workflows only fire from the default branch, and GitHub disables them on a public repository after 60 days without a commit (RUNBOOK header) |
| `.github/workflows/deploy.yml` | Deploy to production (deferred to v1.1; the M8 manual runbook, [`infra/RUNBOOK.md`](../../infra/RUNBOOK.md), comes first) |

**CI Pipeline (Current)** — `.github/workflows/test.yml`, on push to `master` and on pull
requests to `master`. Five jobs, no `needs:` between them, so they run in parallel:

| Job | Services | Runs |
|---|---|---|
| `backend-tests` | postgres:16, redis:7 | `uv run pytest tests/unit` then `uv run pytest tests/integration` |
| `frontend-tests` | — | `npm run lint`, `npm run test:run` (Vitest, single-run), then `VITE_GIT_COMMIT=$GITHUB_SHA npm run build` (with the production `VITE_API_BASE_URL`) and a grep that `dist/index.html` carries that SHA in `<meta name="build-commit">` (M8: proves smoke check 8's stamp and runs the production build as its own step) |
| `infra-tests` | — | `python3 -m pytest infra/tests -q` on Python 3.12, pytest the only install (M8: the host-side operator scripts; every `fly`/`curl`/`git` call and the Cloudflare API are faked) |
| `visual-tests` | docker-compose `visual-test` profile | Playwright against `vite preview` + a baked `api-test` backend |
| `migration-upgrade` | postgres:16 | `alembic upgrade head` from base, then newest-revision down/up symmetry |

Jobs run pytest **on the runner, not in a container**, so any container-only path a test
depends on must be supplied through the job's `env:` block: `UPLOAD_DIR=/tmp/uploads`
(`app/main.py` mkdirs it at import) and, since M7 PR2, `STOCK_ICONS_DIR` pointed at
`backend/stock_icons` (the media read route serves bundled stock icons from
`/app/stock_icons_src`, which exists only inside the image).

Secrets consumed: `CI_FERNET_KEY` (integration + visual), `CI_JWT_SECRET_KEY` and
`CI_HOUSEHOLD_ACCESS_KEY` (visual). The visual job fails fast with an actionable error when
any is unset.

`frontend-tests` also runs `npm run lint` (gated since M7 PR2; it had been red for months on
two ESLint config gaps with nothing running it — Node globals for `playwright.config.js`, and
`react-hooks/rules-of-hooks` firing on Playwright's `use()` fixture hand-off under
`tests/visual/**`).

**CD Pipeline (Planned):**
```yaml
on:
  push:
    branches: [main]
jobs:
  deploy:
    - Run CI tests
    - Build Docker images
    - Push to container registry
    - Deploy to hosting platform
```

### Production Deployment (live since M2, 2026-05-01)

Chosen and shipped in the v1 productionization epic ([plan](../plans/features/prod-contract-freeze/prod-contract-freeze-plan-20260421-182714.md), M2 deploy skeleton PR #26). Railway, Render and Supabase were considered and not chosen.

| Component | Service | Purpose |
|-----------|---------|---------|
| Frontend | Vercel | `mealy.dev` — static SPA with CDN. Since M8 the git integration builds every `master` merge but no longer promotes it: Settings → Environments → Production → Branch Tracking → "Auto-assign Custom Production Domains" is off, so a build sits **Staged** until [`infra/RUNBOOK.md`](../../infra/RUNBOOK.md) promotes it *after* the Fly deploy (backend first). `frontend/vercel.json`'s `buildCommand` (`VITE_GIT_COMMIT=$VERCEL_GIT_COMMIT_SHA npm run build`) stamps the commit into `<meta name="build-commit">`, which needs Settings → Environment Variables → "Automatically expose System Environment Variables" on |
| Backend | Fly.io (`mealy-app-prod`, region `sjc`) | `api.mealy.dev` — `web` (uvicorn), `worker` (Celery), `beat` (scheduler) process groups; `backend/fly.toml`. Counts: `web=1`, `worker=1`, `beat=1` (M8, Eng review 1C), set out-of-band with `fly scale count` (`fly.toml` cannot express them), pinned in [`infra/fly-scale.json`](../../infra/fly-scale.json) and asserted by smoke check 3; `beat=1` is invariant. Deployed by hand with the release runbook. `worker` and `beat` carry `[[restart]] policy = "always"` so a stopped machine comes back on its own |
| Database | Fly Postgres Flex (unmanaged) | `mealy-app-prod-db`, image `flyio/postgres-flex:17.2` (compose and CI run 16; TODOS P3), volume `pg_data` with scheduled snapshots (5-day retention). Continuous WAL backups (`fly pg backup`) are M8 item 12; smoke check 9 reports both mechanisms and the restore drill is [`infra/backup-restore-drill.md`](../../infra/backup-restore-drill.md). `asyncpg` with `ssl=` (see LESSONS.md) |
| Redis | Upstash | Celery broker + result backend over `rediss://`. Upstash bills per command and a Celery worker polls even when idle, so the worker runs `--without-gossip --without-mingle --without-heartbeat` (single-worker deployment: those only coordinate a cluster) |
| File Storage | Cloudflare R2 | User uploads (photos, icons) — provisioned in M2; **cutover executed 2026-09-11** (M7 PR2, #44; execution log in `infra/r2-cutover-runbook.md`); see Object storage below |
| DNS / edge | Cloudflare | Proxied DNS for both hosts, WAF rate limit on `/auth/*`, origin-lock Transform Rule (sets the `X-Origin-Verify` header the host gate requires), Browser Cache TTL "Respect Existing Headers" (private media relies on it); Access Application 1 removed at M7's cutover (2026-09-11); `infra/cloudflare-state.md` |
| SSL | Auto-provisioned | Let's Encrypt via Fly (API) and Vercel (frontend); Cloudflare terminates at the edge |

**Deployment Options:**

1. **Cloud Hosted (Primary)** - Users visit public URL, no setup required
2. **One-Click Deploy** - Heroku/Railway deploy buttons for self-hosting
3. **Docker Compose** - For advanced users running locally

### Object storage (Cloudflare R2)

From the M7 PR2 cutover onward (runbook executed 2026-09-11), production stores every user
upload in R2 (S3-compatible, via boto3) and serves it back through the authenticated
`GET /uploads/{key}` route. Dev, CI, and the visual-test stack stay on local
disk — they must not gain an R2 dependency.

| | Where | Why there |
|---|---|---|
| `STORAGE_BACKEND=r2` | `backend/fly.toml` `[env]` | Not secret, and versioned with the code so a rollback reverts the flip atomically. As a Fly secret it would survive a code rollback, leaving the previous release writing to R2 while reading from disk. |
| `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` | Fly secrets | Credentials. Provisioned in M2; first used in M7. |

Reads and writes must flip together — an R2-written object 404s against a disk-backed read.
The operator procedure, pre-cutover gates, smoke checks, and the three rollback windows are in
[`infra/r2-cutover-runbook.md`](../../infra/r2-cutover-runbook.md). Cloudflare Access /
WAF state is in [`infra/cloudflare-state.md`](../../infra/cloudflare-state.md).

**Same-site is a deployment constraint, not just a detail.** Private images are served by a
cookie-authenticated route, and the `SameSite=Strict` `__Host-refresh` cookie only rides an
`<img>` subresource load when the frontend origin and `api.mealy.dev` are the *same site*.
`mealy.dev` and `api.mealy.dev` share eTLD+1, so production works. `*.vercel.app` is on the
Public Suffix List, so **every Vercel preview origin is a different site and every image 401s
there** — expected, not a regression; see the runbook and the P3 entry in
[TODOS.md](./TODOS.md). Moving the frontend off a `mealy.dev` subdomain would break private
image reads in production.

### Operator tooling (`infra/`)

Since M8 the release is a written procedure with mechanical checks. Everything here runs on the
operator's **host**, never in a container: the scripts shell out to `fly`, `curl` and the
Cloudflare API with the operator's own credentials (a host-side exception in
[development-commands.md](./development-commands.md)). Standard library only, Python ≥ 3.11
(`tomllib`); minimum flyctl v0.4.102.

| File | Purpose |
|---|---|
| [`RUNBOOK.md`](../../infra/RUNBOOK.md) | The release procedure: gates, backend-first deploy, promote, smoke, Cloudflare and manual checks, tagging (`v1-<UTC date>-<short sha>`), rollback as two doctrines, execution log |
| [`incident-diagnostics.md`](../../infra/incident-diagnostics.md) | One entry per known failure mode (symptom, distinguishing signal, ordered recovery), including break-glass Mode A/B; every smoke failure line links an entry |
| [`backup-restore-drill.md`](../../infra/backup-restore-drill.md) | Snapshot and point-in-time restores into dated scratch clusters, with the observed numbers and a restore-point log |
| `release-smoke.py` | Mechanical assertions in four groups (`release`, `liveness`, `recoverability`, `edge`); exit `0` pass, `1` production, `2` tooling; `--only`, `--skip` (PR1b-only `/healthz` keys print `skipped`, never `pass`), `--release-commit`, `--self-test`. Liveness includes `[1] version-reported` (a real commit SHA on `/healthz`, for the cron). Reads `paused.json`: a declared group must be stopped, and its checks print `PAUSE`, never `pass`; jobs-fresh fails once a job has succeeded on a later day than the worker's pause, or beat's when only beat is declared (a resume nobody declared) |
| `cloudflare-drift.py` | Read-only diff of the live WAF rule, origin-lock Transform Rule (presence only; the header value is dropped at parse), Browser Cache TTL, Access apps and Bot Fight Mode against `cloudflare-state.md` |
| `fly-scale.json` | The pinned machine counts smoke check 3 diffs against; its keys must equal `fly.toml [processes]` |
| `paused.json` | M8: a deliberate pause of `worker` and/or `beat` (`since`, `review_by`, `reason`; `{}` means none). Past `review_by` the pause fails every run, and a `review_by` more than 31 days out is exit 2. Declared 2026-09-23 at the Upstash request cap (TODOS.md P1) |
| `cloudflare-state.md`, `r2-cutover-runbook.md` | Cloudflare intent (the drift script's diff target) and the executed M7 cutover |

`infra/*.md` is exempt from the doc map (an execution-log row is not a documented-surface
change); the scripts and `fly-scale.json` route here. Tests: `python3 -m pytest infra/tests -q`,
also the `infra-tests` CI job.

### External API Integrations

| Service | Purpose | Auth Method | Status |
|---------|---------|-------------|--------|
| iCloud Calendar | Two-way calendar sync | App-specific password / CalDAV | Built |
| Google Calendar | Two-way calendar sync | OAuth 2.0 | Planned |

---

## 5. Version Constraints

### Why These Versions

| Decision | Reason |
|----------|--------|
| React 19 | Latest stable, concurrent features |
| Vite 7 | Fast HMR, native ESM |
| Tailwind v4 | New @theme syntax, CSS-first config |
| FastAPI >=0.128 | Async improvements, Pydantic v2 support |
| SQLAlchemy >=2.0 | Async-native, improved typing |
| PostgreSQL 16 | JSON improvements, performance |
| Python >=3.12 | Performance improvements, better typing |

### Upgrade Policy

1. **Patch versions** (x.x.PATCH): Auto-update allowed via `^` in package.json
2. **Minor versions** (x.MINOR.x): Review changelog before updating
3. **Major versions** (MAJOR.x.x): Requires migration plan and testing

### Locked Files

- `frontend/package-lock.json` - Exact frontend dependency tree
- `backend/uv.lock` - Exact backend dependency tree

**Always commit lock files. Never manually edit them.**

---

## 6. API Contracts

### Base URL

```
Development: http://localhost:8000
Production:  https://api.mealy.dev   # Fly.io behind Cloudflare; host + origin-header gate rejects anything that skipped Cloudflare (421)
```

### Content Types

- Request: `application/json` (except file uploads: `multipart/form-data`)
- Response: `application/json`

### Authentication

**Current (since M3–M5, May 2026):** one shared household login. 15-minute HS256 JWT access
token in `Authorization: Bearer`, 30-day `__Host-refresh` cookie with 60-second rotation grace,
every non-`/auth/*` route on the `protected` router. Private media (`GET /uploads/{key}`) is
cookie-authenticated because `<img>` cannot send a Bearer header. Details:
[BACKEND_STRUCTURE.md → Auth](./BACKEND_STRUCTURE.md).

### Rate Limiting

**Current:** Cloudflare WAF rule *Mealy api-auth burst limit* — `/auth/*` capped at
**5 requests / 10 s / IP** (block 10 s), the free-tier ceiling. Verified 2026-05-01; intent
recorded in [`infra/cloudflare-state.md`](../../infra/cloudflare-state.md). No app-layer rate
limiting (a P2 in [TODOS.md](./TODOS.md)). The rule only sees traffic that passes through
Cloudflare; the production host gate's origin-header check is what stops callers going around
it ([BACKEND_STRUCTURE.md → Production host gate](./BACKEND_STRUCTURE.md)).

---

## 7. Browser Support

### Target Browsers

| Browser | Minimum Version |
|---------|-----------------|
| Chrome | 90+ |
| Firefox | 90+ |
| Safari | 14+ |
| Edge | 90+ |
| iOS Safari | 14+ |
| Chrome Android | 90+ |

### Not Supported

- Internet Explorer (any version)
- Opera Mini
- UC Browser

### CSS Features Used

- CSS Grid
- CSS Custom Properties (variables)
- Flexbox
- @media queries
- :where() pseudo-class (Tailwind dark mode)

---

## 8. File Structure Reference

```
todo-app/
├── frontend/
│   ├── package.json          # Frontend dependencies
│   ├── package-lock.json     # Locked versions
│   ├── vite.config.js        # Vite configuration
│   ├── src/
│   │   ├── index.css         # Global styles + Tailwind
│   │   ├── main.jsx          # React entry point (binds the data router)
│   │   ├── RootLayout.jsx    # Root layout + providers
│   │   ├── lib/              # api.js, apiBase.js, queryClient.js, router.jsx, auth/
│   │   ├── pages/            # Route-level page shells
│   │   ├── components/       # Feature directories + shared/
│   │   ├── hooks/            # Reusable hooks
│   │   ├── constants/        # familyColors, foodEmojis, units, …
│   │   └── contexts/         # React context providers
│   └── tests/                # Frontend tests
│
├── backend/
│   ├── pyproject.toml        # Python project config
│   ├── uv.lock               # Locked versions
│   ├── Dockerfile            # Container definition
│   ├── docker-compose.yml    # Service orchestration
│   ├── alembic.ini           # Migration config
│   ├── alembic/              # Migration scripts
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── database.py       # DB connection
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── crud_*.py         # CRUD operations
│   │   └── routes/           # API endpoints
│   └── tests/                # Backend tests
│
├── AGENTS.md                 # Project rules for every AI harness (CLAUDE.md imports it)
├── infra/                    # RUNBOOK.md, incident-diagnostics.md, backup-restore-drill.md,
│                             # release-smoke.py, cloudflare-drift.py, fly-scale.json, paused.json, tests/,
│                             # cloudflare-state.md, r2-cutover-runbook.md (host-side; see §4)
└── .agents/docs/             # Documentation (framework docs set)
    ├── PRD.md
    ├── APP_FLOW.md
    ├── TECH_STACK.md (this file)
    ├── FRONTEND_GUIDELINES.md
    ├── FRONTEND_STRUCTURE.md
    ├── BACKEND_STRUCTURE.md
    ├── IMPLEMENTATION_PLAN.md
    ├── LESSONS.md
    ├── TODOS.md
    ├── development-commands.md
    └── REVIEW_CHECKLIST.md
```
