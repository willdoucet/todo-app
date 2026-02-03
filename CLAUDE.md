# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Family task and responsibility management app with a FastAPI backend and React frontend.

## Development Commands

### Full Stack (Docker Compose)
```bash
cd backend
docker-compose up              # Start all services (db, api, frontend)
docker-compose up --build      # Rebuild and start
docker-compose down            # Stop all services
```

Services:
- PostgreSQL on port 5433
- FastAPI on port 8000
- Vite dev server on port 5173

### Frontend Only
```bash
cd frontend
npm run dev        # Start dev server (port 5173)
npm run build      # Production build
npm run lint       # ESLint
```

### Database Migrations
```bash
cd backend
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                               # Apply migrations
```
Migrations run automatically on Docker container startup.

## Architecture

### Backend (`/backend`)
- **FastAPI** with async SQLAlchemy and PostgreSQL
- **Package manager**: uv (not pip)
- **Structure**:
  - `app/main.py` - FastAPI app, CORS, routers
  - `app/models.py` - SQLAlchemy ORM models
  - `app/schemas.py` - Pydantic validation schemas
  - `app/database.py` - Async DB session
  - `app/crud_*.py` - CRUD operations per entity
  - `app/routes/*.py` - API endpoint handlers

### Frontend (`/frontend`)
- **React 19** with React Router v7, Vite, TailwindCSS v4
- **Structure**:
  - `src/pages/` - Route-level components
  - `src/components/` - Reusable UI components
  - `src/contexts/` - React context providers (DarkModeContext)

### Data Model
- **FamilyMember** - Household members (has is_system flag for "Everyone")
- **List** - Task categories with color/icon
- **Task** - Todo items assigned to members, belong to lists
- **Responsibility** - Recurring tasks with category (MORNING/AFTERNOON/EVENING/CHORE) and frequency (days of week)
- **ResponsibilityCompletion** - Tracks daily completion by member

## Key Patterns

- All backend DB operations use `AsyncSession` with `selectinload()` for relationships
- Frontend uses Axios for API calls, TanStack Query available but not fully integrated
- Custom Tailwind theme colors defined in `frontend/src/index.css` via `@theme` directive
- Dark mode via class toggle on document root (`dark` class)

## Environment Variables

Backend (`.env`):
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/todo_app
UPLOAD_DIR=/app/uploads
```

Frontend (`.env.local`):
```
VITE_API_BASE_URL=http://localhost:8000
```

## API Base URL
- Backend: `http://localhost:8000`
- Endpoints: `/tasks`, `/lists`, `/responsibilities`, `/family-members`, `/upload`

## Workflow Orchestration

### 1.  Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - dont keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3.  Self-Improvement Loop
- After ANY correction from the user: update `.claude/tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4.  Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5.  Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it


## Task Management

1. **Plan First**: Write plan to `./claude/tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Progress**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible.  Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes.  Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary.  Avoid introducing bugs.

