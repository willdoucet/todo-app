# Review Checklist

<!-- guidance: Assembled, not written. init-project concatenates one snippet per chosen
technology from `.agents/templates/checklists/*.md` below the marker at the end of this file, in
stack order: backend framework, ORM, migrations, validation, jobs, cache, database, frontend
framework, build tool, styling, data layer, router, test runners, containers, CI. Each snippet is
headed `## <Technology>` with checks grouped under the categories listed here. When a technology
has no snippet, draft one in the same shape and offer it back to the templates directory.
/review-implementation and /final-review run every check that applies to the diff; a check is
one line a reviewer can answer yes or no. When a review finds a repeatable class of bug, add a
check to the matching snippet, not a paragraph to LESSONS.md. -->

Stack: FastAPI · SQLAlchemy 2 (async) · Alembic · Pydantic v2 · Celery · Redis · PostgreSQL 16 · React 19 · Vite 7 · Tailwind CSS v4 · TanStack Query · React Router 7 · Vitest · pytest · Playwright · Docker Compose · GitHub Actions

## Categories

Every snippet groups its checks under these headings, in this order, omitting any that do not apply.

### Data & migrations
Schema changes, migration safety and reversibility, constraints that back business rules, soft-delete filtering.

### API & trust boundaries
Auth on every non-public route, input validation at the edge, identical failure bodies, nothing secret in a response.

### Background jobs
Idempotency, retries, transaction boundaries around enqueue, event-loop and connection hygiene.

### Query efficiency
Eager loading for what the response touches, indexes for new query shapes, locks held for the whole unit of work.

### Rendering & state
Async states, form structure, effect cleanup, optimistic updates, where tokens live.

### Styling & accessibility
Tokens over literals, light/dark pairing, motion that survives the build and honors reduced motion, focus and targets.

### Testing
The invariant a bug violated has a test; structural tests for cross-cutting guarantees; isolation between tests.

### Secrets & config
Env from one place, nothing secret reaches the client bundle or the transcript, production fails closed.

### Operations
Health checks, non-root containers, writable paths, graceful shutdown, CI parity with local commands.

---

<!-- snippets appended below -->

## FastAPI

### API & trust boundaries
- Every new router is included on the protected router (or its auth dependency is explicit); the public surface is enumerable with one grep of `include_router` in `main.py`.
- `/docs`, `/redoc`, and `/openapi.json` are disabled or explicitly gated; router-level dependencies do not cover them.
- Credential and token failures return one status with a byte-identical body; only body-shape errors return 422.
- Validation `detail` is an array of `{loc, msg, type}`; no caller renders it raw.
- New write paths send the same required fields as the established path for that entity (no shortcut endpoint that 422s).
- CORS origins come from env; never `*` when `APP_ENV=production`.
- Production-only host or origin gate returns a distinct status (e.g. 421) and is disabled in dev and test.
- A route gated by something OTHER than `get_current_user` (a cookie guard, a signed token) carries its own structural assertion that it still has that guard; an exemption in the auth-propagation test never stands alone.
- No response header is built from an unvalidated path or query parameter. Starlette encodes header values as latin-1, so a non-latin-1 value is an unhandled 500 — validate first, then build headers from the already-allowlisted value.

### Query efficiency
- List endpoints eager-load every relationship the `response_model` touches; no lazy load fires during serialization.
- Any list that can grow unbounded has pagination or a hard cap.

### Error handling
- 404 for missing, 409 for unique-constraint conflicts (catch `IntegrityError`), 400 for business-rule rejections, 422 left to Pydantic.
- Custom exceptions map to statuses in one place; handlers never leak stack traces.
- Conditional requests (`If-None-Match` / `If-Modified-Since`) are evaluated only after the key is validated AND the representation is known to exist; a 304 for something that does not exist is both non-conformant and a stale-cache trap.
- A 401 raised from a *dependency* on a route whose URLs end in a cacheable extension (`.png`/`.jpg`/`.webp`) must still carry `Cache-Control: private, no-store`. The route body's error-header helper never runs for a dependency failure, and Cloudflare caches by extension.
- A response meant to be revalidated (ETag + `no-cache`) never carries `Vary` on a header that rotates — `Vary: Cookie` with a rotating session cookie makes the browser discard the cached entry *and its validators* on every rotation, turning every 304 back into a full download. `private` already keeps it out of shared caches.
- A dependency-unavailable status (503) is mapped from specific storage/network exception classes, never a bare `except Exception` — otherwise our own `TypeError` pages someone about a third-party outage.

### Secrets & config
- Lifespan fails closed in production when a required secret is missing and logs a clear bootstrap warning in development.
- Settings are loaded once from env; tests configure them directly instead of reading the process environment.

### Operations
- `/healthz` is public, cheap, and reports the deployed version.
- Every auth-related request emits exactly one structured log line with event, outcome, reason, sanitized ip, request id, and latency; never a credential.

### Testing
- A structural test walks `app.routes` and asserts every non-allowlisted route carries the auth dependency and the docs routes are absent.
- A behavioral test asserts 401 without a token and with a malformed bearer, and 200 on the public surface.

## SQLAlchemy

### Data & migrations
- Enum columns return enum members, not strings; comparisons use the enum, never a raw string.
- A new NOT NULL or boolean column on an existing table is backfilled in the migration, or the read schema tolerates NULL until it is.
- Soft delete: every read goes through one shared statement builder that filters `deleted_at IS NULL`; uniqueness is a partial index `WHERE deleted_at IS NULL`.
- Every FK relationship declares its delete behavior deliberately (CASCADE / SET NULL / RESTRICT) and the docs say which.
- Self-referential FKs that form chains use `use_alter=True` and SET NULL so rows can be deleted.

### Query efficiency
- Relationships the response touches are `selectinload`ed in the query builder; no per-row lazy loads in a list endpoint.
- `with_for_update()` locks are held for the whole unit of work; no per-iteration flush or commit releases the lock mid-loop.
- New query shapes have a supporting index; the migration adds it.
- Engine `echo` is env-gated and defaults to off; `echo=True` is never committed.

### Background jobs
- Async engine used from a sync entry point (job worker, CLI) gets a fresh event loop per call and disposes the engine before the loop closes; pooled connections must not span loops.
- `pool_pre_ping=True` where the provider drops idle connections.

### Secrets & config
- Async drivers use the `+asyncpg` (or equivalent) scheme; `sslmode=` is not a valid asyncpg kwarg (use `ssl=`); internal-network endpoints without TLS need `ssl=disable` explicitly.

### Testing
- Integration tests target `TEST_DATABASE_URL`, never the dev database.
- SAVEPOINT-based isolation does not reset sequences; tests that assert ids reset sequences after `create_all`.
- Session-scoped engines set the pytest-asyncio fixture and test loop scopes to `session`.

## Alembic

### Data & migrations
- Autogenerate output is reviewed by hand: it misses enum value changes, partial indexes, CHECK constraints, server defaults, and CITEXT.
- Type conversions PostgreSQL cannot cast implicitly carry an explicit `postgresql_using=`.
- Every revision has a real `downgrade()`; a destructive drop's downgrade recreates the table (empty is acceptable after an archive window, and the docstring says so).
- Multi-instance deploys use expand/contract: add nullable → backfill → add constraint; never rename a column in place.
- Archive-then-drop: a legacy table kept read-only for a soak window gets a dated TODOS.md item to drop it.
- Data migrations are idempotent, batched, and never import ORM models (schema drift breaks old revisions).
- `alembic heads` shows exactly one head before shipping; branches are merged.

### Operations
- Migrations run on container start or as an explicit release step, never both; development-commands.md says which.
- Inside a container exec session the virtualenv path may be needed explicitly (`.venv/bin/alembic`).
- The migration that ships with a release is listed in RUNBOOK.md with its reversibility.

### Testing
- CI applies `upgrade head` to an empty database and `downgrade base` back on every PR that adds a revision.
- A test asserts the models and the migrated schema agree (autogenerate produces an empty diff).

## Pydantic

### Data & migrations
- A field whose name matches a type in its own annotation (`date: Optional[date]`) aliases the import (`from datetime import date as _Date`).
- Schemas follow Base / Create / Update / Read; Update has all-optional fields and omits immutable discriminators (a `type` column is not patchable).
- Cross-field rules (XOR, "one of A or B required", end after start) live in a `model_validator(mode="after")` AND a DB CHECK constraint.
- String fields carry `min_length` / `max_length` matching the column; numeric fields carry bounds; the same limits appear in APP_FLOW.md → Form Validation.
- Read models set `from_attributes=True`; nested detail models are `Optional` with `None` default so old rows still serialize.

### API & trust boundaries
- Read models never expose hashes, tokens, encrypted blobs, or internal flags; the ORM model is never the response type.
- Validator error messages are the exact strings the UI shows or maps; changing one updates APP_FLOW.md.
- Overlong inputs are rejected by length before any expensive work (hashing, parsing) runs on them.

### Testing
- One test per validator branch, including the message text.
- One test that an old row shape (missing optional fields) still passes the Read model.

## Celery

### Background jobs
- Every task is idempotent: redelivery after a worker crash produces the same end state.
- Tasks receive ids, not ORM objects, and re-fetch inside the task.
- Async DB from a task: a fresh event loop per invocation, engine disposed before the loop closes ("Future attached to a different loop" is the symptom of skipping this).
- Retries set `max_retries` and a backoff; a poison message cannot loop forever.
- Enqueue happens after the surrounding DB transaction commits, never inside it.
- Beat entries derive from `conf.beat_schedule`; the persistent schedule file is on a writable path (`--schedule=/tmp/...`) so non-root containers do not crash in `setup_schedule()`.

### Secrets & config
- A `rediss://` broker URL requires `broker_use_ssl` and `redis_backend_use_ssl` with `ssl_cert_reqs`; a plain `redis://` URL must not set them. Gate the SSL config on the URL scheme so one config boots locally and in production.
- `CERT_REQUIRED` against the system CA bundle; `CERT_NONE` only with a written reason.

### Operations
- Worker and beat are separate processes; exactly one beat instance runs anywhere.
- Task failures log the task id and arguments (never secrets) and are visible in the worker log.
- Sync intervals and sweep schedules are documented in BACKEND_STRUCTURE.md → Background Job Pattern.

### Testing
- Tests call the task function directly or run eagerly; nothing outside `integration/` depends on a live broker.

## Redis

### Data & migrations
- Keys are namespaced (`app:feature:id`) and every key has a TTL or a comment saying why it must not.
- Check-and-set patterns use `SET NX`, a Lua script, or `WATCH`/`MULTI`, never read-then-write.
- Values are versioned or self-describing so a deploy can change the shape without a flush.

### Secrets & config
- The URL comes from env; hosted instances use `rediss://` with certificate verification.
- Local and production URLs differ only in scheme and host; the app tolerates both.

### Operations
- The eviction policy is known and the app survives a miss on every cached key.
- The connection pool is sized to the worker count and closed on shutdown.
- A Redis outage degrades (no cache, queued jobs wait) rather than 500s the request path.

### Testing
- Tests use a fake client or a dedicated database index and never `FLUSHALL` a shared instance.

## PostgreSQL

### Data & migrations
- Every FK declares its delete behavior and the ERD shows it.
- Every business rule that Pydantic checks across fields also has a CHECK constraint.
- Uniqueness among soft-deleted rows uses a partial unique index.
- Timestamps are `timestamptz`; the application timezone comes from a settings row or env, never the container clock.
- Case-insensitive uniqueness (emails) uses CITEXT or a functional index, not app-side lowercasing.

### Query efficiency
- New query shapes have a supporting index; `EXPLAIN` on a realistic data size shows no sequential scan on a large table.
- "Only one may exist" races (singleton registration) use a transaction-scoped advisory lock.
- Rotation chains and counters use `SELECT ... FOR UPDATE`, not optimistic retries.
- Unbounded JSONB columns have a size expectation written down.

### Secrets & config
- Connection strings printed by a provider are reshaped for the driver: scheme, `ssl=` not `sslmode=`, explicit `ssl=disable` on internal endpoints without TLS.
- `pool_pre_ping` is on when the provider drops idle connections.

### Testing
- Sequences advance on rolled-back inserts; tests that assert ids reset them per test.
- A separate test database is created by an init script; `TEST_DATABASE_URL` is never the dev URL.

### Operations
- The backup/restore drill in RUNBOOK.md has been run at least once against a scratch database.

## React

### Rendering & state
- No nested `<form>` elements; an inner submit-like action uses a `<div>` with a button `onClick` and input `onKeyDown` Enter handler, and both call `preventDefault()` and `stopPropagation()`.
- Async UI has loading, empty, and populated states; empty-state guards are gated on `initialLoaded` so they never flash during load.
- No ref mutation during render (Strict Mode double-renders).
- A `useEffect` cleanup that cancels timers keyed to state does not re-run on every state change; when cleanup is unmount-only, the dep array is `[]` with a ref mirror.
- Optimistic updates revert on error and show a toast; the rollback path has a test.
- Contextual ids (`section_id`, `parent_id`) are threaded from UI state into the submit payload; a new write path sends every field the established path sends.
- Nested click targets call `stopPropagation()` so a row click does not fire under a button.
- API validation `detail` arrays are normalized before reaching a toast or an error banner.
- Polling (`setInterval`, `refetchInterval`) is conditional and stops when the pending state clears.

### Styling & accessibility
- Every interactive element has a visible focus ring; icon-only buttons carry `aria-label`; touch targets reach 44px.
- Dialogs trap focus and restore it on close; Escape closes them.

### Secrets & config
- Access tokens live in memory (module scope + `useSyncExternalStore`), never `localStorage` or `sessionStorage`.

### Testing
- The invariant a bug violated has a behavior-level test (one delete removes exactly one card), not a class-name assertion.
- A console error seen during live edits is checked against a clean reload before it is treated as a bug (HMR serves in-between versions).

## Vite

### Secrets & config
- Only `VITE_`-prefixed variables reach the client bundle; nothing secret is ever `VITE_`-prefixed.
- Exactly one module reads `import.meta.env` for the API base URL; every caller imports from it.
- A production build throws when the API base URL is unset instead of silently falling back to localhost.

### Rendering & state
- HMR artifacts are recognized before debugging: a stack line number larger than the file, a `?t=` cache-buster in the URL, or a "useEffect changed size between renders" warning means reload first.

### Operations
- End-to-end and visual suites run against `vite preview` (the production build), never the dev server.
- Chunk-size warnings are reviewed; heavy dependencies (emoji pickers, editors, charts) are lazy-loaded.
- `node_modules` inside a container uses an anonymous volume so host and container installs do not collide.

### Testing
- `build` runs in CI as its own step, with the production env shape.

## Tailwind CSS

### Styling & accessibility
- v4: custom `@keyframes` live inside `@layer base` and custom classes are `@utility` directives; unlayered custom CSS is tree-shaken silently (class present in the DOM, `animation-name: none` in computed style).
- `animate-in`, `fade-in`, `zoom-in-*`, `slide-in-*` do nothing without `tailwindcss-animate`; the plugin is confirmed in `package.json` before those classes are used.
- Tokens are defined once in `frontend/src/index.css` via `@theme`; no hex literal appears in a component.
- Light and dark classes are paired on the same element (`bg-card dark:bg-...`).
- Before theorizing about a variant, the stylesheet is searched for handwritten rules on the same element or a reused stale class name.
- Motion honors `prefers-reduced-motion` via `motion-reduce:` or a media query on every animated element.
- `ml-auto` is used instead of `justify-between` when the left child of a row may mount late.
- Mount and unmount animations use the component library's transition primitive; `transition-*` utilities alone do nothing on mount.

### Testing
- Motion is verified in the browser (computed `animationName`, keyframe present in `document.styleSheets`), not by asserting a class name.
- A visual or geometric test locks in layout invariants that hover or animation must not shift (header x, grid width).

## TanStack Query

### Rendering & state
- Query keys are arrays containing every variable the fetch depends on.
- Mutations invalidate or set the affected keys in `onSuccess`; optimistic updates snapshot in `onMutate` and roll back in `onError`.
- 401 handling lives once in `QueryCache` / `MutationCache` and triggers a single redirect, not per caller.
- Dependent queries use `enabled`; no fetch runs with an undefined parameter.
- `refetchInterval` is a function that returns `false` once the pending state clears.
- Boot-time data (auth status) is loaded by a router loader or a top-level query, not by every page.

### Query efficiency
- `staleTime` is set deliberately per query; heavy lists disable `refetchOnWindowFocus`.
- Lists and details share a normalized key prefix so one invalidation covers both.

### Testing
- Tests wrap components in a fresh `QueryClient` with `retry: false`; no client is shared across tests.
- The rollback path of every optimistic mutation has a test.

## React Router

### Rendering & state
- Data router: auth gating is a loader on a pathless protected layout that runs once; new pages go under it unless APP_FLOW.md marks them public.
- `HydrateFallback` and an `errorElement` exist for the boot sequence; a non-401 boot failure shows a retry, not a blank page.
- The router instance is set once and late-bound for redirects triggered outside components (HTTP client, query cache).
- Nested feature routes are owned by the feature's page shell, not the root route table.

### API & trust boundaries
- `return_to` and similar redirect targets are validated as same-origin relative paths (open-redirect defense) before navigation.
- Route params are validated before use; unknown routes render a 404 page.

### Testing
- Route tests render through a memory router so loaders, redirects, and error elements run.
- One test proves an unauthenticated visit to a protected route lands on the sign-in route with the original path preserved.

## Vitest

### Testing
- Network is mocked with MSW; handlers are reset between tests; no unit test reaches a real API.
- Timers are faked for debounce, undo countdown, and polling tests, and restored afterwards.
- Test placement follows FRONTEND_STRUCTURE.md (co-located or under `tests/`); files are named `<Component>.test.<ext>`.
- Regression tests are named for the bug and assert the invariant (one delete removes exactly one item), not the implementation.
- No test depends on order; stores, contexts, and `localStorage` are reset in `beforeEach`.
- Strict Mode is on in the test renderer so render-time side effects surface.
- CI runs the single-run command, not watch mode; coverage thresholds live in the config file.
- A behavior that a class-name assertion cannot prove (animation, layout shift) gets a browser-level test instead.

## pytest

### Testing
- Unit and integration suites are separate directories; integration tests require the test database and say so with a marker.
- Fixture scopes are deliberate: session-scoped engines pair with session loop scope for async fixtures and tests.
- Global state installed at more than one scope: the broadest install is a function-scoped autouse fixture so it re-installs after any narrower per-test reset.
- Tests that assert ids reset sequences after `create_all`; rolled-back inserts still advance sequences.
- Code that tests exercise with a hand-built `argparse.Namespace` reads flags via `getattr(args, "flag", default)`.
- Tests assert response bodies and side effects (rows written, jobs enqueued, files stored), not only status codes.
- Cross-cutting guarantees (auth on every route, docs disabled) have a structural test alongside the behavioral one.
- Tests run through the command policy in development-commands.md; the CI command is identical to the local one.
- Byte-identical failure responses have a test that compares bodies across every failure reason.

## Playwright

### Testing
- Runs against the production build (`preview`) in a container with pinned fonts, never the dev server.
- Auth is handled in global setup (login-or-register a synthetic user); the cached token file is git-ignored; `context.route()` stubs the refresh endpoint instead of a production bypass flag.
- Geometric assertions (bounding boxes stable across hover / rest / exit) come before pixel diffs; pixel diffs have a tolerance and a written baseline-bump rule.
- Every spec waits on a state (`expect(...).toBeVisible()`), never a fixed sleep.
- The flake protocol is written down: rerun once, then quarantine with a TODOS.md item; the suite stays informational in CI until it has soaked.
- Reports, traces, and screenshots are git-ignored and uploaded by CI on failure only.
- A mobile project covers the views that only exist below the mobile breakpoint.
- Test data is created and deleted by the spec; no spec depends on another's leftovers.

## Object storage (Cloudflare R2 / boto3)

### Secrets & config
- Production builds the configured storage backend in the lifespan hook, so a *missing* `R2_*` secret crashes the boot and the previous image keeps serving; it never boots green and 503s every read. (A present-but-rotated credential is not caught at boot — client construction makes no network call — so the cutover runbook's smoke upload stays mandatory.)
- The boto3 client carries explicit `connect_timeout` / `read_timeout` and bounded retries; the defaults (60 s + 60 s, up to 5 attempts) can pin a pooled DB connection for minutes when the request holds one across the call.
- A request that holds a DB session across a storage call ends its transaction first (`await db.commit()` after the last read — never `close()` or `rollback()`, which the SAVEPOINT test wiring cannot absorb) so a slow object store cannot exhaust the connection pool and take unrelated routes down with it.
- The storage-cutover flag (`STORAGE_BACKEND`) is versioned with the code (`fly.toml [env]`), not a platform secret, so a rollback reverts reads and writes together.
- Nothing constructs the boto3 client outside production: dev, CI and the visual-test stack stay on the local backend, and the test suite pins `STORAGE_BACKEND=local` in an autouse fixture so a developer's `.env` can never point pytest at the production bucket.

### API & trust boundaries
- Every key reaching `storage.get` / `storage.delete` has already passed the one canonical validator (`storage/keys.py`); a second regex anywhere else is a finding.
- The content-type served comes from the manifest row written at upload, never from the object store or the client.

### Error handling
- Only genuine storage failures (`botocore` `ClientError` / `BotoCoreError`, `OSError`, `TimeoutError`) map to `503 storage_unavailable`; anything else raises a real 500 so ops is not sent to the Cloudflare dashboard for a Python bug.
- A missing object (`ObjectNotFound`) is a 404 distinct from the 503, and the 503 is logged with a marker ops can grep.

### Background jobs
- Every boto3 call goes through `run_in_threadpool`; boto3 is synchronous and must never run on the event loop.
- A write is storage-first with a compensating delete on DB failure (catching `BaseException`, so a client disconnect after `put` still reclaims the object); a failed compensating delete is logged loudly because the sweep cannot see a row-less orphan.
- `delete` is idempotent and post-commit only; a rolled-back entity write never erases a still-referenced object.

### Testing
- `R2Backend` is covered with `moto` in-process; no test needs network or credentials.
- A test that asserts storage was NOT reached has a negative control proving the patch took effect (`get_storage()` constructs per call — patch the factory, not the returned instance).

## Docker Compose

### Operations
- Every service has a healthcheck; dependents use `depends_on` with `condition: service_healthy`.
- The dev build target mounts source for reload; the prod target runs as a non-root user with no test dependencies.
- Anything that writes to its working directory (schedulers, caches) has a writable path under the non-root user.
- Optional stacks (visual tests, load tests) sit behind `profiles` so the default `up` stays fast.
- `node_modules` uses an anonymous volume so host and container installs do not collide.
- The test database is created by an init script on first run; `TEST_DATABASE_URL` is distinct from the dev URL.

### Secrets & config
- `.env` is git-ignored; `.env.example` lists every variable with a generation command and never a value.
- Inspecting a container's environment uses names-only or existence-check filters on the container side; `exec <svc> env` is never run bare.

### Testing
- The exact `exec` / `run --rm` commands live in development-commands.md and are the ones CI runs.
- After a model or schema change the API container is restarted when hot reload does not reflect the runtime state.

## GitHub Actions

### Operations
- `doc-guard` runs on every pull request with `fetch-depth: 0` so the base range resolves.
- Every job runs the same command as development-commands.md; there is no CI-only code path.
- A `concurrency` group cancels superseded runs; every job has `timeout-minutes`.
- Actions are pinned to a major version or a SHA; `permissions` is minimal (`contents: read` unless a job needs more).
- Required checks have stable job names; new suites stay informational until they have soaked flake-free.
- Test artifacts are uploaded on failure only.

### Secrets & config
- Secrets are referenced as `${{ secrets.NAME }}` and never echoed; no step runs `env` or `printenv` bare.
- One-time CI secrets (a test encryption key) are documented with their generation command in development-commands.md.
- Forked pull requests do not receive secrets; jobs that need them are skipped or gated, not failed.

### Testing
- The matrix is limited to versions the project actually supports.
- No test depends on a container-only path (`/app/...`). CI runs on a bare runner, so such a path is supplied through the job's `env:` block the way `UPLOAD_DIR` and `STOCK_ICONS_DIR` are, or the test does not belong in the CI suite.

## Framework helpers (Python CLIs)

### Data & migrations
- A line-oriented reader and its writer agree on what a line boundary is: `json.dumps(ensure_ascii=False)` leaves U+2028, U+2029 and U+0085 raw and `str.splitlines()` honours them, so a value carrying one splits the record on read; escape them on write or split on `\n` only.
- Every value a reader orders or compares by (a timestamp, a sequence number) is validated on write for type and format and is never dated ahead of the clock that writes it; readers coerce rather than raise, because a fail-silent banner turns an exception into an open gate.
- A waiver or resolution record names the item it clears, and the reader checks that name against later failures instead of trusting the newest line; a union merge can put an older failure behind a newer resolution. The reader also applies the same resolver-eligibility rule the writer enforces, so a line the CLI would have rejected cannot open a gate.

### API & trust boundaries
- A CLI validates the merged input (flags, positional JSON, `--field`), never one source alone, and refuses fields that are computed on read or filled by the tool.
- Enumerated names (skills, tiers, statuses) are validated on write against the one list the readers use; a typo is refused with the valid names, never written silently.

### Testing
- Every rejection has a test in each input form, and each asserts the store is byte-identical afterwards.
- Fixtures give every entry an explicit, ordered timestamp so a real "now" cannot outrank a hand-dated later step (LESSONS.md → Test isolation gotchas).
