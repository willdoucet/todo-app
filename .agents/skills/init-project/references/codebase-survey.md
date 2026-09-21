# Codebase survey (adopt mode)

Loaded by `init-project` steps A1 and A3. The survey produces facts with file paths. Opinions
and gaps go in a separate "Uncertain" list that becomes interview questions. Delegate to a
subagent when the harness has one; otherwise do it inline in a clearly separated section.

## What to look at

```bash
cd "$REPO_ROOT"
git ls-files | awk -F/ 'NF>1{print $(1)"/"$(2)}' | sort | uniq -c | sort -rn | head -40   # shape
find . -maxdepth 3 -type d -not -path '*/node_modules*' -not -path './.git*' -not -path '*/.venv*' | sort
```

| Area | Look for | Feeds |
|---|---|---|
| Layout | Top-level directories; which hold the backend, the frontend, infra, docs, scripts | config `layout`, doc-map rules |
| Manifests | Package manifests per language (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, and their peers) and lockfiles | `TECH_STACK.md` |
| Entrypoints | The app factory or main module; the frontend root and router | `BACKEND_STRUCTURE.md`, `APP_FLOW.md` |
| Routes | Router or controller modules; every method and path; auth dependencies on them | API Endpoints |
| Models and migrations | Model modules, the migrations directory, the latest migration's schema | Database Schema |
| Schemas | Request and response validation modules | Data Validation |
| Services and jobs | Service modules, task or job definitions, schedules, storage adapters | Code Organization |
| Pages | Page components, route definitions, navigation components | Screen Inventory, Navigation |
| Components | Feature directories, shared components, hooks, lib | `FRONTEND_STRUCTURE.md` |
| Styles | Global stylesheet, token or theme configuration, dark-mode handling | `FRONTEND_GUIDELINES.md` |
| Tests | Test directories, runners, fixtures, whether a real database or a fake is used | `development-commands.md`, `REVIEW_CHECKLIST.md` |
| Containers | Compose file, container build files, their targets and services | `development-commands.md` |
| CI | Workflow files: jobs, commands, triggers, branch protection hints | `TECH_STACK.md` CI |
| Env | `.env.example` files, settings modules, secrets handling | `TECH_STACK.md`, `development-commands.md` |
| Existing docs | README, changelog, TODO or roadmap files, prior agent rules files, docs directories | Every doc, `AGENTS.md`, `TODOS.md` |
| Git | Default branch, recent commit subjects, open branches, tags | config `default_branch`, Current State |

Read the existing docs in full. Skim code by structure first (file lists, top-level
definitions), then read the files the docs will cite.

## Stack detection

Versions come from lockfiles, never from a manifest's range and never from memory. When there
is no lockfile, say so and record the range with a note to pin it in Phase 1.

| Signal | Tells you | Version from |
|---|---|---|
| Backend manifest dependencies | Framework, ORM, migration tool, job library, auth libraries, test runner | The backend lockfile |
| `package.json` dependencies and scripts | Frontend framework, build tool, styling, state library, test runner; the exact dev, build, and test commands | `package-lock.json` or the equivalent lockfile |
| Language pins (`.python-version`, `.nvmrc`, `.tool-versions`, container base images) | Runtime versions | The pin file or the image tag |
| Compose file services | Database engine and version, cache or broker, worker processes, ports | Image tags |
| CI workflow | The commands the project considers authoritative | Workflow file |
| Migration tool config | How migrations run and where they live | The tool's config file |

Present the result as the stack table (layer, choice, version, source file). One question per
layer that is ambiguous: two frameworks present, a dependency that looks unused, a lockfile
older than the manifest.

## Signs the code lies

Raise each as one line in the Uncertain list and, if unresolved, as an interview question:

- A directory with no imports pointing at it.
- Routes registered but not mounted; pages defined but not routed.
- Migrations ahead of or behind the models.
- Two test runners, or tests that cannot run with the documented command.
- An env variable read in code but absent from every example file.
- A README that describes commands the manifests no longer define.
