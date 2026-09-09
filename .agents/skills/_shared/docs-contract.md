# Documentation contract

The documentation set is the agent's knowledge base and the project's memory. It lives in
`$DOCS_DIR`. Facts live in one doc and are linked from the others.

| Doc | Owns | Updated when |
|---|---|---|
| `PRD.md` | What is being built, for whom, scope, acceptance criteria, business rules, roadmap versions | Features, acceptance criteria, or scope change. A planned feature deviates from spec. |
| `APP_FLOW.md` | Every screen, route, navigation path, user flow, error copy | Pages, routes, flows, or user-facing error states change |
| `TECH_STACK.md` | Every dependency with its version, infrastructure, CI, external integrations | A dependency is added or bumped, a technology choice changes |
| `FRONTEND_GUIDELINES.md` | Design tokens, typography, spacing, breakpoints, component patterns, motion, accessibility | New tokens, colors, patterns, or reusable UI conventions |
| `FRONTEND_STRUCTURE.md` | Frontend directory layout, per-feature file inventory, behavioral notes, key patterns | Frontend directories, component ownership, or shared architecture change |
| `BACKEND_STRUCTURE.md` | Schema, endpoints, code organization, validation, error handling, storage | Tables, columns, endpoints, services, or backend organization change |
| `IMPLEMENTATION_PLAN.md` | The roadmap: phases with status and plan links, epic milestone tables, deferrals | A phase or milestone starts, ships, is deferred, or is discovered |
| `LESSONS.md` | Workflow rules, gotchas, corrections log, bug log, decisions, patterns | Any correction from the user, any non-obvious thing the codebase teaches, any decision |
| `TODOS.md` | Deferred engineering items with enough context to resume cold | A review or implementation surfaces work worth doing later |
| `development-commands.md` | How to run, build, test, migrate, lint; required env vars | Commands, services, or env vars change |
| `REVIEW_CHECKLIST.md` | Stack-specific checks reviewers must run | A technology is added or a review finds a repeatable class of bug |

`AGENTS.md` at the repo root is updated when commands, structure, dependencies, env vars, or
build and test procedures change. It links to the docs; it does not duplicate them.

## The doc map

`config.json` maps code paths to owning doc sections. It is the single input for
`/update-docs`, the review staleness gate, and the `doc-guard` hook. When you add a top-level
directory, add it to the map or to the exempt list in the same change.

```bash
"$BIN/doc-guard" --explain <path>            # who owns a path
"$BIN/doc-guard" --staged --dry-run          # what a commit of the index would trip
"$BIN/doc-guard" --worktree                  # everything on the branch, committed or not; exit 1 = gate fails
```

## When to run `/update-docs`

- Execute-plan, when the last step completes.
- Quickfix and ship, before committing.
- Any time you changed code outside a skill. AGENTS.md says so; the hook enforces it.
- `/update-docs --full` after adopting an existing project or when drift is suspected.

Update-docs applies factual drift without asking: a new endpoint, dependency, route, renamed
component, completed phase. It stops and asks for narrative rewrites, PRD scope changes, and
removals. It never regenerates a doc from scratch; it edits.

## LESSONS.md discipline

One canonical rule per topic. When the user corrects you, write the rule, why it went wrong, and
what to do next time. Dated entries go in the Corrections Log and Bug Log tables. Decisions go
under Decisions with a link to the plan. Do not duplicate a lesson across sections.
