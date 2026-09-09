# Automated Testing Plan

## Overview

This plan establishes a comprehensive testing strategy for the todo-app, covering both backend (FastAPI/Python) and frontend (React/Vite). The approach uses a **layered testing pyramid** to balance speed, coverage, and confidence.

### Goals
- **Prevent regressions** — Catch bugs before they reach production
- **Document behavior** — Tests as living documentation
- **Enable refactoring** — Confidence to restructure code
- **CI/CD enforcement** — Block merges when tests fail

### Coverage Target
Focus on **critical paths first**: core CRUD operations, key user flows, and complex business logic.

---

## Testing Pyramid

```
        /\
       /  \      E2E Tests (Few)
      /    \     - Full user journeys
     /------\    - Slow, high confidence
    /        \
   /   Integ  \  Integration Tests (Some)
  /    Tests   \ - Real DB, real API
 /--------------\- Medium speed
/                \
/   Unit Tests    \ Unit Tests (Many)
/   (Mocked)       \ - Fast, isolated
/--------------------\- Test logic only
```

| Layer | Speed | What it tests | When to run |
|-------|-------|---------------|-------------|
| Unit | ~1ms/test | Pure logic, isolated components | Every save (watch mode) |
| Integration | ~100ms/test | DB queries, API contracts | Pre-commit, CI |
| E2E | ~5s/test | Complete user flows | CI only |

---

## Part 1: Backend Testing

### 1.1 Frameworks & Tools

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner and framework |
| **pytest-asyncio** | Async test support for FastAPI |
| **httpx** | Async HTTP client for API testing |
| **pytest-cov** | Coverage reporting |
| **factory-boy** | Test data factories |
| **sqlalchemy** (in-memory SQLite) | Unit test DB mock |
| **testcontainers** | Real PostgreSQL for integration tests |

### 1.2 Directory Structure

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── factories.py             # Test data factories
│   │
│   ├── unit/                    # Mocked/isolated tests
│   │   ├── __init__.py
│   │   ├── test_crud_tasks.py
│   │   ├── test_crud_family_members.py
│   │   ├── test_crud_responsibilities.py
│   │   ├── test_crud_lists.py
│   │   └── test_schemas.py      # Pydantic validation
│   │
│   └── integration/             # Real DB tests
│       ├── __init__.py
│       ├── conftest.py          # DB fixtures
│       ├── test_tasks_api.py
│       ├── test_family_members_api.py
│       ├── test_responsibilities_api.py
│       ├── test_lists_api.py
│       └── test_uploads_api.py
│
├── pyproject.toml               # Add test dependencies
└── pytest.ini                   # Pytest configuration
```

### 1.3 Unit Tests (Mocked)

**Purpose:** Test business logic in isolation without database.

**What to test:**
- CRUD function logic with mocked AsyncSession
- Pydantic schema validation (valid/invalid inputs)
- Edge cases and error conditions

**Example pattern:**
```python
# tests/unit/test_crud_family_members.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.crud_family_members import delete_family_member

@pytest.mark.asyncio
async def test_delete_family_member_blocks_system_member():
    """Cannot delete system members (Everyone)."""
    mock_db = AsyncMock()
    mock_member = MagicMock(is_system=True, name="Everyone")
    mock_db.get.return_value = mock_member

    result, error = await delete_family_member(mock_db, member_id=1)

    assert result is None
    assert error == "Cannot delete system family member"
    mock_db.delete.assert_not_called()

@pytest.mark.asyncio
async def test_delete_family_member_blocks_if_has_tasks():
    """Cannot delete members with assigned tasks."""
    # ... test implementation
```

**Priority areas for unit tests:**
1. `crud_family_members.py` — Deletion validation logic (system check, task check)
2. `crud_responsibilities.py` — Completion toggle logic (create vs delete)
3. `schemas.py` — Validation rules for all Pydantic models
4. `uploads.py` — File validation (extension, size limits)

### 1.4 Integration Tests (Real Database)

**Purpose:** Test actual database operations and API endpoints.

**What to test:**
- Full API request/response cycles
- Database constraints and relationships
- Query correctness (joins, filters, ordering)
- HTTP status codes and error responses

**Example pattern:**
```python
# tests/integration/test_tasks_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_task(test_db, test_list, test_member):
    """POST /tasks creates a task and returns 201."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/tasks", json={
            "title": "Buy groceries",
            "list_id": test_list.id,
            "assigned_to": test_member.id
        })

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert data["completed"] is False

@pytest.mark.asyncio
async def test_create_task_invalid_list_returns_404(test_db):
    """POST /tasks with invalid list_id returns 404."""
    # ... test implementation
```

**Fixtures needed (`tests/integration/conftest.py`):**
```python
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models import Base

@pytest.fixture(scope="session")
def postgres_container():
    """Spin up real PostgreSQL for integration tests."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest_asyncio.fixture
async def test_db(postgres_container):
    """Create tables and provide session."""
    engine = create_async_engine(postgres_container.get_connection_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # ... yield session, cleanup
```

**Priority areas for integration tests:**
1. All CRUD endpoints — Happy path + error cases
2. Relationship loading — Tasks with family_member and list populated
3. Cascade behavior — Deleting responsibility removes completions
4. Unique constraints — ResponsibilityCompletion date uniqueness
5. File uploads — Actual file writing and retrieval

### 1.5 Backend Test Commands

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "httpx>=0.27",
    "factory-boy>=3.3",
    "testcontainers[postgres]>=4.0",
]
```

Commands:
```bash
# Run all tests
uv run pytest

# Run only unit tests (fast)
uv run pytest tests/unit -v

# Run only integration tests
uv run pytest tests/integration -v

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Watch mode (requires pytest-watch)
uv run ptw tests/unit
```

---

## Part 2: Frontend Testing

### 2.1 Frameworks & Tools

| Tool | Purpose |
|------|---------|
| **Vitest** | Test runner (Vite-native, fast) |
| **React Testing Library** | Component testing |
| **jsdom** | Browser environment simulation |
| **MSW (Mock Service Worker)** | API mocking |
| **@testing-library/user-event** | Realistic user interactions |

### 2.2 Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── TaskItem.jsx
│   │   ├── TaskItem.test.jsx        # Co-located tests
│   │   └── ...
│   ├── pages/
│   │   ├── ListsPage.jsx
│   │   ├── ListsPage.test.jsx
│   │   └── ...
│   └── contexts/
│       ├── DarkModeContext.jsx
│       └── DarkModeContext.test.jsx
│
├── tests/
│   ├── setup.js                     # Test setup (jsdom, MSW)
│   ├── mocks/
│   │   ├── handlers.js              # MSW request handlers
│   │   └── server.js                # MSW server setup
│   └── integration/                 # Multi-component tests
│       └── task-flow.test.jsx
│
├── vitest.config.js
└── package.json                     # Add test dependencies
```

### 2.3 Unit Tests (Mocked API)

**Purpose:** Test components in isolation with mocked API responses.

**What to test:**
- Component rendering (correct elements appear)
- User interactions (clicks, form inputs)
- State changes (loading, error, success states)
- Props and conditional rendering

**Example pattern:**
```javascript
// src/components/TaskItem.test.jsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect } from 'vitest'
import TaskItem from './TaskItem'

describe('TaskItem', () => {
  const mockTask = {
    id: 1,
    title: 'Buy groceries',
    description: 'Milk, eggs, bread',
    completed: false,
    important: true,
    due_date: '2024-12-01',
    family_member: { id: 1, name: 'Alice', photo_url: null }
  }

  it('renders task title and description', () => {
    render(<TaskItem task={mockTask} onToggle={() => {}} onEdit={() => {}} onDelete={() => {}} />)

    expect(screen.getByText('Buy groceries')).toBeInTheDocument()
    expect(screen.getByText('Milk, eggs, bread')).toBeInTheDocument()
  })

  it('shows important star when task is important', () => {
    render(<TaskItem task={mockTask} onToggle={() => {}} onEdit={() => {}} onDelete={() => {}} />)

    expect(screen.getByTestId('important-star')).toBeInTheDocument()
  })

  it('calls onToggle when checkbox clicked', async () => {
    const onToggle = vi.fn()
    render(<TaskItem task={mockTask} onToggle={onToggle} onEdit={() => {}} onDelete={() => {}} />)

    await userEvent.click(screen.getByRole('checkbox'))

    expect(onToggle).toHaveBeenCalledWith(1)
  })

  it('shows overdue styling for past due dates', () => {
    const overdueTask = { ...mockTask, due_date: '2020-01-01' }
    render(<TaskItem task={overdueTask} onToggle={() => {}} onEdit={() => {}} onDelete={() => {}} />)

    expect(screen.getByText(/Jan 1, 2020/)).toHaveClass('text-red-500')
  })
})
```

**Priority areas for unit tests:**
1. `TaskItem.jsx` — Rendering, completion toggle, overdue styling
2. `ResponsibilityCard.jsx` — Completion state, edit/delete actions
3. `TodoForm.jsx` — Form validation, submission
4. `ResponsibilityForm.jsx` — Complex form with frequency selector
5. `PhotoUpload.jsx` — File validation, drag-drop, preview
6. `DarkModeContext.jsx` — Toggle behavior, localStorage persistence

### 2.4 Integration Tests (MSW)

**Purpose:** Test page-level components with realistic API interactions.

**MSW Setup:**
```javascript
// tests/mocks/handlers.js
import { http, HttpResponse } from 'msw'

export const handlers = [
  // Lists
  http.get('http://localhost:8000/lists', () => {
    return HttpResponse.json([
      { id: 1, name: 'Personal', color: '#EF4444', icon: '📋' },
      { id: 2, name: 'Work', color: '#3B82F6', icon: '💼' }
    ])
  }),

  // Tasks
  http.get('http://localhost:8000/tasks', ({ request }) => {
    const url = new URL(request.url)
    const listId = url.searchParams.get('list_id')
    return HttpResponse.json([
      { id: 1, title: 'Task 1', list_id: parseInt(listId), completed: false }
    ])
  }),

  http.post('http://localhost:8000/tasks', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ id: 99, ...body, completed: false }, { status: 201 })
  }),

  // Family members
  http.get('http://localhost:8000/family-members', () => {
    return HttpResponse.json([
      { id: 1, name: 'Everyone', is_system: true },
      { id: 2, name: 'Alice', is_system: false }
    ])
  }),
]
```

```javascript
// tests/mocks/server.js
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

```javascript
// tests/setup.js
import '@testing-library/jest-dom/vitest'
import { beforeAll, afterEach, afterAll } from 'vitest'
import { server } from './mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

**Example integration test:**
```javascript
// tests/integration/task-flow.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { DarkModeProvider } from '../../src/contexts/DarkModeContext'
import ListsPage from '../../src/pages/ListsPage'

const renderWithProviders = (component) => {
  return render(
    <BrowserRouter>
      <DarkModeProvider>
        {component}
      </DarkModeProvider>
    </BrowserRouter>
  )
}

describe('ListsPage', () => {
  it('loads and displays lists from API', async () => {
    renderWithProviders(<ListsPage />)

    await waitFor(() => {
      expect(screen.getByText('Personal')).toBeInTheDocument()
      expect(screen.getByText('Work')).toBeInTheDocument()
    })
  })

  it('loads tasks when a list is selected', async () => {
    renderWithProviders(<ListsPage />)

    await waitFor(() => screen.getByText('Personal'))
    await userEvent.click(screen.getByText('Personal'))

    await waitFor(() => {
      expect(screen.getByText('Task 1')).toBeInTheDocument()
    })
  })

  it('creates a new task via the form', async () => {
    renderWithProviders(<ListsPage />)

    // Open form, fill it, submit
    await userEvent.click(screen.getByTestId('add-task-button'))
    await userEvent.type(screen.getByLabelText('Title'), 'New task')
    await userEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(screen.getByText('New task')).toBeInTheDocument()
    })
  })
})
```

**Priority areas for integration tests:**
1. `ListsPage.jsx` — Full task management flow
2. `ResponsibilitiesPage.jsx` — Tab switching, completion tracking
3. `ScheduleView.jsx` — Date navigation, filtering, member selection
4. `FamilyMemberManager.jsx` — Member CRUD operations

### 2.5 Frontend Test Commands

Add to `package.json`:
```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:ui": "vitest --ui"
  },
  "devDependencies": {
    "vitest": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/user-event": "^14.5.0",
    "@vitest/coverage-v8": "^2.0.0",
    "@vitest/ui": "^2.0.0",
    "jsdom": "^24.0.0",
    "msw": "^2.3.0"
  }
}
```

Vitest config (`vitest.config.js`):
```javascript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    globals: true,
    css: true,
  },
})
```

Commands:
```bash
# Run tests in watch mode
npm test

# Run once (for CI)
npm run test:run

# With coverage report
npm run test:coverage

# Visual UI
npm run test:ui
```

---

## Part 3: E2E Testing (Optional/Future)

E2E tests run the full stack and simulate real user behavior in a browser.

### 3.1 Recommended Tool: Playwright

```bash
npm init playwright@latest
```

### 3.2 Example E2E Test

```javascript
// e2e/task-management.spec.js
import { test, expect } from '@playwright/test'

test('user can create and complete a task', async ({ page }) => {
  await page.goto('http://localhost:5173')

  // Navigate to tasks
  await page.click('text=Tasks')

  // Create a task
  await page.click('[data-testid="add-task-button"]')
  await page.fill('[name="title"]', 'E2E Test Task')
  await page.click('button:has-text("Save")')

  // Verify task appears
  await expect(page.locator('text=E2E Test Task')).toBeVisible()

  // Complete the task
  await page.click('[data-testid="task-checkbox"]')
  await expect(page.locator('[data-testid="task-checkbox"]')).toBeChecked()
})
```

### 3.3 When to Add E2E Tests

Add E2E tests after unit and integration tests are stable. Focus on:
- Critical user journeys (login → create task → complete task)
- Flows that span multiple pages
- Accessibility testing

---

## Part 4: GitHub Actions CI

### 4.1 Workflow File

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: todo_app_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        working-directory: backend
        run: uv sync --all-extras

      - name: Run unit tests
        working-directory: backend
        run: uv run pytest tests/unit -v

      - name: Run integration tests
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/todo_app_test
        run: |
          uv run alembic upgrade head
          uv run pytest tests/integration -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        if: always()
        with:
          files: backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Run tests
        working-directory: frontend
        run: npm run test:run

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        if: always()
        with:
          files: frontend/coverage/lcov.info
```

### 4.2 Branch Protection (Optional)

After CI is working, enable branch protection on `main`:
1. Go to repo Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Check "Require status checks to pass before merging"
4. Select `backend-tests` and `frontend-tests`

---

## Part 5: Implementation Phases

### Phase 1: Infrastructure Setup
- [ ] Add test dependencies to backend `pyproject.toml`
- [ ] Add test dependencies to frontend `package.json`
- [ ] Create directory structures
- [ ] Configure pytest (`pytest.ini` or `pyproject.toml`)
- [ ] Configure Vitest (`vitest.config.js`)
- [ ] Set up MSW for frontend

### Phase 2: Backend Unit Tests
- [ ] Create `conftest.py` with shared fixtures
- [ ] Create `factories.py` for test data
- [ ] Write tests for `crud_family_members.py` (deletion logic)
- [ ] Write tests for `crud_responsibilities.py` (toggle logic)
- [ ] Write tests for `schemas.py` (validation)
- [ ] Write tests for `uploads.py` (file validation)

### Phase 3: Backend Integration Tests
- [ ] Set up testcontainers PostgreSQL fixture
- [ ] Write tests for `/tasks` endpoints
- [ ] Write tests for `/family-members` endpoints
- [ ] Write tests for `/responsibilities` endpoints
- [ ] Write tests for `/lists` endpoints
- [ ] Write tests for `/upload` endpoints

### Phase 4: Frontend Unit Tests
- [ ] Set up test utilities and render helpers
- [ ] Write tests for `TaskItem.jsx`
- [ ] Write tests for `ResponsibilityCard.jsx`
- [ ] Write tests for `TodoForm.jsx`
- [ ] Write tests for `ResponsibilityForm.jsx`
- [ ] Write tests for `PhotoUpload.jsx`
- [ ] Write tests for `DarkModeContext.jsx`

### Phase 5: Frontend Integration Tests
- [ ] Set up MSW handlers for all endpoints
- [ ] Write tests for `ListsPage.jsx`
- [ ] Write tests for `ResponsibilitiesPage.jsx`
- [ ] Write tests for `ScheduleView.jsx`

### Phase 6: CI/CD
- [ ] Create `.github/workflows/test.yml`
- [ ] Verify backend tests pass in CI
- [ ] Verify frontend tests pass in CI
- [ ] Enable branch protection (optional)

### Phase 7: E2E Tests (Future)
- [ ] Set up Playwright
- [ ] Write critical path E2E tests
- [ ] Add to CI workflow

---

## Quick Reference

### Run All Tests Locally

```bash
# Backend
cd backend
uv run pytest

# Frontend
cd frontend
npm test

# Both (from root)
cd backend && uv run pytest && cd ../frontend && npm run test:run
```

### Coverage Targets

| Area | Initial Target | Long-term Target |
|------|----------------|------------------|
| Backend Unit | 80% | 90% |
| Backend Integration | Key endpoints | All endpoints |
| Frontend Unit | 60% | 80% |
| Frontend Integration | Critical flows | All pages |

---

## Files to Create

```
.github/
└── workflows/
    └── test.yml

backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── factories.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_crud_tasks.py
│   │   ├── test_crud_family_members.py
│   │   ├── test_crud_responsibilities.py
│   │   ├── test_crud_lists.py
│   │   └── test_schemas.py
│   └── integration/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_tasks_api.py
│       ├── test_family_members_api.py
│       ├── test_responsibilities_api.py
│       ├── test_lists_api.py
│       └── test_uploads_api.py
└── pytest.ini

frontend/
├── tests/
│   ├── setup.js
│   ├── mocks/
│   │   ├── handlers.js
│   │   └── server.js
│   └── integration/
│       └── task-flow.test.jsx
├── src/
│   └── components/
│       ├── TaskItem.test.jsx
│       ├── ResponsibilityCard.test.jsx
│       ├── TodoForm.test.jsx
│       ├── ResponsibilityForm.test.jsx
│       └── PhotoUpload.test.jsx
└── vitest.config.js
```
