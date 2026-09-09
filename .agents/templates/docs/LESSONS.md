# Lessons

> Canonical project memory for mistakes, corrections, bug patterns, and workflow rules.
> Read this before planning or implementing work that touches the areas below.

## How To Use This File

- Update this file when the user corrects a pattern, when you catch your own mistake, or when the codebase teaches a non-obvious rule.
- Keep one canonical rule per topic. Preserve history in the logs below, but do not duplicate the same lesson in multiple sections.
- Prefer high-signal updates: what went wrong, why it went wrong, and what to do instead next time.
- Dated entries go in the Corrections Log and Bug Log tables. Decisions go under Decisions with a link to the plan.

## Workflow And Trust Rules

### Verify current state before claiming status

- Ask the user what is already complete if feature status is uncertain.
- Check recent changes before assuming "not started" from prior context or summaries.
- After one correction, immediately re-check all similar claims in the same document or plan.
- When documenting status, default to "what is already done?" instead of "what is probably missing?"
- Verify the repo's actual default branch before describing CI, PR, or release flow; do not assume `main` when the project uses `{{DEFAULT_BRANCH}}`.

### Never run unfiltered `env` / `printenv` against any machine that may carry secrets

- A remote console command that dumps the whole process environment (`ssh <host> env`, a platform's `console -C 'printenv'`, `{{CONTAINER_TOOL}} exec <service> env`, or any equivalent) WILL spill the database URL, encryption keys, signing secrets, API tokens, and more into the conversation transcript. Once spilled, those values are unrecoverably present in chat history and require rotation.
- This applies on hosted machines, containers, CI runners, and any remote shell — not just production.
- **Rule:** when checking env presence, always filter ON THE REMOTE SIDE before output leaves the machine. Acceptable patterns:
  - **Names only (no values):** `env | grep "^PREFIX_" | cut -d= -f1`
  - **Existence check, no values:** `for v in NAME1 NAME2; do test -n "${!v}" && echo "$v=set" || echo "$v=MISSING"; done`
  - **Count only:** `env | grep -c "^PREFIX_"`
  - **Specific named var with redaction:** `printenv VAR_NAME | sed 's/./*/g'` (preserves length only)
- Never use `printenv` (no args) or `env` (no args) — both dump everything.
- Never grep client-side: `<remote> -C 'printenv' | grep ^PREFIX_` already leaked the non-matching lines through the pipe to the local terminal, where they enter the transcript.
- Never paste a secret value into the conversation for any reason; refer to it by name.

<!-- example: discovered on a Fly.io deploy verification when an unfiltered `printenv` dumped DATABASE_URL, FERNET_KEY, JWT_SECRET_KEY, an access key, and REDIS_URL into chat; four of the five had to be rotated, and the fifth could not be because it encrypted data at rest. -->

### Use {{COMMAND_POLICY}} for app commands

- Never run the app's package manager, build, dev server, migration, or test commands outside the command policy stated in `development-commands.md`.
- The only host-side exceptions are the framework helpers under `.agents/bin` and their tests under `.agents/tests`; those never run inside a container.

### Verify behavior, not declarations

- Rendering correctly is not the same as animating correctly, syncing correctly, or handling errors correctly.
- For UI motion, verify in the browser that the motion actually fires.
- For backend changes, verify the real response shape and side effects, not just that code compiles.

<!-- guidance: add further rules here as the user corrects you: one `###` per topic, the rule
first, then why it went wrong, then what to do next time. Candidates that most projects
eventually need: "Explicit user-linked paths override editor context", "Merge review artifacts
instead of replacing them", "Ignored paths need deterministic path checks before treating a
search miss as absence". -->

## User Preferences

<!-- guidance: filled by init-project from the interview: learning goals, command policy,
review appetite, planning depth, anything the user said about how they like to work. -->

- Plan mode for non-trivial tasks.
- Verify before marking done.
- Simplicity first; no over-engineering.
- Surgical scope; touch only what is asked.

## Backend Lessons And Gotchas

<!-- guidance: one `###` per topic ({{BACKEND_FRAMEWORK}}, {{ORM}}, {{MIGRATION_TOOL}}, jobs,
integrations). Start empty; the REVIEW_CHECKLIST.md snippets already carry the generic ones. -->

## Frontend Lessons And Gotchas

<!-- guidance: one `###` per topic ({{FRONTEND_FRAMEWORK}}, {{STYLING}}, motion, forms, state). -->

## Decisions

<!-- guidance: every stack or scope decision with its reason and the plan that made it. Init
records the interview decisions here. -->

| Date | Decision | Why | Plan |
|---|---|---|---|
| {{DATE}} | | | — |

## Corrections Log

| Date | Source | What Went Wrong | What To Do Instead |
|---|---|---|---|

## Bug Log

| Date | Location | Bug | Fix |
|---|---|---|---|

## Infrastructure Post-Mortems

<!-- guidance: one `##`-level-worthy incident per `###`: what broke, the symptom map (error →
layer → fix), the canonical config that works, and the date discovered. -->

## Test Isolation Gotchas

<!-- guidance: state that leaks between tests (sequences, event loops, global config installed at
mixed fixture scopes) and the fix that held. -->

## Patterns That Work

-

## Patterns That Do Not Work

- Assuming feature completion status from prior conversation context without verifying current code.
- Trusting class names or configuration by name without verifying the underlying CSS, plugin, or setting exists.
- Shipping fixes based on theory instead of checking real behavior (computed styles, response bodies, logs).

## Domain Notes

<!-- guidance: short facts a new session needs: ports, where tokens live, which breakpoints
switch which view, the one-line description of the product. -->

- {{PROJECT_NAME}}: {{PROJECT_TAGLINE}}
- {{DB}} on `{{DB_PORT}}`, API on `{{APP_PORT}}`, frontend dev server on `{{FRONTEND_PORT}}`.
