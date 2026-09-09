# Lessons

> Canonical project memory for mistakes, corrections, bug patterns, and workflow rules.
> Read this before planning or implementing work that touches the areas below.

## How To Use This File

- Update this file when the user corrects a pattern, when I catch my own mistake, or when the codebase teaches a non-obvious rule.
- Keep one canonical rule per topic. Preserve history in the logs below, but do not duplicate the same lesson in multiple sections.
- Prefer high-signal updates: what went wrong, why it went wrong, and what to do instead next time.

## Workflow And Trust Rules

### Verify current state before claiming status

- Ask the user what is already complete if feature status is uncertain.
- Check recent changes before assuming "not started" from prior context or summaries.
- After one correction, immediately re-check all similar claims in the same document or plan.
- When documenting status, default to "what is already done?" instead of "what is probably missing?"
- Verify the repo's actual default branch before describing CI, PR, or release flow; do not assume `main` when the project still uses `master`.

### Explicit user-linked paths override editor context

- When the user provides a file path directly, including an `@path` reference, use that exact file as the source of truth.
- Do not substitute the currently focused editor file, a recently viewed file, or a previously discussed file just because it looks related.
- If the user corrects the path, discard the old target immediately and restate the new one before proceeding.

### Merge review artifacts instead of replacing them

- Test artifacts and review artifacts are execution contracts. When hardening them after a review, preserve high-signal gates, numbered E2E flows, operational invariants, log-hygiene checks, deployment guards, and critical paths unless they are truly invalid.
- If one detail inside a block is stale, rewrite that detail in place instead of deleting the whole block.
- After editing an artifact, reread the full file to verify there is only one coherent body, no stale contradictions remain, and every removed critical gate is represented with equal or clearer specificity elsewhere.

### Ignored review artifacts need deterministic path checks

- Files under `.agents/plans/testing/` may be ignored by `.gitignore` / Cursor search, so `Glob` or `rg` returning no matches does not prove a test artifact is absent.
- For branch test artifacts, first check the exact deterministic path: `.agents/plans/testing/<safe-branch>-test-artifact.md`.
- If the exact path is supplied by the user or derived from the branch, read it directly before falling back to search.

### Use Docker Compose for app commands

- Never run app `npm`, backend `uv`, or backend `pytest` commands directly on the host.
- Use Docker Compose for builds, tests, and runtime commands unless the task explicitly involves host-side `.claude` workflow tooling.

### Never run unfiltered `env` / `printenv` against any machine that may carry secrets

- `fly ssh console -C 'env'`, `fly ssh console -C 'printenv'`, or any equivalent that dumps the entire process environment WILL spill `DATABASE_URL`, `FERNET_KEY`, `JWT_SECRET_KEY`, API tokens, etc. into the conversation transcript. Once spilled, those values are unrecoverably present in chat history and require rotation.
- This applies on Fly machines, Docker containers, CI runners, and any remote shell — not just production.
- **Rule:** when checking env presence, always filter ON THE REMOTE SIDE before output leaves the machine. Acceptable patterns:
  - **Names only (no values):** `env | grep "^PREFIX_" | cut -d= -f1`
  - **Existence check, no values:** `for v in NAME1 NAME2; do test -n "${!v}" && echo "$v=set" || echo "$v=MISSING"; done`
  - **Count only:** `env | grep -c "^PREFIX_"`
  - **Specific named var with redaction:** `printenv VAR_NAME | sed 's/./*/g'` (preserves length only)
- Never use `printenv` (no args) or `env` (no args) — both dump everything.
- Never grep client-side: `fly ssh ... -C 'printenv' | grep ^R2_` already leaked the non-matching lines through the SSH pipe to the local terminal where they enter the transcript.

Discovered 2026-05-01 during M2 prod-deploy-skeleton Slice 3 verification — an unfiltered `printenv` call dumped DATABASE_URL, FERNET_KEY, JWT_SECRET_KEY, HOUSEHOLD_ACCESS_KEY, and REDIS_URL into chat. Four of the five had to be rotated; FERNET_KEY was kept due to iCloud-cred-decryption invariant.

### Verify behavior, not declarations

- Rendering correctly is not the same as animating correctly, syncing correctly, or handling errors correctly.
- For UI motion, verify in the browser that the motion actually fires.
- For backend changes, verify the real response shape and side effects, not just that code compiles.

## User Preferences

- Plan mode for non-trivial tasks.
- Use subagents to keep the main context clean.
- Verify before marking done.
- Simplicity first; no over-engineering.
- Surgical scope; touch only what is asked.
- Use `uv` for backend package management, but run backend app commands through Docker Compose.
- Use Docker Compose for full-stack development.

## Backend Lessons And Gotchas

### Async DB work from sync contexts

- When Celery tasks or other sync entry points create a fresh event loop, dispose the async engine before closing the loop.
- Without disposal, pooled asyncpg connections can leak across loops and trigger `"Future attached to a different loop"` on the second invocation.

```python
def run_async(coro):
    from .database import engine
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        if engine is not None:
            loop.run_until_complete(engine.dispose())
        loop.close()
```

### Pydantic and schema pitfalls

- When a field name matches a type in its own `Optional[]` annotation, alias the imported type. Example: use `from datetime import date as _Date` and annotate with `_Date`.
- New `bool` fields added to existing tables may come back as `NULL` for old rows. Response schemas should tolerate that if the database can still contain `NULL`.
- FastAPI validation `detail` payloads are often arrays of objects, not user-safe strings. Guard before rendering or passing them to toast helpers.

### Database and migration rules

- SQLAlchemy enum columns return enum members, not strings. Compare against the enum value, not a raw string.
- When Alembic autogenerates a PostgreSQL type conversion that cannot cast implicitly, add `postgresql_using=...` explicitly.
- Integration tests should target `TEST_DATABASE_URL`, not the dev database URL.

### iCloud / CalDAV gotchas

- iCloud can return `412 Precondition Failed` for `event_by_uid()` REPORT lookups. A direct event URL fallback is required.
- caldav `2.2.6` does not provide `edit_icalendar_instance()`. Use the `icalendar_instance` property and save the event.
- When pushing events, iterate all selected calendars instead of assuming the first one contains the event.
- Preserve local timezone information when generating ICS times so iCloud displays local times instead of raw UTC.

### API behavior and data threading

- New write paths must include the same required fields as established ones. Adding a shortcut API call path without required backend fields causes avoidable 422s.
- When creating new records inside synced parent contexts, inherit the parent's sync metadata and dispatch the same follow-up side effects as existing flows.
- When a caller passes contextual IDs like `section_id`, thread them end-to-end through the UI state and submit payload.

## Frontend Lessons And Motion Rules

### Never nest `<form>` elements

- HTML does not allow nested forms, but React's `createElement` renders them literally — so the DOM contains the invalid nesting. A `<button type="submit">` inside the inner form still submits the outer form via event bubbling, and both `onSubmit` handlers fire.
- Symptom: clicking a "submit" button inside a tab/panel caused the whole modal to disappear (or fail silently) because the OUTER form's handler tried to POST a partially-built payload on behalf of the unrelated inner button.
- Rule: when a sub-panel needs its own submit-like action inside an already-wrapping `<form>`, **use `<div>` plus button `onClick` + input `onKeyDown` Enter handling** instead of another `<form>`.
- Belt-and-suspenders: have the inner handler call `e.preventDefault()` AND `e.stopPropagation()` so no synthetic submit escapes, even if future code accidentally re-introduces a nested form.
- Bug case: `RecipeUrlImport.InputState` originally rendered `<form onSubmit=...>` around the Import button inside `RecipeFormBody`'s outer `<form>`. Clicking Import submitted the outer form, which called `onSubmit` with `name=""` + minimal fields. The error branch set `setError()` but the URL-tab doesn't render the error banner, so the user saw the modal "disappear" (actually: failed silently, and sometimes partial recipes were saved with whatever name was typed in Manual tab before switching). Fixed 2026-04-17. Regression test: `frontend/tests/components/RecipeImportClickBug.test.jsx`.

### Transitions need a real state change

- CSS `transition` utilities only animate when a mounted element changes state.
- Mount/unmount components like Headless UI `Dialog` need `Transition.Root` and `Transition.Child` with explicit enter and leave states.

```jsx
<Transition.Child
  enter="transform transition-transform duration-250 ease-out"
  enterFrom="translate-x-full"
  enterTo="translate-x-0"
  leave="transform transition-transform duration-200 ease-in"
  leaveFrom="translate-x-0"
  leaveTo="translate-x-full"
>
  <Dialog.Panel>...</Dialog.Panel>
</Transition.Child>
```

### Tailwind animation plugin classes are not core Tailwind

- `animate-in`, `fade-in`, `zoom-in-*`, `slide-in-*`, and `slide-out-*` do nothing unless `tailwindcss-animate` or an equivalent plugin is installed.
- Before using those classes, confirm the plugin exists in `package.json` and the CSS setup.
- For mount/unmount animations, prefer Headless UI transitions.
- For one-off entrances, use custom `@keyframes` plus inline `animation` or core Tailwind arbitrary animation syntax.

### Tailwind CSS v4 tree-shakes unlayered custom CSS

- Custom `@keyframes` and class selectors written outside a `@layer` in `index.css` are silently stripped by Tailwind v4's tree-shaker unless referenced by a generated Tailwind utility (e.g., `animate-[my-keyframe_0.4s_ease-out]`).
- **Fix**: place custom `@keyframes` inside `@layer base { ... }` and convert custom animation classes to `@utility name { ... }` directives.
- Symptoms: the class exists in the DOM but `getComputedStyle` shows `animationName: "none"` and the keyframe is absent from the compiled stylesheet.
- To debug: inspect `document.styleSheets` for the keyframe name; if absent, the CSS build pipeline stripped it.

### Do not mutate refs during render

- React Strict Mode double-renders make render-time ref mutation unreliable.
- CSS entrance animations usually do not need ref guards at all; the browser already avoids replaying them on ordinary re-renders of the same DOM node.

### Animation fill mode and composition

- Use `animation-fill-mode: both` on mount animations to avoid first-frame flashes.
- Do not fade a container while also staggering its children if the parent opacity hides the child motion.
- If a crossfade is bidirectional, verify both directions.

### Loading, empty, and layout states

- Async UI has three states: loading, empty, and populated. Do not render empty states during loading.
- If the wrong-state flash would be visible, return `null` or a skeleton until data exists.
- Track all parallel initial fetches in the loading state.
- When rendering a component unconditionally from frame zero (to avoid spinner flash), audit its empty-state guards. A `if (items.length === 0) return <EmptyMessage />` that was harmless behind a spinner will flash a misleading empty state during the loading phase. Gate such guards on `initialLoaded` so they only fire after data has actually loaded.
- Use `ml-auto` instead of `justify-between` when right-aligning a dynamic child in a row whose left content may mount later.

### CSS cascade and stale classes

- When Tailwind utilities are not taking effect, check for handwritten CSS rules on the same element before theorizing about variants.
- Reused old class names can pull in stale stylesheet rules that override the new Tailwind approach.
- Search `index.css` before debugging a class-name-specific issue.

### Console errors during live edits are usually HMR transients — verify against a clean reload before fixing

- Vite's Hot Module Reload serves in-between versions of a file as you save edits. A browser tab left open during a multi-file refactor will collect errors like `ReferenceError: oldHandler is not defined` even though the finished code has zero references to `oldHandler`.
- Telltales: error stack trace cites a line number larger than the current file has (e.g. `MealCard.jsx:316` when the file is 304 lines), URL has a cache-buster (`?t=1776555502155`), and multiple sequential errors have different timestamps ~seconds apart.
- The other HMR-only signal: `"The final argument passed to useEffect changed size between renders. Previous: [[object Map]] Incoming: []"` — this fires when a useEffect's dep array shape changes mid-component-lifetime, which only React's HMR state preservation can create; a full reload resets to a consistent lifecycle.
- **Before treating a console error as a real bug, always:** (1) `grep` the current source for the symbol the error references — if absent, it's stale; (2) reload the page fresh and capture a new error trace; (3) check the line number against `wc -l` of the file.
- Fixed 2026-04-19 after the `mealboard-meal-card-polish` handover: three stack traces of `handleViewRecipe is not defined` were HMR artifacts from Chunk-1 edits; the committed code had no such reference.

### Single-delete invariant for meal entries (regression test)

- Deleting ONE meal card must remove EXACTLY ONE card from the swimlane grid. Covered by `frontend/tests/components/mealboard/MealPlannerView.delete.test.jsx`: happy-path undo flow, mixed-version fallback (no `undo_token` in response), and rapid sequential delete (F3 regression for the timer-cancel race).
- When a user reports "X caused Y other things to disappear" and can't reproduce, prefer adding a regression test to lock in the correct invariant rather than speculatively refactoring. The test prevents the next occurrence from going unnoticed.

## Corrections Log

| Date | Source | What Went Wrong | What To Do Instead |
|------|--------|----------------|-------------------|
| 2026-02-05 | user | Stated Mealboard Integration was incomplete — it was already working | Ask the user what is already complete before documenting status |
| 2026-02-05 | user | After the first correction, still claimed Shopping List Integration was incomplete | After one correction, re-examine all similar claims immediately |
| 2026-02-05 | self | Carried over assumptions from conversation summary without verifying | Check recent code state before trusting prior context |
| 2026-02-07 | user | Attempted to run `npm run build` directly on the host instead of through Docker | Always use Docker Compose for app builds, tests, and dev commands |
| 2026-02-07 | self | Built `QuickAddPopover` but never wired it into `MonthView` | Trace the full interaction path end to end before marking a step complete |
| 2026-02-07 | user | TimeGrid quick-add behavior diverged across calendar views | Verify shared interactions across all relevant views, not just the first one touched |
| 2026-04-08 | self | Added argparse flags but broke tests that manually construct `argparse.Namespace(...)` | Use `getattr(args, "flag", default)` when callers may bypass the parser |
| 2026-04-08 | self | Assumed markdown task ranges always behave like half-open spans | Handle zero-span and task-line-only range cases explicitly |
| 2026-04-18 | user | Ran a plan review against the focused historical plan instead of the explicit `@...` plan path the user linked | Explicit user-linked paths override editor context, recent files, and prior-turn plan assumptions |
| 2026-05-02 | user | While deduplicating an adversarial-review test artifact, removed a still-valid numbered E2E gate and operational invariants because nearby login-rotation wording was stale | Merge review artifacts surgically: preserve valid critical gates and rewrite stale details in place; reread the full artifact after edits |
| 2026-05-03 | user | Claimed no current-branch test artifact existed because `Glob`/`rg` returned no matches under ignored `.agents/plans/testing/`, even though the deterministic artifact path existed and was directly readable | Check `.agents/plans/testing/<safe-branch>-test-artifact.md` by exact path before treating search-tool misses as absence |

## Bug Log

| Date | Location | Bug | Fix |
|------|----------|-----|-----|
| 2026-03-31 | `schemas.py:CalendarResponse` | Added `is_todo: bool = False`, but existing rows had `NULL`, causing response validation failures and masked browser CORS errors | Use a schema that tolerates existing `NULL` values until the data is fully backfilled |
| 2026-03-31 | `crud_tasks.py:create_task` | Tasks created in a synced list did not inherit sync metadata or dispatch push behavior | Inherit the parent sync metadata and queue the same sync side effects on create |
| 2026-03-31 | `ListsPage.jsx` + `TodoForm.jsx` | Section-scoped task creation dropped `section_id` | Thread `section_id` through the page state and submission payload |
| 2026-02-08 | `ResponsibilitiesPage.jsx` | Responsibility edit PATCH omitted `icon_url` and `description` | Include the full intended editable payload in PATCH requests |
| 2026-02-08 | `ScheduleView.jsx:groupByCategory` | Category filter pills did not actually filter grouped responsibilities | Restrict grouping logic to the selected category when filtering is active |
| 2026-02-25 | `app/tasks.py:run_async` | Celery async bridge reused asyncpg connections across event loops | Dispose the engine before closing each fresh loop |
| 2026-03-02 | `app/schemas.py:CalendarEventUpdate`, `MealPlanUpdate` | Pydantic V2 name shadowing broke `Optional[date]` field resolution | Alias imported types used in shadow-prone optional annotations |
| 2026-03-02 | `app/services/caldav_client.py:update_remote_event` | iCloud sync failed due to `event_by_uid()` behavior, a missing caldav method, and incorrect calendar selection | Add direct URL fallback, use `icalendar_instance`, and iterate calendars properly |
| 2026-03-02 | `useCalendarData.js` | Sync badge stayed stuck because the frontend never re-fetched after async push completion | Poll while any event is in `PENDING_PUSH` until the state clears |
| 2026-04-02 | `ListsPage.jsx:createTaskInline` | Inline task creation missed required backend fields and rendered FastAPI error objects unsafely | Match backend-required fields and normalize API error details before rendering |
| 2026-03-02 | `caldav_client.py:_apply_times_to_vevent` | Pushed events used UTC Z-suffixes and displayed confusing times in iCloud | Preserve local timezone notation so generated ICS uses `TZID` |
| 2026-04-15 | `index.css` | All custom `@keyframes` and `.class` animation rules (swimlane-enter, meal-card-enter, bounce-in, etc.) silently stripped by Tailwind CSS v4 tree-shaker | Move `@keyframes` into `@layer base`, convert animation classes to `@utility` directives |
| 2026-04-17 | `RecipeUrlImport.jsx` + `ItemFormModal.jsx` | Nested `<form>` — RecipeUrlImport's inner form was inside RecipeFormBody's outer form. Clicking the Import button bubbled a submit event to the outer form, which tried to POST /items with empty fields; user saw the modal disappear | Inner panel uses `<div>` + `onClick` on button + `onKeyDown` on input; both handlers `stopPropagation()` to prevent any bubbling. Regression test at `frontend/tests/components/RecipeImportClickBug.test.jsx` |
| 2026-04-19 | `MealPlannerView.jsx` pendingDeletes cleanup | `useEffect(() => cleanup, [pendingDeletes])` cancelled the previous Map's timers on every state change. Rapid sequential deletes killed the first meal's 5s purge timer → the first UndoMealCard stuck on-screen forever | Switched dep to `[]` with a ref mirror (`pendingDeletesRef.current`) so cleanup only runs on unmount. Adversarial-review F3 / lock-in tests at `frontend/tests/components/mealboard/MealPlannerView.delete.test.jsx` |
| 2026-04-19 | `crud_items.py:undo_soft_delete_item` restore cascade | Restoring a soft-deleted Item cleared `soft_hidden_at` on cascade-hidden meal_entries but left `undo_token` populated. Live rows must have `undo_token=NULL` per the state-machine invariant documented in `crud_meal_entries.py`. No user-visible corruption (CAS guard prevents accidental undo of live rows), but a latent foot-gun | Added `undo_token=None` to the restore UPDATE's `.values()` |

## Fly Postgres + asyncpg setup

`fly postgres attach` prints connection strings shaped for psycopg2 (libpq). asyncpg rejects three of those defaults. When wiring Fly Postgres into a SQLAlchemy + asyncpg project, expect to do all three of these *before the first `fly deploy`*:

1. **Scheme:** Fly prints `postgres://`. asyncpg requires `postgresql+asyncpg://`. Override with `fly secrets set DATABASE_URL="postgresql+asyncpg://USER:PASS@HOST:5432/DB"`.
2. **SSL parameter name:** asyncpg does not accept `sslmode=` as a connect kwarg. SQLAlchemy passes URL query params through to the dbapi; `?sslmode=require` → `TypeError: connect() got an unexpected keyword argument 'sslmode'`. Use `?ssl=require` if SSL is wanted, OR drop the parameter entirely.
3. **Internal connections have no SSL:** Fly's `.flycast` and `.internal` Postgres endpoints don't have application-layer TLS configured (the WireGuard mesh handles encryption between machines). asyncpg's default `ssl=prefer` policy attempts a TLS handshake that the server resets mid-stream, surfacing as `ConnectionResetError` in `_create_ssl_connection` — NOT a clean rejection that asyncpg would fall back from. Explicitly disable: `?ssl=disable` in the URL query string.

**Canonical Fly Postgres internal DATABASE_URL for an asyncpg app:**

```
postgresql+asyncpg://USER:PASS@<app>-db.flycast:5432/DB?ssl=disable
```

(Substitute `.internal` for `.flycast` on older Fly Postgres clusters.)

Symptoms map:
| Error | Layer | Fix |
|-------|-------|-----|
| `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgres` | Scheme | Use `postgresql+asyncpg://` |
| `TypeError: connect() got an unexpected keyword argument 'sslmode'` | URL parsing | Rename `sslmode=` → `ssl=` or drop |
| `ConnectionResetError` during `_create_ssl_connection` | TLS handshake | Add `?ssl=disable` |
| `socket.gaierror: Name or service not known` | DNS | Wrong host (typo / unsubstituted placeholder / wrong suffix `.flycast` vs `.internal`) |

Discovered 2026-04-30 during M2 prod-deploy-skeleton Slice 1 first deploy.

## Celery + Upstash Redis (rediss://) on Fly

Celery's Redis backend AND broker have an SSL-config mismatch contract that rejects the URL in *both* directions:

- `rediss://` URL with NO `broker_use_ssl`/`redis_backend_use_ssl` config → `ValueError: A rediss:// URL must have parameter ssl_cert_reqs and this must be set to CERT_REQUIRED, CERT_OPTIONAL, or CERT_NONE`.
- `redis://` URL WITH `broker_use_ssl`/`redis_backend_use_ssl` config → `ValueError: SSL connection parameters have been provided but the specified URL scheme is redis://. A Redis SSL connection URL should use the scheme rediss://.`

Local docker-compose typically uses plain `redis://`; Upstash forces `rediss://`. To make one codebase boot in both, gate the SSL config on the URL scheme:

```python
import ssl
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("appname", broker=REDIS_URL, backend=REDIS_URL, ...)

celery_app.conf.update(
    # ... non-SSL config ...
    **(
        {
            "broker_use_ssl": {"ssl_cert_reqs": ssl.CERT_REQUIRED},
            "redis_backend_use_ssl": {"ssl_cert_reqs": ssl.CERT_REQUIRED},
        }
        if REDIS_URL.startswith("rediss://")
        else {}
    ),
    # ... beat_schedule etc ...
)
```

`CERT_REQUIRED` validates against the system CA bundle (Upstash uses publicly-trusted Let's Encrypt certs). Use `CERT_NONE` only if the cert chain is genuinely problematic (e.g. self-signed Redis with no CA distribution).

Discovered 2026-04-30 during M2 prod-deploy-skeleton Slice 2 first deploy.

## Cloudflare Access — path-based bypass requires a SEPARATE Application

Cloudflare Access Policy "Include" selectors are **identity-based only**: Country, IP ranges, Common name, Service Token, Email, Email domain, Everyone, etc. There is no "Hostname" or "Path matches regex" selector at the policy level. So you cannot write a single Application with one "Allow on /healthz" policy and another "Bypass on /plumbing-test" policy keyed off the request path.

The correct mechanism for path-based bypass is two Self-hosted Applications:

1. **Broad Application** — domain = full subdomain (e.g., `api.mealy.dev`), path field empty. Policy: Allow + identity allowlist.
2. **Narrow path-bound Application** — domain = `api.mealy.dev` with explicit Path = `plumbing-test` (one row per path). Policy: Bypass + Everyone (or IP ranges 0.0.0.0/0 + ::/0 if Everyone unavailable).

Cloudflare evaluates the more-specific path-bound Application FIRST. So a request to `/plumbing-test` matches the bypass app and skips auth; everything else falls through to the broad app and gets the auth challenge.

> Keep paths EXACT. A bypass app with `path = plumbing-test` (no wildcards) covers exactly that path and `/plumbing-test` only. Empty path = the bypass covers the whole subdomain — that would unintentionally make the entire API public.

Discovered 2026-05-01 during M2 prod-deploy-skeleton Slice 4 (Cloudflare Access setup) — runbook had to be corrected, `infra/cloudflare-state.md` schema updated to document the two-application structure.

## Celery beat schedule file location under non-root containers

Celery beat's default `PersistentScheduler` writes a shelve database to the cwd as `celerybeat-schedule` (with `.dir`/`.dat` siblings depending on dbm backend). When the container runs as a non-root user but the cwd (`/app` etc.) was created as root, the shelve open fails inside `setup_schedule()` and beat crashes (Python exits with the entire traceback emitted as a long stream of single-character `^` "underline" lines via Celery's WARNING logger — which makes it very hard to read in archived logs).

Fix: pass `--schedule=/tmp/celerybeat-schedule` (or another writable path) to the beat command. Loss-on-restart is fine for typical schedules — beat re-derives entries from `celery_app.conf.beat_schedule` on boot.

```toml
# fly.toml — full prod-image, non-root container
[processes]
  beat = "celery -A app.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule"
```

Local dev images that run as root don't hit this because root can write `/app/celerybeat-schedule`.

Discovered 2026-04-30 during M2 prod-deploy-skeleton Slice 2 (Fly).

## Patterns That Work

- In Docker exec sessions, Alembic may need the virtualenv path explicitly: `docker-compose exec api .venv/bin/alembic`.
- After changing backend models or schemas, restart the API container when hot reload does not pick up the effective runtime state.
- Thread page handlers down to leaf components and use `stopPropagation` for nested click targets.
- Use Headless UI render props like `{({ close }) => ...}` when a popover must close before opening another modal.

## Obsidian Workflow

- `update_note_file` always re-emits `MANAGED_MULTI_KEYS` (e.g. `review_status`) via the merge logic, so the filter that strips existing lines must include `MANAGED_MULTI_KEYS` — not just `set_fields`, `append_fields`, and `MANAGED_SINGLE_KEYS`. Without this, any `--set`-only call (like `--set status=shipped`) doubles existing multi-key entries. Fixed 2026-04-12.
- When adding new managed key categories to `obsidian-workflow`, always verify the filter condition in `update_note_file` (line ~936) covers them, or they will silently duplicate on non-append updates.

## Patterns That Do Not Work

- Assuming feature completion status from prior conversation context without verifying current code.
- Trusting animation-related class names without verifying that the underlying CSS or plugin actually exists.
- Shipping CSS fixes based on theory instead of checking computed styles in the browser.

## Test isolation gotchas

### PostgreSQL sequences advance on rolled-back INSERTs

- SAVEPOINT-based test isolation rolls back rows but does NOT roll back sequences. A test that inserts a user, fails, and rolls back still bumps `users_id_seq`. Subsequent tests that hardcode `assert payload["sub"] == "1"` start failing once the sequence has advanced beyond 1.
- **Fix:** reset sequences explicitly at the start of each test, AFTER `Base.metadata.create_all` (which is itself idempotent). Pattern:
  ```python
  seq_rows = await setup_conn.execute(text(
      "SELECT sequence_name FROM information_schema.sequences "
      "WHERE sequence_schema = 'public'"
  ))
  for (seq_name,) in seq_rows.fetchall():
      await setup_conn.execute(text(f'ALTER SEQUENCE "{seq_name}" RESTART WITH 1'))
  ```
- Discovered 2026-05-06 during M5 PR1 integration-test conftest refactor — `test_e2e_flow.py` failed with `'239' == '1'` after ~239 prior tests had auto-incremented `users.id`.

### Mixed pytest-asyncio loop scopes leak pooled connections

- When session-scoped async fixtures (e.g. a shared `test_engine`) share state with function-scoped tests via SQLAlchemy connection pools, the default per-function loop scope leaks pooled asyncpg connections across loops. Symptom: `Future attached to a different loop` on the second test using the engine.
- **Fix (simplest):** set both defaults to `"session"` in `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  asyncio_default_fixture_loop_scope = "session"
  asyncio_default_test_loop_scope = "session"
  ```
- This matches the standard pattern for integration test suites with shared DB resources. The same class of bug as the LESSONS.md "Async DB work from sync contexts" Celery note — pooled async connections must not span event loops.

### Per-test `auth_config.reset()` collides with session-scoped `auth_config.configure()`

- `tests/integration/auth/conftest.py` has a function-scoped autouse `install_auth_test_config` that calls `auth_config.reset()` at teardown. If a parent conftest also installs auth config but session-scoped, the parent's install fires once at session start and stays installed — until the first auth subfolder test resets it. After that, every post-auth-subfolder test runs with `_settings=None` and 500s on protected routes.
- **Rule:** when the same global state is being installed at multiple test-suite scopes, make the broadest install function-scoped autouse so it re-installs after any narrower per-test reset. Discovered 2026-05-06 during M5 PR1.

## Domain Notes

- Family task and responsibility management app with a FastAPI backend and React frontend.
- PostgreSQL runs on `5433`, API on `8000`, Vite on `5173`, Redis on `6379`.
- TailwindCSS v4 uses custom theme values in `frontend/src/index.css`.
- Dark mode is class-based on the document root.
- Mealboard has two responsive breakpoints: `1200px` for header layout (single-row vs. collapsed) and `768px` for the SwimlaneGrid vs. MobileDayView switch (`MealPlannerView.jsx:67`).
- iCloud calendar sync uses CalDAV, Celery, and timezone-aware settings from the app settings singleton.

## Decisions

| Date | Decision | Why | Plan |
|---|---|---|---|
| 2026-04-21 | Visual regression for mealboard: geometric-invariant tests (bbox/width/position deltas) catch the actual bug class deterministically without font-rendering Docker wrestling; pixel snapshots should be a secondary layer, not the primary mechanism | recorded by /office-hours | branch mealboard-todos-042026 |
| 2026-04-22 | Infra-first for prod migrations: split-origin cookies, Fly migrations-on-release, and similar infra unknowns cost the most to discover late. De-risk infra before auth code commits to it. Ordering rule: which unknown costs the most to discover late? | recorded by /office-hours | branch prod-contract-freeze |
| 2026-04-23 | Single-instance Fly deployments should use shallow /healthz (process-alive only), not deep DB+Redis probes. Deep health checks with min_machines_running=1 turn 5-sec dep flaps into total user-facing downtime — Fly pulls the only instance from rotation. Conventional wisdom (deep probes) assumes multi-instance + LB routing around bad instances; single-instance config inverts the calculus. | recorded by /plan-eng-review | branch prod-deploy-skeleton |
