# Development Commands

> **This is the canonical source of truth for development, build, test, and run commands.**
>
> Referenced by [AGENTS.md](../../AGENTS.md) (for Grok Build) and [CLAUDE.md](../../CLAUDE.md) (for Claude Code compatibility).

## Critical Rule

**IMPORTANT: App commands must run through Docker Compose. Never run `npm`, backend app `uv`, or backend app `pytest` directly on the host.**

Exceptions (host-side by design):
- The framework helpers under `.agents/bin/` (`workflow-state`, `obsidian-workflow`, `doc-guard`, `review-log`, `review-read`, `ctx`, `design-sync-check`, `design-sync-mark`)
- Their tests under `.agents/tests/`
- The operator scripts under `infra/` (`release-smoke.py`, `cloudflare-drift.py`) and their tests under `infra/tests/`. They shell out to `fly`, `curl` and the Cloudflare API with the operator's own credentials, which a container does not have. Standard library only; see Operator Scripts below.

## Full Stack (Docker Compose)

```bash
cd backend
docker-compose up              # Start the default stack (db, redis, api, celery_worker, celery_beat, frontend) — dev targets
docker-compose up --build      # Rebuild and start
docker-compose down            # Stop all services
```

Services:
- PostgreSQL on port 5433
- Redis on port 6379
- FastAPI on port 8000
- Celery worker (background task processing)
- Celery beat (periodic sync scheduler — 10-min iCloud sync interval)
- Vite dev server on port 5173

**Required env vars in `backend/.env`** (post-M5; `backend/.env.example` is the full template and `TECH_STACK.md` "Environment Variables" owns the complete list):
- `JWT_SECRET_KEY` — ≥32 chars, no placeholder substrings (see `backend/app/auth/config.py::PLACEHOLDER_DENY_LIST`). Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `HOUSEHOLD_ACCESS_KEY` — any non-empty string. Gates `/auth/register`.
- `FERNET_KEY` — for iCloud credential encryption. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

Without `JWT_SECRET_KEY` and `HOUSEHOLD_ACCESS_KEY`, every protected route returns 500. The api container's startup logs a clear `[M5 auth bootstrap warning]` line on stderr when these are unset and `APP_ENV != production`. See `backend/.env.example` for the full template.

**Multi-target Dockerfile** (`backend/Dockerfile`):
- `builder` — python:3.12-slim + uv 0.5.24, installs prod deps only, copies app code
- `dev` (extends builder) — adds test extras (`uv sync --extra test`), keeps uv available, runs with `--reload`
- `prod` — slim image from builder, non-root `appuser`, no test deps, bundled stock icons at `/app/stock_icons_src` (served by the M7 media read route). Takes a `GIT_COMMIT` build arg (M8), which `/healthz` reports as `version`; without it the image reports `"unknown"`. The release runbook passes it (`fly deploy --build-arg GIT_COMMIT=<sha>`); local builds need nothing

**Docker Compose** (`backend/docker-compose.yml`):
- `db` — postgres:16, healthcheck, `init-test-db.sh` creates `todo_app_test` DB on first run
- `redis` — redis:7-alpine, healthcheck
- `api` — builds `dev` target, volume-mounts `app/`, `alembic/`, `tests/` for hot-reload, `UV_DEV_MODE` env var toggles `--reload`. Runs `alembic upgrade head` at start. (M7 PR2 removed the old stock-icon copy step: the media read route serves bundled icons straight from `/app/stock_icons_src`, so nothing reads `/app/uploads/stock_icons` any more.)
- `celery_worker` — same image as api, runs `celery -A app.celery_app worker`
- `celery_beat` — same image as api, runs `celery -A app.celery_app beat`
- `frontend` — builds from `../frontend`, Vite dev on 5173, anonymous volume for `node_modules`
- `TEST_DATABASE_URL` points to `todo_app_test` DB for isolated integration tests
- `--profile visual-test` only: `api-test` (dev image, NO `app/` bind-mount, `DATABASE_URL` → `todo_app_test`, migrates + seeds on boot), `frontend-preview` (`preview` target, `vite preview` on 4173, `VITE_API_BASE_URL` baked to `http://api-test:8000`), `frontend-visual` (Playwright + Chromium, pinned base image). See Visual regression below.

## Frontend (via Docker)

```bash
cd backend
docker-compose exec frontend npm run build      # Production build
docker-compose exec frontend npm run lint       # ESLint — gated in CI (frontend-tests job) since M7 PR2
docker-compose exec frontend npm run hygiene    # knip — unused files / exports / dependencies
```

## Database Migrations (via Docker)

```bash
cd backend
docker-compose exec api alembic revision --autogenerate -m "description"  # Create migration
docker-compose exec api alembic upgrade head                               # Apply migrations
```

Migrations run automatically on Docker container startup.

## Testing (via Docker)

```bash
# Backend (pytest with testcontainers)
cd backend
docker-compose exec api uv run pytest                      # All tests
docker-compose exec api uv run pytest tests/unit -v        # Unit tests only
docker-compose exec api uv run pytest tests/integration -v # Integration tests

# Frontend (vitest with MSW)
cd backend
docker-compose exec frontend npm test                      # Watch mode
docker-compose exec frontend npm run test:run              # Single run (CI)
docker-compose exec frontend npm run test:coverage         # With coverage report

# Visual regression (Playwright against `vite preview`)
cd backend
# Include api-test in the build whenever BACKEND code changed — it has no
# bind-mount for app/ (deliberate), so it bakes the backend in at build time.
# Omitting it silently runs the suite against the previously-built backend.
docker-compose --profile visual-test build api-test frontend-preview frontend-visual
# After a backend pytest run, todo_app_test is left stamped at head with no tables, so api-test
# would skip its migration and globalSetup fails with a login 500. Reset it first (LESSONS.md →
# "The visual-test stack and the integration suite share `todo_app_test`"):
#   docker-compose exec -T db psql -U postgres -d todo_app_test -c "DROP TABLE IF EXISTS alembic_version, recipes_archived, food_items_archived"
#   docker-compose --profile visual-test restart api-test    # only when api-test is already running
docker-compose --profile visual-test up -d --wait db redis api-test frontend-preview
docker-compose --profile visual-test run --rm frontend-visual
# Teardown. NOTE: `-v` also removes the shared `db` and `uploads_data` volumes.
# To keep a dev session alive, remove only the visual-only containers instead:
#   docker-compose --profile visual-test rm -sf api-test frontend-preview frontend-visual
docker-compose --profile visual-test down -v
```

The Playwright fixture shims `GET /uploads/*` with fixture bytes
(`tests/visual/fixtures/auth-base.js`). It has to: the browser reaches the API on a docker
hostname, which is not same-site with the preview origin, so the `SameSite=Strict`
`__Host-refresh` cookie would not transmit on an `<img>` subresource load and every image would
401. The real media byte path is covered by backend pytest
(`tests/integration/auth/test_media_read.py`), which sets the cookie directly.

See `frontend/tests/visual/README.md` for the flake-response protocol, debugging workflow, version-bump rules, and the `CI_FERNET_KEY` one-time setup.

## Framework Helper Tests (host-side)

```bash
python3 -m pytest .agents/tests -q
```

These cover the framework helpers under `.agents/bin/` only. They are intentionally separate from the Dockerized backend test suite. `framework doctor .` runs them too.

CI runs automatically on push/PR to `master` via `.github/workflows/test.yml` — five parallel jobs:
`backend-tests` (the two pytest commands above, on the runner with `UPLOAD_DIR` and `STOCK_ICONS_DIR`
pointed at writable/repo paths), `frontend-tests` (`npm run lint`, `npm run test:run`, then
`VITE_GIT_COMMIT=$GITHUB_SHA npm run build` (with the production `VITE_API_BASE_URL`) and a grep that `dist/index.html` carries the SHA),
`infra-tests` (`python3 -m pytest infra/tests -q`), `visual-tests` (the visual-regression block
above via `docker compose`), and `migration-upgrade`:

```bash
# What the migration-upgrade job proves, locally:
cd backend
docker-compose exec api uv run alembic upgrade head          # full chain from base
docker-compose exec api uv run alembic downgrade -1 && docker-compose exec api uv run alembic upgrade head   # newest revision is reversible
```

`.github/workflows/doc-guard.yml` runs `python3 .agents/bin/doc-guard --range origin/master..HEAD` on every pull request. `.github/workflows/ops-check.yml` (M8) runs the operator command `python3 infra/release-smoke.py --only=liveness,recoverability,edge` daily against production (see Operator Scripts below). Job inventory and CI secrets: TECH_STACK.md → CI/CD Pipeline.

## Operator Scripts (host-side)

The release and drift tooling under `infra/` (M8). The procedures that use them, and the exact
production commands, are in [`infra/RUNBOOK.md`](../../infra/RUNBOOK.md); nothing below touches
production.

```bash
python3 -m pytest infra/tests -q            # their tests: every fly/curl/git call and the Cloudflare API are faked
python3 infra/release-smoke.py --self-test  # proves the exit plumbing; expect "exit 1 production: [3] scale-reconciled"
python3 infra/release-smoke.py --help
```

Python ≥ 3.11 on the host (`tomllib`), pytest for the tests; no other dependency. The `infra-tests`
CI job runs the first command.