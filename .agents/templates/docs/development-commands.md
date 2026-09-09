# Development Commands

> **This is the canonical source of truth for development, build, test, and run commands.**
> Referenced by `AGENTS.md` and by every skill that runs the stack. Every command here is
> copy-pasteable. Env var VALUES never appear in this file; names and generation commands do.

## Critical Rule

**{{COMMAND_POLICY}}**

<!-- guidance: state the policy in one bold sentence, e.g. "App commands run through
{{CONTAINER_TOOL}}; never run the package manager, build, or test commands directly on the
host." If the project has no policy, say "No container policy; commands run on the host." -->

Exceptions (host-side by design):
- Framework helpers under `.agents/bin/` (`workflow-state`, `obsidian-workflow`, `doc-guard`, `review-log`, `ctx`, and the rest)
- Tests for those helpers under `.agents/tests/`
- Git, and the `gh` CLI

## Full Stack

```bash
{{DEV_COMMAND}}                      # start every service
<!-- guidance: add rebuild, stop, and logs commands for {{CONTAINER_TOOL}}. -->
```

Services:

| Service | Port | Purpose |
|---|---|---|
| {{DB}} | {{DB_PORT}} | Database |
| API ({{BACKEND_FRAMEWORK}}) | {{APP_PORT}} | Backend |
| Frontend dev server ({{FRONTEND_FRAMEWORK}}) | {{FRONTEND_PORT}} | Frontend |
<!-- conditional: add rows for job workers, schedulers, caches, and test-only services. -->

**Required env vars** (in `{{BACKEND_DIR}}/.env`; template in `{{BACKEND_DIR}}/.env.example`):

<!-- guidance: one row per variable: name, purpose, required or optional, how to generate it.
Never a value. Say what fails when a required one is missing. -->

| Variable | Purpose | Required | Generate with |
|---|---|---|---|
| `DATABASE_URL` | Database connection | yes | see `.env.example` |
| `TEST_DATABASE_URL` | Isolated test database | yes (tests) | see `.env.example` |
| `SECRET_KEY` | Signing secret | yes | `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |

Without the required variables the API refuses to start in production and logs a bootstrap warning in development.

**Frontend env** (`{{FRONTEND_DIR}}/.env.local`):

| Variable | Purpose | Required |
|---|---|---|
| `<PREFIX>_API_BASE_URL` | API origin | yes for production builds |

<!-- guidance: describe the container build targets (dev with reload and mounts; prod non-root,
no test deps) and the compose services in two short lists. -->

## Frontend

```bash
<!-- guidance: install, dev server (if separate from Full Stack), build, lint, type check, one test file. -->
```

## Database Migrations

```bash
<!-- guidance: {{MIGRATION_TOOL}} create (autogenerate), apply, roll back one, show heads; seed and reset if they exist. -->
```

<!-- guidance: state whether migrations run automatically on container start or as an explicit release step. -->

## Testing

### Backend ({{TEST_RUNNER_BACKEND}})

```bash
{{TEST_COMMAND_BACKEND}}                   # all tests
<!-- guidance: unit only, integration only, one file, one test by name. -->
```

### Frontend ({{TEST_RUNNER_FRONTEND}})

```bash
{{TEST_COMMAND_FRONTEND}}                  # single run (CI)
<!-- guidance: watch mode, coverage, one file. -->
```

### End-to-End

<!-- conditional: keep when an e2e suite exists; say what it runs against (production build, not the dev server). -->

```bash
```

### Visual Regression

<!-- conditional: keep when a visual suite exists; include build, up, run, and teardown, plus a link to its README for the flake protocol. -->

```bash
```

## Lint & Format

```bash
<!-- guidance: backend lint/format/type-check; frontend lint/format. Same commands CI runs. -->
```

## Host-side Tooling Tests

```bash
python3 -m pytest .agents/tests -q
```

These cover the framework helpers only and run on the host, never through a container.

## CI

<!-- guidance: {{CI_PROVIDER}}: what triggers CI, the jobs by name, and a statement that each
job runs the exact command listed above. The job table lives in TECH_STACK.md → CI/CD
Pipeline; do not duplicate it here. -->

CI runs on push and pull request to `{{DEFAULT_BRANCH}}`. The `doc-guard` job runs
`python3 .agents/bin/doc-guard --range "origin/<base>..HEAD"` on every pull request.
