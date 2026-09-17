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

### The visual-test `api-test` container has no bind-mount — rebuild it after backend changes

- `docker-compose.yml`'s `api` service bind-mounts `./app`, but `api-test` (the visual-test
  profile's backend) deliberately does not (Adversarial A5) — it bakes the code in at build time.
- The documented sequence built only `frontend-preview frontend-visual`, so a backend change ran
  the Playwright suite against the previously-built backend and "passed" while proving nothing.
- **Rule:** `docker-compose --profile visual-test build api-test frontend-preview frontend-visual`
  whenever backend code changed. Also avoid the documented `down -v` teardown mid-session: it
  removes the shared `db` and `uploads_data` volumes. Fixed in `development-commands.md`
  2026-09-09.

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

### Runbook checks must be runnable, and meaningful, where they sit

- A pre-deploy gate that inspects behavior only the new code produces cannot pass before the deploy. The M7 runbook asked for the private-media `cache-control` header and `cf-cache-status` as pre-cutover gates, but the old StaticFiles mount sent no `Cache-Control`. Split such a gate: the precondition (a dashboard setting) goes before the deploy, the observation goes in the smoke checks.
- A check must fail when the thing it guards is broken. "The image loads" was OQ1's signal, but before the deploy the old mount served the image with or without the cookie. The real signal was the cookie on the request.
- A log-line check needs a line that is always printed. The sweep's `Abandoned-upload sweep: deleted N` line only appears when there is something to delete, so check the Celery `Task … succeeded` line instead.
- An edge gate answers before the app. While Cloudflare Access was up, a no-cookie `curl` got Access's 302, not the app's 401, so it said nothing about the app.

Discovered 2026-09-11 while executing `infra/r2-cutover-runbook.md`.

### Worktrees: pass literal absolute paths to framework helpers, and recreate the vault link

- The harness can reset the shell's cwd between commands, so `cd` and `"$PWD"` inside one Bash call are not reliable from a worktree. One `framework upgrade "$PWD"` call landed 27 payload files in the main checkout (restored with `git checkout --`). Pass the worktree's literal absolute path to `framework upgrade` and `framework doctor`, and confirm the tool's header line names it.
- Worktrees under `.claude/worktrees/` have no `todo-app-notes/` (gitignored, not its own repo). `/ship` writes to `$VAULT_DIR/Learning/` and `obsidian-workflow` raises `vault not found` on vault scans. Symlink `todo-app-notes -> ../../../todo-app-notes` in the worktree and keep the link out of `git status` with a `todo-app-notes` line in the shared `.git/info/exclude`; the `todo-app-notes/` ignore pattern matches directories only.
- `core.hooksPath` must be the relative `.agents/hooks` so each worktree runs its own `commit-msg` hook; `framework doctor` FAILs on an absolute path.

Discovered 2026-09-16 while resolving the execute-plan concerns on `workflow-review-resolution`.

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

### Anchor Python key/path regexes with `\Z`, never `$`

- Python's `$` matches at end-of-string **or just before a trailing newline**. A validator like
  `re.match(r"^item-icons/<uuid>\.png$", key)` therefore accepts `"item-icons/<uuid>.png\n"`.
- For anything where the match IS the identity of a resource — a storage key, a path segment, a
  filename — use `\Z`. A key with a stray newline is a key that exists in neither the database
  nor the object store, so it silently becomes a no-op delete or a phantom 404 rather than a
  loud error.
- Discovered 2026-09-09 in M7 PR2 by a `trailing-newline` parametrized case in
  `tests/unit/test_storage_keys.py` — written as an obvious-looking negative that turned out to
  pass. Both `app/storage/keys.py` regexes were affected.

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

### Parse API timestamps as UTC — they arrive without a timezone

Datetime columns are `timestamp without time zone` holding UTC, and Pydantic serializes them with no offset (`2026-09-11T20:07:34`). `new Date(thatString)` reads it as **local** time, so every derived duration is off by the viewer's UTC offset — west of Greenwich, a recent timestamp lands in the future and "5 minutes ago" renders as "just now".

- Append `Z` when the string carries no offset before constructing a `Date` (`ICloudSettings.jsx: parseServerTime`), or anchor the countdown on the client clock where that is honest (`MealPlannerView.jsx` undo window).
- Test fixtures must use the API's real shape. `new Date().toISOString()` adds the `Z` that production never sends, which is exactly why this went unnoticed — and pin a non-UTC `process.env.TZ` in the test, or the assertion passes in UTC CI either way.

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
| 2026-09-16 | self | `framework upgrade "$PWD"` from a worktree upgraded the main checkout (27 payload files) because the harness reset the shell cwd between commands | Pass the literal absolute worktree path to framework helpers and check the header line names it; restore stray files with `git checkout --` |

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
| 2026-09-11 | Cloudflare Access Application 1 (edge, `api.mealy.dev`) | Operator could not log in at mealy.dev; the console showed a CORS error on `api.mealy.dev/auth/status`. The Access session for `api.mealy.dev` had lapsed (Access sessions are per hostname, 24h here), so Access answered the SPA's XHR with a 302 to its login page on `mealyapp.cloudflareaccess.com`, which carries no CORS headers. The app's own CORS config was correct | Workaround: open any `api.mealy.dev` URL in a tab to re-authenticate. Fixed for good by removing Application 1 at the M7 cutover. When a browser CORS error hides the real response, `curl -i` the URL with an `Origin` header first — a 3xx or 5xx from the edge is the usual cause |
| 2026-09-11 | `app/main.py:production_host_gate` | The gate compared only the client-written `Host` header. Fly holds a cert for `api.mealy.dev`, so `curl --resolve` to the Fly IP reached the app and skipped the Cloudflare `/auth/*` rate limit — the only brute-force and argon2-CPU control on login | Gate also requires `X-Origin-Verify` (set by a Cloudflare Transform Rule) to match the `ORIGIN_VERIFY_SECRET` Fly secret; production refuses to boot without it. Regression tests in `tests/integration/auth/test_host_gate.py` and `tests/unit/test_origin_verify_bootstrap.py` |
| 2026-09-11 | Fly `worker` process group (`mealy-app-prod`) | The Celery worker machine had been stopped since at least the end of May — 103 days. iCloud calendar and reminder sync, the soft-delete purge, and the abandoned-upload sweep never ran; 32,136 scheduled jobs queued in Upstash. Nothing surfaced it: web stayed healthy, beat kept queueing, and the M7 deploy updated the stopped machine without starting it | Purged the queue and started the machine. `[[restart]] policy = "always"` on `worker` and `beat`; a `fly status` "every process group started" check in the cutover runbook; a sync-freshness dot in `ICloudSettings.jsx` so the next outage is visible in the app |
| 2026-09-15 | `/office-hours` on `workflow-review-resolution` | Planned an upgrade against a stale `master`: the worktree branch was cut at `651ff27` while `origin/master` was three PRs ahead (#50–#52), so the plan called for re-applying eight files that had already shipped and would have conflicted in `.agents/manifest.json`. A `framework upgrade --dry-run` "confirmed" the stale view | Before writing a plan whose steps depend on repository state, `git fetch` and compare the branch against `origin/<base>`, not the local base ref; state the base commit in the plan |
| 2026-09-11 | `ICloudSettings.jsx:relativeTime` | "Last synced" was off by the viewer's UTC offset. `last_sync_at` is a `timestamp without time zone` serialized without a `Z`, and `new Date()` read it as local time — in PDT a sync from five hours ago rendered "just now", which would have made the new freshness dot lie | `parseServerTime` appends `Z` when the string carries no offset. Tests use the API's no-`Z` shape with `process.env.TZ` pinned to `America/Los_Angeles`; the old fixtures used `toISOString()`, whose `Z` hid the bug |
| 2026-09-16 | `.agents/bin/_lib.py` review log (framework 1.1.0, before PR-F merged) | `json.dumps(ensure_ascii=False)` writes U+2028, U+2029 and U+0085 raw while `str.splitlines()` treats them as line breaks, so one `note` holding one made the whole review log unreadable and every review command refused; a supplied `ts` was never validated, so a null or number crashed the readers once a review had two entries, and a future date would have shadowed every later run | Escape the three characters on write (`review_log_line`); stamp `ts` before the rules run and require UTC `YYYY-MM-DDTHH:MM:SSZ` not later than now; compare timestamps only through `review_ts`. Found by `/review-implementation` and its adversarial subagent on `workflow-review-resolution`; fixed in framework `0cda9ef`; checks added to REVIEW_CHECKLIST.md → Framework helpers |
| 2026-09-17 | `.agents/bin/_lib.py` `review_disposition` | Writer used `can_resolve`; reader only checked "gating tier, not self". A hand-appended or union-merged `resolved_by=ship` (or a plan-stage resolver on a ship-stage skill) read as `resolved` and opened the gate. A `resolved` line with no prior failure did the same. Text rows still split on U+2028 after the writer escaped the file. | Reader uses `can_resolve` and requires the target to be a gating tier; unmatched / duplicate-timestamp resolutions get `superseded_by_failure`; `fmt_review_value` quotes with `ensure_ascii=True`. Found by `/final-review` adversarial pass. |
| 2026-09-17 | M7 plan `prod-r2-storage` Adopt step vs `services/asset_lifecycle.py::adopt` | The adversarial plan review wrote an adopt-time rejection of already-referenced keys into the Adopt bullet and claimed it under "What this review changed", without editing Eng review 1 (A1), which had accepted the shared-key case in the same section. The plan carried both rules; PR #44 shipped A1, so the plan claimed a control that never existed. The rule as written was also unshippable: the recipe form sends one upload as both `icon_url` and `recipe_detail.image_url`, which a `referenced=false` precondition would 400. | Decided with the user: A1 stands. Plan annotated in place (struck through, dated), the module docstring corrected from "one entity column" to "one entity", the same-item shared-key flow pinned by `test_recipe_form_shares_one_key_across_icon_and_image`. Rule already exists under "Merge review artifacts instead of replacing them": reread the whole file for stale contradictions. A review's summary bullet describes the plan, not the code; check the control shipped. |

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

## A Host-header check does not stop direct-to-origin bypass

When the origin holds a TLS certificate for the public hostname (Fly does for `api.mealy.dev`, through the `_acme-challenge.api` record), anyone can skip Cloudflare by connecting to the origin IP with the public hostname as both SNI and `Host`:

```bash
curl --resolve api.mealy.dev:443:<fly-ip> https://api.mealy.dev/...
```

That request carries the same `Host` as a Cloudflare-proxied one, so a gate comparing `Host` with `PUBLIC_API_HOST` lets it through, and Cloudflare never sees it: no WAF rate limit, no Access, no Transform Rule. The M3 `production_host_gate` only ever stopped callers who used the `*.fly.dev` name.

- **Rule:** to prove a request came through the edge, check something only the edge can add. Here that is a secret header set by a Cloudflare Transform Rule (`X-Origin-Verify`, compared with `hmac.compare_digest` against the `ORIGIN_VERIFY_SECRET` Fly secret). A `Host` check is a fine extra layer, but on its own it proves nothing.
- A Cloudflare IP allowlist is not proof either: every Cloudflare customer shares those ranges, so another tenant can reach the origin from a Cloudflare IP with their own WAF off.
- Two traps in the compare. `hmac.compare_digest` raises `TypeError` on non-ASCII `str`, so compare bytes (otherwise a forged header is a 500, not a rejection). And an empty configured secret equals an absent header, so reject explicitly when the secret is empty.
- Headers the edge normally sets are attacker-controlled on a request that went around it. `resolve_client_ip` trusts `CF-Connecting-IP` for auth logs, which is only sound while the origin is locked.
- Verify a lock by going around the edge (the `--resolve` curl), not only through it.

Discovered 2026-09-11 during the M7 R2 cutover smoke checks. Rollout and rotation: `infra/cloudflare-state.md` → *Transform Rules — origin lock*.

## `fly deploy` leaves an already-stopped machine stopped

A deploy updates every machine's image, but a machine that was stopped beforehand stays stopped — no `start` event, no app log line beyond "Configuring firecracker". Nothing in `fly deploy`'s output says a process group is down, and a process group with no `[[services]]` (the Celery `worker` and `beat`) has no health check to fail either.

- **After every deploy, run `fly status -a <app>` and confirm every process group is `started`.** `fly scale show` is not a substitute: it counts machines, including stopped ones.
- Give background process groups `[[restart]] policy = "always"`. The default is `on-failure`, which leaves the machine down after a clean exit or a platform-initiated stop.
- A dead worker is silent by construction: the API keeps serving, beat keeps queueing, and the jobs pile up in Redis. Surface it in the UI (see the sync-freshness dot in `ICloudSettings.jsx`), because no log line arrives to tell you.

Discovered 2026-09-11 during the M7 cutover: the `worker` machine had been stopped since at least the end of May. 32,136 scheduled jobs had queued in Upstash (103 days' worth), and iCloud sync plus the soft-delete purge had been dead that entire time.

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

### The visual-test stack and the integration suite share `todo_app_test` — do not run them at once

- `api-test` (visual-test profile) points `DATABASE_URL` at `todo_app_test` and runs
  `alembic upgrade head` + seeding at boot. The integration suite targets the SAME database via
  `TEST_DATABASE_URL` and manages schema itself with `Base.metadata.create_all`.
- Running `docker-compose exec api uv run pytest` while the visual stack is up (or immediately
  after it started, mid-migration) produces mass unrelated failures — observed once as
  **72 failed / 263 errors**, where the identical suite passed **878** minutes earlier and again
  immediately after. Individual files passed in isolation the whole time, which is the tell.
- **Rule:** treat a sudden full-suite collapse with healthy per-file runs as environment
  contention, not a code regression. Let the visual-test containers finish being removed, then
  re-run before touching any code. Do not "fix" tests against it.
- Discovered 2026-09-09 during M7 PR2 verification.

### Review-log fixtures must give every entry an explicit, ordered `ts`

- `review-log` stamps a real "now" on what it writes, and `reviews_for_plan` picks the latest
  entry per skill by `ts`, never by line position. A fixture that logs a later step with a
  hand-picked `ts` earlier than a CLI-written entry (a resolution stamped today, then a
  "re-run" dated last week) silently loses the tie: the resolution stays latest and the test
  asserts against the wrong state.
- **Rule:** in `.agents/tests` and the framework's `payload/tests`, pass `ts=` on every
  `log_review` call and `--field ts=` on every CLI write in the same test, in the order the
  story happens. Equal `ts` is fine (the later line wins) and is itself a case worth testing.
- Discovered 2026-09-16 while executing `workflow-review-resolution`: two fixture checks
  failed for this reason before any helper bug was suspected.

### Patch the factory, not the returned instance, when a getter constructs per call

- `app.storage.get_storage()` builds a **fresh** `LocalDiskBackend` on every call (it is cheap
  to construct). So `monkeypatch.setattr(get_storage(), "get", fake)` patches an object the code
  under test never sees, and the test passes for the wrong reason.
- Patch where the caller looks it up: `monkeypatch.setattr("app.routes.media.get_storage", lambda: fake)`.
- **Rule:** any test that asserts a dependency was NOT called needs a negative control proving
  the patch takes effect at all — otherwise "not called" and "not patched" are indistinguishable.
- Discovered 2026-09-09 in M7 PR2: a storage-unreachable test returned 200 instead of 503, and
  its sibling "malformed keys never reach storage" assertion could never have failed.

### HTTP clients normalize `../` out of URL paths — route-level traversal tests can be vacuous

- httpx (like every conforming client, per RFC 3986) resolves dot-segments before sending, so
  `GET /uploads/item-icons/../../app/main.py` never arrives at the server as a traversal. It
  arrives as a different path and 404s on no-route-match — with or without a validator.
- Percent-encoded traversal (`..%2f..%2f`) and empty segments (`/uploads//etc/passwd`, which
  arrives as the absolute key `/etc/passwd`) **do** reach the route. Those are the shapes worth
  asserting over HTTP.
- **Rule:** pin literal-traversal rejection in a unit test against the validator directly, where
  nothing normalizes the input, and keep route tests to shapes that survive transport. Verify
  empirically which is which rather than assuming.
- Discovered 2026-09-09 in M7 PR2 while writing the media read matrix.

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
| 2026-09-09 | Version a storage-cutover feature flag WITH THE CODE (`fly.toml [env]`), not as a platform secret, whenever the previous release also honors the flag. A secret survives a code rollback, so rolling back leaves old code + new flag — for M7 that means writing to R2 while reading from disk, the one combination that breaks every image. Versioning the flag makes rollback atomic and turns an operational hazard into a non-event. | recorded by /execute-plan (M7 PR2, user-approved) | branch prod-r2-storage |
| 2026-09-11 | Prove a request came through Cloudflare with a secret header set by a Transform Rule (`X-Origin-Verify` against the `ORIGIN_VERIFY_SECRET` Fly secret). Rejected: allowlisting Cloudflare's IP ranges (every tenant shares them, so another zone with its WAF off passes); Authenticated Origin Pulls (Fly's proxy terminates TLS, so the app never sees the client cert); Cloudflare Tunnel (largest change for the same result). App-layer `/auth/login` rate limiting stays deferred to v1.1: it is defense in depth and does not close the bypass. | recorded by /quickfix (user-approved) | branch quickfix/origin-verify-header |
| 2026-09-15 | A review gate must distinguish "never ran" from "ran and did not pass", and every status word gets one meaning across all skills. The industry's waiver conventions transfer only in part: scoping an exception to one control and recording who cleared it and why do transfer (a resolution names the review it closes, a resolver that actually ran later and passed, and where the items are closed), and so does separation of duties (a review never clears itself). Dismissal-on-change does not: every review edits the plan by design, so content-change invalidation would void each resolution as soon as the next review saved — superseding a plan already resets its dashboard. Expiry does not fit plans that live days. And no status may mean "skipped counts as success": an unreadable or unknown status reads as failed. | recorded by /office-hours | branch workflow-review-resolution |
| 2026-09-16 | An ordering rule over second-resolution timestamps compares with `>=`, never `>`: one skill step writes two log entries in the same second (the review log holds ten such pairs), so "the resolver ran after the failure" must admit equality or the natural case is rejected every time. And a reader that skips unparseable lines silently is a gate that opens on a merge conflict — report the count and fail closed. | recorded by /plan-eng-review | branch workflow-review-resolution |
| 2026-09-15 | A fail-silent wrapper around a fail-closed check is an open gate: the session banner catches every exception and prints nothing, so if unreadable-log handling raises instead of returning a count, the only control the operator does not check goes blank and the agent proceeds. Return the failure as data (a count, a verdict) and render it; reserve fail-silent for unexpected crashes. Mixed versions of the four review-gate helpers (`_lib.py`, `workflow-state`, `review-log`, `review-read`) are worse than staying on the old version: new `review-log` against old `_lib` crashes, and new `review-log` against old `workflow-state` re-opens the gate. Upgrade those four together or not at all. CLI validation that inspects `args.status` before `--field` is applied is not validation: `--field status=clean` smuggles a passing write past every resolver rule. Validate the merged entry. | recorded by /plan-adversarial-review | branch workflow-review-resolution |
