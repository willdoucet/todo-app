# Development Commands

> **This is the canonical source of truth for development, build, test, and run commands.**
>
> Referenced by [AGENTS.md](./AGENTS.md) (for Grok Build) and [CLAUDE.md](./CLAUDE.md) (for Claude Code compatibility).

## Critical Rule

**IMPORTANT: App commands must run through Docker Compose. Never run `npm`, backend app `uv`, or backend app `pytest` directly on the host.**

Exceptions (host-side by design):
- Local workflow tooling under `.claude/`
- The Obsidian helper at `.claude/skills/bin/obsidian-workflow`
- Tests for that helper live under `.claude/tests/`

## Full Stack (Docker Compose)

```bash
cd backend
docker-compose up              # Start all services (db, api, frontend) — uses dev target
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

**Required env vars in `backend/.env`** (post-M5):
- `JWT_SECRET_KEY` — ≥32 chars, no placeholder substrings (see `backend/app/auth/config.py::PLACEHOLDER_DENY_LIST`). Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `HOUSEHOLD_ACCESS_KEY` — any non-empty string. Gates `/auth/register`.
- `FERNET_KEY` — for iCloud credential encryption. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

Without `JWT_SECRET_KEY` and `HOUSEHOLD_ACCESS_KEY`, every protected route returns 500. The api container's startup logs a clear `[M5 auth bootstrap warning]` line on stderr when these are unset and `APP_ENV != production`. See `backend/.env.example` for the full template.

**Multi-target Dockerfile** (`backend/Dockerfile`):
- `builder` — python:3.12-slim + uv 0.5.24, installs prod deps only, copies app code
- `dev` (extends builder) — adds test extras (`uv sync --extra test`), keeps uv available, runs with `--reload`
- `prod` — slim image from builder, non-root `appuser`, no test deps, copies stock icons for uploads

**Docker Compose** (`backend/docker-compose.yml`):
- `db` — postgres:16, healthcheck, `init-test-db.sh` creates `todo_app_test` DB on first run
- `redis` — redis:7-alpine, healthcheck
- `api` — builds `dev` target, volume-mounts `app/`, `alembic/`, `tests/` for hot-reload, `UV_DEV_MODE` env var toggles `--reload`
- `celery_worker` — same image as api, runs `celery -A app.celery_app worker`
- `celery_beat` — same image as api, runs `celery -A app.celery_app beat`
- `frontend` — builds from `../frontend`, Vite dev on 5173, anonymous volume for `node_modules`
- `TEST_DATABASE_URL` points to `todo_app_test` DB for isolated integration tests

## Frontend (via Docker)

```bash
cd backend
docker-compose exec frontend npm run build      # Production build
docker-compose exec frontend npm run lint       # ESLint
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
docker-compose --profile visual-test build frontend-preview frontend-visual
docker-compose --profile visual-test up -d --wait db redis api-test frontend-preview
docker-compose --profile visual-test run --rm frontend-visual
# Teardown:
docker-compose --profile visual-test down -v
```

See `frontend/tests/visual/README.md` for the flake-response protocol, debugging workflow, version-bump rules, and the `CI_FERNET_KEY` one-time setup.

## Local Workflow Helper Tests (host-side)

```bash
cd /path/to/repo
python3 -m pytest .claude/tests/test_obsidian_workflow.py -q
```

These tests cover the local Obsidian workflow helper only. They are intentionally separate from the Dockerized backend test suite.

CI runs automatically on push/PR to `master` via `.github/workflows/test.yml`.