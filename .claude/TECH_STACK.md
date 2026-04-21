# Tech Stack Documentation

> Every package, dependency, API, and tool locked to exact versions.

---

## Table of Contents

1. [Frontend Dependencies](#1-frontend-dependencies)
2. [Backend Dependencies](#2-backend-dependencies)
3. [Development Tools](#3-development-tools)
4. [Infrastructure](#4-infrastructure)
5. [Version Constraints](#5-version-constraints)

---

## 1. Frontend Dependencies

### Core Framework

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^19.2.0 | UI framework |
| `react-dom` | ^19.2.0 | React DOM renderer |
| `react-router-dom` | ^7.12.0 | Client-side routing |
| `vite` | ^7.2.4 | Build tool and dev server |

### UI Libraries

| Package | Version | Purpose |
|---------|---------|---------|
| `tailwindcss` | ^4.1.18 | Utility-first CSS framework |
| `@tailwindcss/vite` | ^4.1.18 | Vite plugin for Tailwind |
| `@headlessui/react` | ^2.2.9 | Unstyled accessible UI components (modals, dialogs) |
| `@heroicons/react` | ^2.2.0 | SVG icon library |

### Data & State

| Package | Version | Purpose |
|---------|---------|---------|
| `axios` | ^1.13.2 | HTTP client for API calls |
| `@tanstack/react-query` | ^5.90.19 | Server state management (available, not fully integrated) |

### Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| `react-swipeable` | ^7.0.2 | Touch swipe gestures |

### Dev Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `@vitejs/plugin-react` | ^5.1.1 | React plugin for Vite |
| `@types/react` | ^19.2.5 | TypeScript types for React |
| `@types/react-dom` | ^19.2.3 | TypeScript types for React DOM |
| `eslint` | ^9.39.1 | JavaScript linter |
| `@eslint/js` | ^9.39.1 | ESLint JavaScript rules |
| `eslint-plugin-react-hooks` | ^7.0.1 | React Hooks linting rules |
| `eslint-plugin-react-refresh` | ^0.4.24 | React Refresh linting |
| `globals` | ^16.5.0 | Global variables for ESLint |
| `prettier` | ^3.8.1 | Code formatter |

### Testing

| Package | Version | Purpose |
|---------|---------|---------|
| `vitest` | ^2.0.0 | Test runner |
| `@vitest/coverage-v8` | ^2.0.0 | Code coverage |
| `@testing-library/react` | ^16.0.0 | React testing utilities |
| `@testing-library/jest-dom` | ^6.4.0 | Jest DOM matchers |
| `@testing-library/user-event` | ^14.5.0 | User event simulation |
| `jsdom` | ^24.0.0 | DOM environment for tests |
| `msw` | ^2.3.0 | API mocking (Mock Service Worker) |

---

## 2. Backend Dependencies

### Core Framework

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | >=0.128.0 | Async web framework |
| `uvicorn` | >=0.40.0 | ASGI server |
| `pydantic` | >=2.12.5 | Data validation and serialization |

### Database

| Package | Version | Purpose |
|---------|---------|---------|
| `sqlalchemy` | >=2.0.45 | ORM and database toolkit |
| `asyncpg` | >=0.31.0 | Async PostgreSQL driver |
| `psycopg[binary]` | >=3.2.0 | PostgreSQL adapter |
| `greenlet` | >=3.3.0 | Async support for SQLAlchemy |
| `alembic` | >=1.18.0 | Database migrations |

### Background Jobs & Messaging

| Package | Version | Purpose |
|---------|---------|---------|
| `celery[redis]` | >=5.4 | Distributed task queue with Redis broker |
| `redis` | >=5.0 | Redis client for Celery broker/backend |

### Calendar Integration

| Package | Version | Purpose |
|---------|---------|---------|
| `caldav` | >=1.4 | CalDAV protocol client (iCloud calendar access) |
| `icalendar` | >=6.1 | ICS/iCalendar parsing and generation |
| `cryptography` | >=44.0 | Fernet encryption for stored app-specific passwords |

### AI & Web Extraction

| Package | Version | Purpose |
|---------|---------|---------|
| `anthropic` | >=0.40 | Anthropic Python SDK for Claude API (AI recipe extraction + suggest-icon) |
| `recipe-scrapers` | >=15.0 | Recipe structured data extraction from 631+ cooking sites |
| `beautifulsoup4` | >=4.12 | HTML cleaning before LLM extraction |
| `httpx` | >=0.27 | HTTP client for fetching web pages (prod dep; also used by the test suite) |

Related env vars: `ANTHROPIC_API_KEY` (required at runtime for `/items/import-from-url` worker + `/items/suggest-icon`), `AI_MODEL_NAME` (default `claude-haiku-4-5-20251001`). Both are read by `app/services/ai_client.py`.

Build note: the `Dockerfile` builder stage installs `libxml2-dev`, `libxslt-dev`, and `gcc` so `lxml` (transitive dep of `recipe-scrapers`) compiles on `python:3.12-slim`.

### Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| `python-multipart` | >=0.0.22 | File upload handling |
| `tzdata` | >=2024.1 | IANA timezone database (required for `zoneinfo` on slim Docker images) |

### Development

| Package | Version | Purpose |
|---------|---------|---------|
| `ipykernel` | >=7.1.0 | Jupyter notebook support |

### Testing

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | >=8.0 | Test framework |
| `pytest-asyncio` | >=0.23 | Async test support |
| `pytest-cov` | >=4.1 | Code coverage |
| `httpx` | >=0.27 | Async HTTP client for tests |
| `factory-boy` | >=3.3 | Test data factories |
| `testcontainers[postgres]` | >=4.0 | Containerized test databases |

---

## 3. Development Tools

### Package Managers

| Tool | Version | Purpose |
|------|---------|---------|
| `uv` | Latest | Python package manager (NOT pip) |
| `npm` | >=18.0 | JavaScript package manager |
| Node.js | >=18.0 | JavaScript runtime |
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
  build: ./frontend
  ports: "5173:5173"
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
```

**Frontend (.env.local)**
```
VITE_API_BASE_URL=http://localhost:8000
```

### Ports

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5433 (external) / 5432 (internal) | Database |
| Redis | 6379 | Celery broker and result backend |
| FastAPI | 8000 | Backend API |
| Vite Dev | 5173 | Frontend development |

### CI/CD Pipeline

| Tool | Purpose |
|------|---------|
| GitHub Actions | CI/CD automation |
| `.github/workflows/test.yml` | Run tests on push/PR |
| `.github/workflows/deploy.yml` | Deploy to production (planned) |

**CI Pipeline (Current):**
```yaml
on: [push, pull_request]
jobs:
  test:
    - Checkout code
    - Setup Python/Node
    - Install dependencies
    - Run backend tests (pytest)
    - Run frontend tests (vitest)
    - Lint check
```

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

### Production Deployment (Planned)

| Component | Service | Purpose |
|-----------|---------|---------|
| Frontend | Vercel / Fly.io | Static hosting with CDN |
| Backend | Fly.io / Railway | Container hosting |
| Database | Managed PostgreSQL | Fly.io Postgres / Railway / Supabase |
| File Storage | S3 / Cloudflare R2 | User uploads (photos, icons) |
| SSL | Auto-provisioned | HTTPS for all traffic |

**Deployment Options:**

1. **Cloud Hosted (Primary)** - Users visit public URL, no setup required
2. **One-Click Deploy** - Heroku/Railway deploy buttons for self-hosting
3. **Docker Compose** - For advanced users running locally

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
Production: TBD
```

### Content Types

- Request: `application/json` (except file uploads: `multipart/form-data`)
- Response: `application/json`

### Authentication

**Current:** None (single-household mode)
**Planned:** JWT Bearer tokens in Authorization header

### Rate Limiting

**Current:** None
**Planned:** TBD for production

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
│   │   ├── main.jsx          # React entry point
│   │   ├── App.jsx           # Root component + routes
│   │   ├── pages/            # Route-level components
│   │   ├── components/       # Reusable UI components
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
├── CLAUDE.md                 # AI assistant instructions
└── .claude/                  # Documentation
    ├── PRD.md
    ├── APP_FLOW.md
    ├── TECH_STACK.md (this file)
    ├── FRONTEND_GUIDELINES.md
    ├── FRONTEND_STRUCTURE.md
    ├── BACKEND_STRUCTURE.md
    └── IMPLEMENTATION_PLAN.md
```
