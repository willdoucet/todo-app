# Tech Stack

<!-- guidance: This doc owns every dependency with its exact version, the infrastructure, CI,
and external integrations. In new mode record the version and the date it was looked up; in
adopt mode copy the version from the lockfile. Environment variable names and how to generate
them live in development-commands.md; link, do not duplicate. -->

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

<!-- guidance: source of truth is `{{FRONTEND_DIR}}/package.json` and its lockfile. One table per
category; drop a category that is empty with a one-line note. Framework: {{FRONTEND_FRAMEWORK}};
styling: {{STYLING}}; test runner: {{TEST_RUNNER_FRONTEND}}. -->

### Core Framework

| Package | Version | Purpose |
|---|---|---|
| | | |

### UI Libraries

| Package | Version | Purpose |
|---|---|---|
| | | |

### Data & State

| Package | Version | Purpose |
|---|---|---|
| | | |

### Utilities

| Package | Version | Purpose |
|---|---|---|
| | | |

### Dev Dependencies

| Package | Version | Purpose |
|---|---|---|
| | | |

### Testing

| Package | Version | Purpose |
|---|---|---|
| | | |

---

## 2. Backend Dependencies

<!-- guidance: source of truth is the backend manifest in `{{BACKEND_DIR}}/` and its lockfile.
Framework: {{BACKEND_FRAMEWORK}}; ORM: {{ORM}}; migrations: {{MIGRATION_TOOL}}; test runner:
{{TEST_RUNNER_BACKEND}}. -->

### Core Framework

| Package | Version | Purpose |
|---|---|---|
| | | |

### Database

| Package | Version | Purpose |
|---|---|---|
| | | |

### Background Jobs & Messaging

<!-- conditional: keep when the stack has a job runner or queue; otherwise one line: "None in v1." -->

| Package | Version | Purpose |
|---|---|---|
| | | |

### Auth

<!-- conditional: keep when the app authenticates users ({{AUTH_MODEL}}). -->

| Package | Version | Purpose |
|---|---|---|
| | | |

### Integrations

<!-- conditional: third-party API clients (calendar, email, AI, payments). -->

| Package | Version | Purpose |
|---|---|---|
| | | |

### Utilities

| Package | Version | Purpose |
|---|---|---|
| | | |

### Development

| Package | Version | Purpose |
|---|---|---|
| | | |

### Testing

| Package | Version | Purpose |
|---|---|---|
| | | |

---

## 3. Development Tools

### Package Managers

| Tool | Version | Scope |
|---|---|---|
| | | frontend |
| | | backend |

### Containerization

| Tool | Version | Purpose |
|---|---|---|
| {{CONTAINER_TOOL}} | | |

### Database Tooling

| Tool | Version | Purpose |
|---|---|---|
| {{DB}} | | Primary database |
| {{MIGRATION_TOOL}} | | Schema migrations |

---

## 4. Infrastructure

### Services

<!-- guidance: every process the dev stack runs, in the order it starts, with image or build
target and the port it exposes. Mirror development-commands.md → Full Stack. -->

| Service | Image / build | Port (host:container) | Purpose |
|---|---|---|---|
| db | | {{DB_PORT}} | |
| api | | {{APP_PORT}} | |
| frontend | | {{FRONTEND_PORT}} | |

### Environment Variables

Names, purpose, and generation commands live in [development-commands.md → Required env vars](./development-commands.md#full-stack). Values are never written in any doc.

### Ports

| Service | Port | Purpose |
|---|---|---|
| {{DB}} | {{DB_PORT}} | Database |
| API | {{APP_PORT}} | Backend |
| Frontend dev server | {{FRONTEND_PORT}} | Frontend |

### CI/CD Pipeline

<!-- guidance: provider {{CI_PROVIDER}}; one row per job with its trigger and the command it
runs (the same command as development-commands.md). Say which jobs are required checks. -->

| Job | Trigger | Runs | Required check |
|---|---|---|---|
| doc-guard | pull_request | `python3 .agents/bin/doc-guard --range "origin/<base>..HEAD"` | yes |
| backend tests | push, pull_request | `{{TEST_COMMAND_BACKEND}}` | yes |
| frontend tests | push, pull_request | `{{TEST_COMMAND_FRONTEND}}` | yes |

### Production Deployment

<!-- guidance: one row per component with the target and its purpose. Status: planned / live.
Release procedure lives in RUNBOOK.md once it exists. -->

| Component | Target | Purpose | Status |
|---|---|---|---|
| Frontend | | | planned |
| Backend | | | planned |
| Database | | | planned |
| File storage | | | planned |

### External Integrations

<!-- guidance: every third-party service the app talks to at runtime. -->

| Service | Purpose | Auth method | Status |
|---|---|---|---|
| | | | |

---

## 5. Version Constraints

### Why These Versions

| Decision | Reason |
|---|---|
| | |

### Upgrade Policy

1. **Patch** (x.y.PATCH): allowed automatically within the lockfile range
2. **Minor** (x.MINOR.y): read the changelog before updating
3. **Major** (MAJOR.x.y): needs a plan file and a test run; it is feature-tier work

### Locked Files

- `{{FRONTEND_DIR}}/<lockfile>` — exact frontend dependency tree
- `{{BACKEND_DIR}}/<lockfile>` — exact backend dependency tree

**Always commit lock files. Never edit them by hand.**

---

## 6. API Contracts

### Base URL

```
Development: http://localhost:{{APP_PORT}}
Production:  <!-- guidance: the API origin; say whether it is same-origin or split from the frontend. -->
```

### Content Types

- Request: `application/json` (file uploads: `multipart/form-data`)
- Response: `application/json`

### Authentication

**Model:** {{AUTH_MODEL}}
<!-- guidance: header or cookie, token lifetime, refresh behavior. Enforcement pattern is in BACKEND_STRUCTURE.md → API Endpoints → Auth. -->

### Rate Limiting

<!-- guidance: current and planned; where it is enforced (edge, app). -->

---

## 7. Browser Support

### Target Browsers

| Browser | Minimum version |
|---|---|
| Chrome | |
| Firefox | |
| Safari | |
| Edge | |
| iOS Safari | |
| Chrome Android | |

### Not Supported

-

### CSS Features Used

-

---

## 8. File Structure Reference

<!-- guidance: top-level tree only; the detailed trees are in the structure docs. -->

```
{{PROJECT_NAME}}/
├── {{FRONTEND_DIR}}/           # see FRONTEND_STRUCTURE.md
├── {{BACKEND_DIR}}/            # see BACKEND_STRUCTURE.md
├── .agents/
│   ├── docs/                   # this documentation set
│   ├── plans/                  # feature plans, epics, quickfix log, test artifacts
│   ├── state/                  # registry, review log
│   ├── skills/                 # workflow skills
│   └── bin/                    # host-side helpers
├── {{VAULT_PATH}}/             # idea vault (ignored by git)
├── AGENTS.md                   # project rules for every harness
└── CLAUDE.md                   # imports AGENTS.md
```

The documentation set, with what each doc owns:

| Doc | Owns |
|---|---|
| [PRD.md](./PRD.md) | Scope, personas, acceptance criteria, business rules, roadmap versions |
| [APP_FLOW.md](./APP_FLOW.md) | Screens, routes, navigation, user flows, error copy |
| TECH_STACK.md (this file) | Dependencies, infrastructure, CI, integrations |
| [FRONTEND_GUIDELINES.md](./FRONTEND_GUIDELINES.md) | Design tokens, typography, spacing, breakpoints, component patterns, motion, accessibility |
| [FRONTEND_STRUCTURE.md](./FRONTEND_STRUCTURE.md) | Frontend layout, per-feature file inventory, key patterns |
| [BACKEND_STRUCTURE.md](./BACKEND_STRUCTURE.md) | Schema, endpoints, code organization, validation, error handling, storage |
| [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) | Roadmap phases with status and plan links |
| [LESSONS.md](./LESSONS.md) | Workflow rules, gotchas, corrections, bugs, decisions |
| [TODOS.md](./TODOS.md) | Deferred engineering items |
| [development-commands.md](./development-commands.md) | Run, build, test, migrate, lint; env var names |
| [REVIEW_CHECKLIST.md](./REVIEW_CHECKLIST.md) | Stack-specific review checks |
| [RUNBOOK.md](./RUNBOOK.md) | Release, rollback, rotation, backup drills (created with the first release phase) |
