# Execution Summary — M7 `prod-r2-storage`

Plan: [prod-r2-storage-plan-20260715-201232.md](./prod-r2-storage-plan-20260715-201232.md)
Test artifact: [../../testing/prod-r2-storage-test-artifact.md](../../testing/prod-r2-storage-test-artifact.md)
Started: 2026-09-08
Executor: /execute-plan (Claude Code, Opus 4.8)

## Obsidian workflow
- `plan-metadata-get` → `metadata: {}` → **NOT an Obsidian-workflow plan.** No registry/note sync steps apply.
- design-sync-check: CLEAN (synced 2026-05-08, design files unchanged).

## Reviews complete before execution
- Eng review (2026-07-22): ✅ clean — Fork 3 kept, A1/A2/CQ1/T1 resolved, 0 critical gaps.
- Adversarial review (2026-08-10, GPT-5.5 in Cursor): ✅ done — hardened key validation, lifecycle ordering, rollback plan; 1 medium (PR2 rollback awkwardness — a PR2 concern).

## Scope of PR1 (Foundation)
All environments (incl. prod) stay on `LocalDiskBackend`. The `/uploads` StaticFiles mount is
UNTOUCHED (removed in PR2). R2 enablement + the cookie read-proxy + ETag are PR2. PR1 lands the
storage seam, the manifest, hardened validation, the orphan-lifecycle hooks, and the sweep — all
verifiable end-to-end on local disk.

### Assumptions (surface before coding — correct now or these hold)
1. **`R2Backend` ships in PR1** (built + moto-tested) but stays **disabled**; `STORAGE_BACKEND`
   defaults to `local` everywhere. The enable-flip is PR2.
2. **`assets` rows are written in PR1 but not yet READ** — no read path consumes them until PR2's
   proxy. Populating now is forward-prep so PR2 has a manifest. Harmless on local disk.
3. **Orphan-lifecycle hooks activate in PR1.** Today, replacing an icon orphans the old file on
   disk; PR1 starts deleting it (via `LocalDiskBackend.delete`). Intended — the whole point.
4. **GIF rejection activates in PR1** (the one intended user-facing change).

## Step plan

> **Reconciled 2026-09-09** — all nine boxes below shipped in PR #41 (`23d02ef`, on
> `master`). Evidence: registry `pr: "#41 (PR1)"`; `git log master..HEAD` empty (branch
> recreated from master for PR2); code present on disk (`app/storage/`,
> `app/services/asset_lifecycle.py`, `Asset` + migration `b7e2c9a4f1d8`); plan REVIEW
> REPORT verdict "CLEARED — PR1 ready to land" after two clean code reviews.
> The boxes were stale bookkeeping, not unfinished work.
- [✓] **S0 — Deps.** `boto3` (main) + `moto` (dev/test) via `uv`. Note in TECH_STACK.md.
- [✓] **S1 — Storage abstraction.** `app/storage/`: `base.py` (Protocol), `local.py`, `r2.py`
      (boto3 + `run_in_threadpool`), `__init__.py` (env factory, default `local`). Tests (moto for R2).
- [✓] **S2 — `assets` table.** `Asset` model + Alembic migration. Cols: `key` PK text,
      `content_type`, `size_bytes`, `created_at`, `referenced` bool (server_default false).
      Index `(referenced, created_at)`.
- [✓] **S3 — Unified validator.** `validate_and_read(file, *, max_bytes, subdir)` — streaming-abort
      reader, magic-byte PNG/JPEG/WebP, reject GIF/SVG/fake. Delete weak `save_upload`. Tests.
- [✓] **S4 — Upload endpoints.** 4 types → validate → `storage.put` → INSERT assets(referenced=false)
      → return `/uploads/{key}`; compensating `delete` on DB failure (+ log if delete also fails).
      Tests incl. failure injection.
- [✓] **S5 — Lifecycle hooks.** Adopt/replace/delete on the 4 entity write paths + `stock_icons/*`
      carve-out (no ref flip, no delete). Tests incl. A1 duplicated-key out-of-scope doc test.
- [✓] **S6 — Abandoned-upload sweep.** Celery beat task (reuse `run_async` + engine dispose per
      LESSONS): delete assets rows + objects where `referenced=false AND created_at<now()-24h`. Tests.
- [✓] **S7 — `echo=True` env-gate.** `database.py` → `SQLALCHEMY_ECHO` env. Mark TODOS.md done.
- [✓] **S8 — Full suite + docs.** `docker-compose exec api uv run pytest`; update BACKEND_STRUCTURE,
      TECH_STACK, IMPLEMENTATION_PLAN status, env docs. Final summary.

## Progress log
- **S0 ✅** `boto3>=1.35` (main) + `moto[s3]>=5.0` (test) added to `backend/pyproject.toml`. Needs `docker-compose build` to sync.
- **S1 ✅** `app/storage/` written: `base.py` (Protocol + `ObjectNotFound`), `local.py` (`LocalDiskBackend`, root-injectable), `r2.py` (`R2Backend`, boto3 + `run_in_threadpool`, env fallback to the M2 names `R2_ENDPOINT`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`/`R2_BUCKET_NAME`), `__init__.py` (`get_storage()` env factory, default `local`, R2 client cached).
- **S2 ✅** `Asset` model appended to `models.py` (key PK, content_type, size_bytes, referenced bool default false, created_at) + migration `b7e2c9a4f1d8_add_assets_table.py` (down_revision = head `cf4f8428948e`), index `(referenced, created_at)`.
- **Map facts:** 4 byte-writers only (recipe_extractor extracts an EXTERNAL image_url, no bytes). items = soft-delete → asset cleanup hooks the hard-delete sweeper (`crud_items.py` L81), not the DELETE route. responsibilities.update does NOT prefetch old row → must add prefetch for the replace hook. Test rewrites needed: test_uploads.py (unit) + test_uploads_api.py (integration) use fake bytes + expect GIF pass / 400 — incompatible with magic-byte validation. test_item_icon_upload.py already magic-byte-aware (keep).
- **S3 ✅** `app/utils/upload_validation.py` — `validate_and_read(file, *, max_bytes)` (streaming-abort, magic-byte PNG/JPEG/WebP, GIF/SVG/fake → 415, `HTTP_413_CONTENT_TOO_LARGE`). Old `item_icon_upload.py` deleted.
- **S4 ✅** `app/uploads.py` rewritten to `store_upload(db, file, subdir, *, max_bytes)` — validate → put → INSERT assets(referenced=false) → compensating delete on DB failure. `routes/uploads.py` rewired (4 endpoints, `Depends(get_db)`, ICON_MAX=1MB / PHOTO_MAX=5MB). Old weak `save_upload` gone.
- **Deps locked:** `uv.lock` updated via standalone uv image (boto3 1.43.90, moto 5.2.3 + transitive). api image rebuilt.
- **✅ VERIFIED (S0–S4):** migration `cf4f8428948e → b7e2c9a4f1d8` applied cleanly on api boot; **38 tests pass** (`test_storage` 6 [LocalDisk + R2/moto], `test_upload_validation` 12, `test_uploads_api` 15 [incl. GIF-rejected, 1MB icon cap, assets-row written, compensating-delete-no-orphan], `test_item_icon_upload` 5). moto gotchas resolved: use `with mock_aws()` context (not class decorator) + AWS-hostname endpoint.
- **S5 ✅** `app/services/asset_lifecycle.py` — `managed_key` (stock/external → unmanaged), `adopt` (referenced=true, in-txn), `release` (delete + drop row, post-commit), `release_if_replaced`. Wired into `crud_responsibilities` (create/update/delete), `crud_family_members` (create/update/delete), `crud_items` (create_item, update_item icon+recipe image, and the hard-delete sweeper). `stock_icons/*` carve-out; post-commit delete ordering (adversarial).
- **S6 ✅** `sweep_abandoned_uploads` (asset_lifecycle) + Celery task `app.tasks.sweep_abandoned_uploads` + hourly beat entry. Deletes referenced=false rows aged >24h (naive-UTC, matches item hard-delete convention).
- **S7 ✅** `database.py` echo env-gated (`SQLALCHEMY_ECHO`, default off). TODOS.md item marked DONE.
- **S8 ✅** docs: TECH_STACK (boto3 + moto[s3]), BACKEND_STRUCTURE (M7 storage layer section). IMPLEMENTATION_PLAN left unchanged (PR1 not merged — no premature status claim).

## ✅ VERIFICATION — FULL SUITE GREEN
- **`docker-compose exec api uv run pytest` → 743 passed, 3 skipped, 0 failed** (9.3s). No regressions in responsibilities/family_members/items/meal_entries despite the CRUD hook wiring.
- New tests: `test_storage` (6), `test_upload_validation` (12), `test_asset_lifecycle` unit (10) + integration (10 — adopt/replace/delete/stock-carve-out/sweep/A1-doc), rewritten `test_uploads_api` (15), `test_item_icon_upload` (5).
- Migration `b7e2c9a4f1d8` applied on api boot; single alembic head; all new modules import clean; sweep in beat schedule.
- Warnings: pre-existing `datetime.utcnow()` deprecations only (matched existing convention).

## STATUS: DONE — PR1 ready for review
All 8 steps complete + verified. NOT an Obsidian-workflow plan (no task-box sync).
**Behavior changes shipped in PR1 (both user-confirmed):** (1) GIF uploads rejected; (2) orphan-lifecycle deletes active on local disk (replace/delete/sweep). PR2 (R2 flip + cookie read-proxy + mount removal) is untouched.

**Next:** `/review-implementation` (first code review), then the Cursor `cursor-implementation-review` (final gate).

## Pre-landing review (`/review-implementation`, 2026-09-09) — CLEAN after fixes
Structured two-pass + LARGE-tier adversarial subagent (2044-line diff). Scope CLEAN.

**Fixed (verified):**
- **[CRITICAL] Path traversal → arbitrary file deletion.** User-controlled `icon_url`/`photo_url`/`image_url` flowed through `managed_key` (no validation) into `storage.delete`. A crafted `/uploads/../../app/main.py` or `/uploads//etc/passwd` (leading slash drops the root) on replace/delete deleted arbitrary files. **Fix:** `managed_key` now validates the exact `{subdir}/{uuid4}.{png|jpg|webp}` shape (→ None otherwise); `LocalDiskBackend._path` asserts `is_relative_to(root)` (defense-in-depth). Regression tests: `test_asset_lifecycle` (traversal→unmanaged, e2e clean lifecycle), `test_storage` (containment raises).
- **[MEDIUM] Sweep/adopt race.** `sweep` did SELECT→delete→DELETE (no `referenced` guard) — a key adopted mid-sweep got its live object reclaimed. **Fix:** atomic `DELETE ... WHERE referenced=false RETURNING key`, then storage-delete only claimed keys.
- **[INFO] Test gap** — added item recipe-image adopt + hard-delete-sweeper release tests; removed a dead `select` import.

**Accepted (documented single-family scope decisions, not defects):** A1 shared-key 1:1 invariant (eng-review), concurrent-update leak (plan: read-then-write races accepted), naive-UTC cutoff (matches codebase).

**Full suite after first pass: 760 passed, 3 skipped, 0 failed** (+17 tests over the pre-review 743).

## Cursor implementation review (2026-09-09) — CLEAN after fixes
Independent second pass + LARGE-tier Cursor adversarial subagent. Scope CLEAN (PR1 only).

**Auto-fixed:**
- Compensating delete now catches `BaseException` (client disconnect/`CancelledError` after `put`).
- Mandated "compensating delete also fails → logged" test.
- Unknown `STORAGE_BACKEND` raises instead of silently writing to local disk.
- `R2Backend.get` maps `ClientError` 404/NoSuchKey/NotFound → `ObjectNotFound` and closes the stream body.
- Docs: actual subdir names for PR2 allowlist, TECH_STACK env vars, `.env.example`, PRD GIF rejection.

**User-approved ASK items (applied):**
- Keep unreferenced `assets` row when storage delete fails (`release` + sweep `SELECT FOR UPDATE`, drop row only after successful delete).
- Adopt fail-closed (400) when a managed key has no manifest row.

**Full suite: 768 passed, 3 skipped, 0 failed.** Not an Obsidian-workflow plan (`metadata: {}`).

---

# PR2 — R2 + read cutover (atomic flip)

- Plan: [prod-r2-storage-plan-20260715-201232.md](./prod-r2-storage-plan-20260715-201232.md)
- Branch: `prod-r2-storage` (recreated from `master` @ `94022a1` after PR1 merged as #41)
- Started: 2026-09-09
- Executor: /execute-plan (Claude Code, Opus 5)
- Metadata (`plan-metadata-get`, verbatim): `{"metadata": {"milestone": "M7", "parent_epic": "v1-productionization", "plan_kind": "feature", "registry_key": "plan:prod-r2-storage", "updated_at": "2026-09-09T22:10:06Z"}, "plan_path": ".agents/plans/features/prod-r2-storage/prod-r2-storage-plan-20260715-201232.md", "status": "ok"}`
- Registry at start: `implementation_status: implementing`, `pr: "#41 (PR1)"`, `review_status: []`
- Correction to PR1's record: PR1 logged "NOT an Obsidian-workflow plan (`metadata: {}`)". True pre-migration; post-PR #42 the plan IS registry-tracked (`plan:prod-r2-storage`). PR2 syncs state through `obsidian-workflow`.
- No `## Inherited constraints` section — the plan predates that convention. Epic `v1-productionization` M7 of 8; not recreated.
- design-sync-check: not applicable (`modules.design_sync` — backend/infra plan, no UI scope).

## Scope

Enable `R2Backend` in prod (`STORAGE_BACKEND=r2`), add the cookie-checked `GET /uploads/{key}`
read proxy (incl. the `stock_icons/*` compat branch), **remove the StaticFiles mount**, and
resolve dev/test media-auth handling — all in one deploy. Ops (prod flip verification, OQ1 live
same-site check, CF Access Application 1 teardown) stays with the operator.

### Pre-merge gate owned by the operator (OQ1)
Live same-site verification in the real Cloudflare-proxied browser: confirm `SameSite=Strict`
`__Host-refresh` transmits on same-site `<img>` subresource loads from `mealy.dev` →
`api.mealy.dev`, and that CF does not edge-cache `/uploads/*` under `private, no-cache`. Cannot
be driven from this session; pytest coverage (A2 (a)) proves the route, not the browser.

### Finding surfaced before implementation
**Stock icons are already broken in prod.** `docker-compose.yml:28` copies
`/app/stock_icons_src` → `/app/uploads/stock_icons` at container start, but prod's `fly.toml`
`[processes] web` is bare `uvicorn` and the prod Dockerfile `CMD` is
`alembic upgrade head && uvicorn` — nothing populates `/app/uploads/stock_icons` in prod, so
`/uploads/stock_icons/*.png` 404s there today. PR2's compat branch reads them from
`/app/stock_icons_src` directly, which **fixes** this rather than risking it.

## Steps
- [✓] S1 — Extract `RefreshStatus` + `refresh_row_status(row, now)` (CQ1); refactor `service.refresh` onto it (2026-09-09 21:35)
- [✓] S2 — Read-only cookie media guard (matrix lands with S3, see notes) (2026-09-09 21:48)
- [✓] S3 — `app/routes/media.py`: `GET /uploads/{key:path}` proxy + rejection matrix (2026-09-09 22:10)
- [✓] S4 — Remove the StaticFiles mount, register the media router, update the structural surface test (compose copy → S8) (2026-09-09 22:10)
- [✓] S5 — T2 invariant tests: logout → image 401; the bump-without-revoke hazard pinned (2026-09-09 22:10)
- [✓] S6 — Visual-suite `context.route('**/uploads/**')` fixture shim (A2) (2026-09-09 22:38)
- [✓] S7 — `crossorigin`/fetch guardrail comments at the media router and the `apiUrl` seam (OQ6) (2026-09-09 22:40)
- [✓] S8 — Prod enablement config (`STORAGE_BACKEND=r2`) + PR2 cutover/rollback runbook (2026-09-09 23:05)
- [✓] S9 — Full suites + `/update-docs` (2026-09-09 23:40)

## Step notes

### S1 — shared validity predicate (CQ1)

**Files**
- `backend/app/auth/tokens.py` — added `RefreshStatus` (5 states), `REFRESH_STATUS_SERVES`
  frozenset, and the pure `refresh_row_status(row, now)`. `TYPE_CHECKING`-only import of
  `RefreshToken` so the module keeps no runtime model dependency.
- `backend/app/auth/service.py` — `refresh` steps 2-4 now branch on the predicate; the Case-B
  terminal liveness re-check does too.
- `backend/tests/unit/auth/test_tokens.py` — 10 new tests.

**Decisions**
- Home is `tokens.py`, not `service.py`: `REFRESH_TOKEN_GRACE_SECONDS` already lives there and
  the module is import-light, so the predicate stays pure and importable from the media guard
  without dragging in `service.py`'s DB machinery.
- Check order mirrors `service.refresh` exactly (revoked → expired → superseded) so the
  `bad_refresh_revoked` / `bad_refresh_expired` log reasons are unchanged. Two tests pin the
  precedence.
- Naive `now` raises `TypeError` rather than mis-classifying — every compared column is
  `DateTime(timezone=True)`. Pinned by a test.
- Grace window is half-open (`now < superseded_at + grace`), so exactly-at-boundary is PAST
  grace. Matches the pre-existing Case C behavior; pinned by a test.

**Deviation from plan (in CQ1's favor)**
CQ1 named "the read guard and `service.refresh` steps 2-4". There was a THIRD copy: the Case-B
successor-walk terminal check (`revoked_at is None and superseded_at is None and expires_at >=
now`) — the exact negation of the predicate's first three branches. DRYed it too; leaving a
third copy would have defeated the point.

**Verification**
- `docker-compose exec api uv run pytest tests/unit/auth tests/integration/auth -q` →
  **148 passed** BEFORE the new tests, including all 12 `test_refresh.py` cases (A/B/C) — the
  refactor is behavior-preserving, not just compiling.
- `docker-compose exec api uv run pytest tests/unit/auth/test_tokens.py -q` → **19 passed**
  (9 pre-existing + 10 new).

**Test-artifact coverage**: the artifact specifies the rejection matrix at the route level (S2/S3
own that). These are the unit-level predicate tests underneath it — no gap.

### S2 — read-only cookie media guard

**Files**
- `backend/app/auth/tokens.py` — `REFRESH_COOKIE_NAME` moved here.
- `backend/app/auth/routes.py` — re-exports `REFRESH_COOKIE_NAME = tokens.REFRESH_COOKIE_NAME`
  (name it exposes today is unchanged).
- `backend/app/auth/dependencies.py` — `require_media_session` + a block comment recording why
  the media route cannot ride `protected`, and why there is no dev bypass.
- `backend/tests/unit/auth/test_dependencies.py` — 2 new tests (absent + empty cookie).

**Decisions**
- The cookie name had to move: `routes.py` already imports `dependencies.py`, so putting the
  guard in `dependencies.py` and importing the constant from `routes.py` would cycle. `tokens.py`
  is imported by both and is where the transport constants already live. Tests reference the
  literal `"__Host-refresh"`, not the constant, so nothing broke.
- Guard returns `user_id`, not a `User`. It deliberately does NOT look up `users` — the plan
  says read-access revocation rides on the M3 invariant that a `session_version` bump also
  revokes the refresh rows, so a `User` join would be a second query buying nothing. `user_id`
  is used only for the failure log line.
- **Failures logged, successes not.** `emit_log_line(event="media_read", outcome="failure")` on
  every rejection; no INFO line per successful image load. One line per `<img>` render is noise
  with no security signal, while an unauthenticated hit on a private image is exactly the signal
  ops wants. REVIEW_CHECKLIST's one-structured-line-per-auth-request rule is written for the
  `/auth/*` endpoints; a subresource read is not one.
- 401 body is `errors.unauthorized()` — byte-identical to every other 401. Categorical reasons
  (`media_no_cookie`, `media_unknown_cookie`, `media_revoked`, `media_expired`,
  `media_superseded_past_grace`) live on the exception's `log_reason`, never in the body.
- No `with_for_update()` — a read must not touch the rotation grace window `/auth/refresh` owns.
- Renamed the local `status` → `session_status` to avoid shadowing `fastapi.status` in a
  security check.

**Deviation from the step plan (test placement, not scope)**
S2 was scoped as "guard + full rejection matrix". The matrix's serve cases assert real bytes
come back, so they need the route. Matrix moved to S3 against the real route — the plan's
mandated coverage is route-level anyway ("→ serve"). Nothing dropped; only relocated one step
later. The two branches that return before any DB access (absent/empty cookie) stayed as unit
tests here.

**Verification**
- `docker-compose exec api uv run pytest tests/unit/auth tests/integration/auth -q` →
  **158 passed** (no import cycle from the constant move, no auth regressions).
- `docker-compose exec api uv run pytest tests/unit/auth/test_dependencies.py -q` →
  **20 passed** (18 pre-existing + 2 new). The new tests pass `db=None`, which proves the
  absent-cookie path returns before any DB work.
- Confirmed `ix_refresh_tokens_token_hash` already exists (`cf4f8428948e`) — the guard is one
  indexed lookup per image load, no new migration.

### S3 — media read route + S4 — mount removal + S5 — T2 invariants

Landed together: the matrix's "→ serve" cases need the route registered, and the route is only
reachable once the mount is gone.

**Files**
- `backend/app/storage/keys.py` (NEW) — the canonical storage-key contract: `MANAGED_SUBDIRS`
  (closed allowlist), `MANAGED_EXTENSIONS`, `is_managed_key`, `is_stock_icon_key`,
  `stock_icon_path`, `STOCK_ICONS_DIR`.
- `backend/app/routes/media.py` (NEW) — `GET /uploads/{key:path}`.
- `backend/app/services/asset_lifecycle.py` — dropped its local `_KEY_RE`, now imports
  `is_managed_key`; `re` import removed.
- `backend/app/uploads.py` — `store_upload` rejects a subdir outside `MANAGED_SUBDIRS`.
- `backend/app/main.py` — `app.mount("/uploads", StaticFiles(...))` and the `StaticFiles` import
  DELETED; `app.include_router(media.router)` added after `protected`; obsolete
  mount-ordering comments removed; `UPLOAD_DIR` kept (LocalDiskBackend still needs it).
- `backend/tests/unit/test_storage_keys.py` (NEW) — 55 tests.
- `backend/tests/integration/auth/test_media_read.py` (NEW) — 41 tests.
- `backend/tests/unit/test_protected_router_propagation.py` — mount allowlist now empty; two
  new assertions for the cookie-guarded route.

**Decisions**
- **One canonical key validator.** PR1 kept the traversal regex inside `asset_lifecycle`. PR2
  adds a second path to storage (the read proxy), and CQ1's lesson is that a security check
  copied into two modules drifts. So the definition moved to `storage/keys.py` with three
  consumers. This also **closed the subdir set** — `_KEY_RE` previously allowed any
  `[a-z0-9_-]+` subdir. Verified against `23d02ef~1` that the four names have been stable since
  before M7, so nothing legitimate is excluded, and an unknown subdir is now a typo or an
  attack, never data. Strictly more fail-closed for `asset_lifecycle` too.
- **Everything not servable is 404** with a byte-identical body: malformed key, unknown subdir,
  missing manifest row, missing object. The response cannot be used to probe which keys or
  subdirs exist.
- **Storage-unreachable is 503**, not 500 or 404, and logged with a distinct `STORAGE
  UNREACHABLE` marker so ops can separate "unknown key" from "R2 is down" (eng review 1).
- **Guard runs as a dependency**, so it fires before key validation — the route cannot be probed
  unauthenticated for which key shapes are well-formed. Pinned by a test.
- **`If-None-Match` handles the shapes real clients send**: bare tag, `W/` weak tag, `*`, and
  comma-separated lists. Weak comparison is correct for GET.
- **304 responses carry `ETag` + `Cache-Control`** and still run the guard — a revoked session
  gets 401, never a cheap 304. Pinned by a test, since that is precisely what makes `no-cache`
  safe rather than a bypass.
- Media router registered AFTER `protected` so `POST /uploads/item-icon` keeps its exact-path
  match; verified by enumerating `app.routes`.

**Two bugs found by these tests (both real, both fixed)**
1. **`$` vs `\Z` in both key regexes.** Python's `$` also matches just before a trailing
   newline, so `item-icons/{uuid}.png\n` classified as a *valid managed key*. Fixed to `\Z`.
   Low practical impact (the newline key exists in neither disk nor R2) but it broke the
   invariant that a managed key is exactly what `store_upload` minted.
2. **Two of my own tests were vacuous.** `get_storage()` constructs a FRESH `LocalDiskBackend`
   on every call, so `monkeypatch.setattr(get_storage(), "get", ...)` patched an object the
   route never used — the 503 test passed 200 and the "storage untouched" assertion could never
   fail. Now patched at the factory (`app.routes.media.get_storage`), with a **negative control
   test** asserting the patch actually takes effect for a valid key.

**Test-design finding worth keeping**
httpx (like every conforming client) normalizes literal `../` dot-segments out of the URL path
before sending, so `GET /uploads/item-icons/../../app/main.py` never arrives as a traversal — it
404s on no-route-match, and a route test for it would pass with no validator at all. Verified
empirically which shapes DO arrive:

| Sent | Arrives as `key` |
|---|---|
| `/uploads/item-icons/../../app/main.py` | never routed (404) |
| `/uploads/stock_icons/..%2f..%2fapp%2fmain.py` | `stock_icons/../../app/main.py` |
| `/uploads//etc/passwd` | `/etc/passwd` (leading slash — `root / key` would discard the root) |
| `/uploads/unknown-subdir/x.png` | `unknown-subdir/x.png` |

So literal-traversal rejection is pinned at the unit level (`test_storage_keys.py`, no transport
in the way) and the route matrix covers only shapes that survive transport. Both halves are
needed; the split is documented in both files so nobody re-adds a vacuous route test.

**T2 (S5)**
- `test_logout_revokes_read_access_for_the_same_cookie` — login → image 200 → logout → same
  cookie → image **401**.
- `test_logout_bumps_session_version_and_revokes_refresh_rows` — asserts the invariant the guard
  leans on: the bump and the revoke happen in the same operation.
- `test_session_version_bump_alone_does_not_revoke_reads` — the documented hazard from the
  plan's failure-mode table, pinned so nobody later assumes the guard checks `session_version`
  itself. Same convention as PR1's A1 out-of-scope doc test.
- No separate operator password-rotation route exists; `service.logout` is the only
  `session_version` bump in the codebase, so it is the path tested.

**Verification**
- `docker-compose exec api uv run pytest -q` → **878 passed, 3 skipped, 0 failed** (9.8s), up
  from PR1's 768. The +110 is exactly the new tests (10 + 2 + 55 + 41 + 2).
- `app.routes` enumerated at runtime: **`mounts: []`** — no public static surface remains — and
  `/uploads/{key:path}` GET registered alongside `POST /uploads/item-icon`.
- Structural guard green with the new assertions; confirmed it FAILS first with
  `Routes missing auth: ['/uploads/{key:path}']` before the allowlist update, so it is really
  watching this route.
- No regressions anywhere from the mount removal — nothing in the suite depended on it.

### S6 — visual-suite media shim (A2)

**Files**: `frontend/tests/visual/fixtures/auth-base.js` — `context.route('**/uploads/**')`
fulfilling an inlined 1x1 PNG with `Cache-Control: private, no-cache`, beside the existing
`/auth/refresh` intercept.

**Decisions**
- Fixture bytes inlined as base64 rather than a fixture file, so the fixture module stays
  self-contained (matches how the token check is already handled there).
- The shim is unconditional. The visual stack *cannot* satisfy the real guard: the browser talks
  to docker hostnames (`frontend-preview` / `api-test`), which are not same-site, so a
  `SameSite=Strict` cookie would not transmit on an `<img>` subresource load. Same rationale as
  the pre-existing `/auth/refresh` intercept (A2 (b)).

**Finding: the shim is preventative, not corrective.** Nothing in the current specs requests
`/uploads/*` — `tests/visual/fixtures/seed.js` seeds items with `icon_emoji`, not `icon_url`, and
no spec references an image. So the suite exercises no media path today. Installed anyway per
A2, and commented as ahead-of-need so the first spec that seeds an uploaded or stock icon stays
deterministic instead of silently 401ing. Also confirmed there are **no pixel baselines** (0
`.png` files, no `toHaveScreenshot`) — the suite is geometric-invariant, as LESSONS records — so
the shim cannot shift a baseline.

**Gap found in the documented visual-test procedure**
`development-commands.md` says to build `frontend-preview frontend-visual` only. `api-test` has
NO bind-mount for `app/` (deliberate — Adversarial A5), so it bakes the backend in at build
time. Following the documented sequence after a backend change runs the visual suite against the
**old** backend — with the StaticFiles mount still present — which would have "passed" while
proving nothing. I built `api-test` as well. This belongs in `development-commands.md`
(see Doc impact).

**Verification**
- `docker-compose --profile visual-test build api-test frontend-preview frontend-visual` → built.
- `docker-compose --profile visual-test up -d --wait db redis api-test frontend-preview` → all
  healthy.
- `docker-compose --profile visual-test run --rm frontend-visual` → **7 passed (7.1s)**, against
  a rebuilt api-test with the mount removed.
- Teardown: removed only the visual-only containers. Did NOT run the documented
  `down -v`, which would have wiped the shared `db` / `uploads_data` volumes and killed the dev
  stack mid-session.

### S7 — `<img>` cookie guardrail (OQ6)

**Files**: `frontend/src/lib/apiBase.js` — guardrail comment at `apiUrl()`. (The backend half
was written with S3 in `app/routes/media.py`.)

**Decision: one comment at the shared seam, not 11 copies.** The plan says "near the `<img>`
consumers", and there are 11 of them — but every one resolves its URL through `apiUrl()`, so
that single function is the choke point. Duplicating the warning 11 times is the exact drift
hazard CQ1 is about, and 11 comments rot independently. The comment names all three
cookie-suppressing patterns (`crossorigin`, `fetch`/XHR, CSS `background-image`), lists the
consumers, and cross-references the media router; the router's docstring points back.

**Premise re-verified in code (not taken from the plan on trust)**
- `grep -rn 'crossorigin' src/` → only my own comment. No `crossorigin` attribute exists.
- `grep -rn 'backgroundImage|background-image' src/` → only my own comment.
- `grep -rn 'fetch(.*uploads|XMLHttpRequest' src/` → only my own comment.
- All 11 `apiUrl(` call sites feed an image `src`.

**Verification**
- `docker-compose run --rm frontend npm run test:run` → **547 passed, 57 files**, including
  `src/lib/apiBase.test.js`.

### S8 — prod enablement + cutover runbook

**Files**
- `backend/fly.toml` — NEW `[env]` block with `STORAGE_BACKEND = "r2"`.
- `backend/docker-compose.yml` — removed the now-dead stock-icon copy from the api entrypoint.
- `backend/.env.example` — annotated the `STORAGE_BACKEND` entry, pointing at the runbook.
- `infra/r2-cutover-runbook.md` (NEW) — operator procedure.

**Two user decisions (both asked, both approved)**

1. **`STORAGE_BACKEND=r2` is versioned in `fly.toml`, not a Fly secret.** A deliberate
   exception to this project's convention (every other prod env var is a Fly secret). Reason:
   `R2Backend` shipped in PR1, so PR1's code honors `STORAGE_BACKEND=r2` too. As a secret, the
   flag would SURVIVE a code rollback, leaving PR1's code writing to R2 while reading from disk
   — the one genuinely broken combination, and the sharp edge of the adversarial review's
   remaining `[medium]` rollback concern. In `fly.toml` the flip reverts atomically with the
   code. Rationale recorded inline in `fly.toml` and in the runbook.
2. **The dead stock-icon copy is removed** (plan said "flag for removal in PR2; don't silently
   drop" — so it was flagged and asked, not tidied away). After PR2 the media route reads stock
   icons from `/app/stock_icons_src`; nothing reads `/app/uploads/stock_icons` any more.

**Runbook contents** — pre-cutover gates (OQ1 live same-site check marked BLOCKING and
operator-owned; CF no-cache check; `fly volumes list` for OQ3's residual; `R2_*` presence with a
names-only command and the unfiltered-`env` warning from LESSONS), the cutover sequence with a
timestamp field and smoke freeze, smoke verification (including `fly apps restart` → image still
renders, which is what actually proves R2 over ephemeral disk), the three rollback windows with
forward-fix preferred, and the post-cutover CF Access Application 1 teardown with a note to
record it in `cloudflare-state.md` the way Application 2 was on 2026-05-14.

The runbook also documents the prod stock-icon breakage found in S0 grounding, so the operator
expects stock icons to start working rather than to regress.

**Verification — live, against real uvicorn (not ASGITransport)**
Recreated the api container so the new compose command took effect; it boots clean. Then ran a
throwaway script inside the container (so no secret value could reach the transcript — it mints
a session by inserting a `refresh_tokens` row rather than reading `HOUSEHOLD_ACCESS_KEY`) and
cleaned up after itself. **17/17 checks passed:**
- `GET /uploads/stock_icons/homework.png` with no cookie → **401**. Before PR2 this returned
  200 with bytes from the static mount. That single line is the milestone.
- `GET /uploads/{key}` no cookie → 401; with a valid cookie → 200, bytes round-trip exactly,
  `content-type: image/png` from the manifest, `Cache-Control: private, no-cache`,
  `ETag: "item-icons/…png"`; `If-None-Match` → 304 with an empty body.
- Stock icon with a valid cookie → 200 and **byte-identical to `/app/stock_icons_src/homework.png`**
  — proves the route does not read the uploads volume, so removing the compose copy is safe.
  (The stale `/app/uploads/stock_icons` directory survives in the existing dev volume as a
  harmless leftover; nothing reads it.)
- Key validation over real HTTP: unknown subdir, `%2f`-encoded traversal, leading-slash
  absolute (`/uploads//etc/passwd`), unknown key → all 404.
- Revoked cookie → 401.

## Doc impact

- **S3/S4/S5** — `BACKEND_STRUCTURE.md`: new `GET /uploads/{key}` endpoint (auth model, 404/503
  mapping, ETag/304, stock-icon compat branch), new `app/storage/keys.py` module, the removed
  StaticFiles mount, and `store_upload`'s subdir allowlist. `APP_FLOW.md`: `/uploads/*` is now
  authenticated — unauthenticated image loads 401. `PRD.md`: the "no public static surface"
  acceptance criterion is now met. `IMPLEMENTATION_PLAN.md`: M7 status at `/ship` time.
  `REVIEW_CHECKLIST.md`: candidate FastAPI check — "a route gated by something other than
  `get_current_user` has its own structural assertion".
- **S8** — `TECH_STACK.md` "Infrastructure": the new `fly.toml` `[env]` block and
  `infra/r2-cutover-runbook.md` (doc map: `backend/fly.toml` + `infra/**` → this section).
  `development-commands.md` "Full Stack": the compose entrypoint no longer copies stock icons.
- **S6** — `development-commands.md`: the visual-test build step must include `api-test` when
  backend code changed (it has no bind-mount), and the `down -v` teardown warning about shared
  volumes. `frontend/tests/visual/README.md` may want the same note.
- **S7** — `FRONTEND_STRUCTURE.md`: `apiUrl()` now carries the private-media constraint that
  governs how every image may be loaded.
- **S2** — `BACKEND_STRUCTURE.md` (auth section): `require_media_session` dependency, its 401
  reason codes, and the "no dev bypass" property. `REVIEW_CHECKLIST.md` may want a check for
  "new cookie-authorized routes reuse `refresh_row_status`" — decide at `/update-docs`.
- **S1** — `BACKEND_STRUCTURE.md` (auth section): new shared `refresh_row_status` predicate +
  `RefreshStatus` enum in `app/auth/tokens.py`; note the three consumers. No endpoint, schema,
  route, dependency, or token change → no other doc.

## Update-docs conclusion

Recorded verbatim from `/update-docs` (default mode):

```
DOC SYNC REPORT — default — prod-r2-storage vs master — 2026-09-09

| Doc | Section | Action | Summary |
|---|---|---|---|
| BACKEND_STRUCTURE.md | API Endpoints | updated | added GET /uploads/{key} (cookie-authed read proxy); corrected the File Upload table to the 5 real endpoints; fixed the stale upload response shape (no `filename` since PR1); recorded StaticFiles mount removal + no public static surface; updated the structural-test assertions; corrected `SameSite=Lax` → `Strict` (OQ1 reconciliation) |
| BACKEND_STRUCTURE.md | Code Organization | updated | retitled "M7 storage layer (PR1)" → "M7 storage layer" and documented the key contract (`storage/keys.py`), the media read route, ETag/304, 404-vs-503 mapping, `\Z` anchoring, prod `STORAGE_BACKEND=r2`; added `uploads.py`, `storage/`, `utils/upload_validation.py`, `services/asset_lifecycle.py`, `routes/media.py` to the directory tree; noted `refresh_row_status` on tokens.py and `require_media_session` on dependencies.py |
| FRONTEND_STRUCTURE.md | Directory Overview | updated | apiBase.js carries the private-media guardrail; new Key Patterns entry on why all 11 `<img>` consumers must stay plain `<img>` with no `crossorigin` |
| TECH_STACK.md | Infrastructure | updated | `STORAGE_BACKEND` comment corrected (prod runs r2), `STOCK_ICONS_DIR` added, prod-only Fly-secret list added; File Storage row marked live since M7; new "Object storage (Cloudflare R2)" subsection covering why the flag is versioned in fly.toml rather than a secret, plus the runbook link |
| development-commands.md | Full Stack | updated | compose api no longer copies stock icons; visual-test build must include `api-test` (no bind-mount); `down -v` warning about shared volumes; note on the `/uploads/*` Playwright shim; env-var pointer to the owning doc |
| IMPLEMENTATION_PLAN.md | Phase 7 / epic table | no change | M7 row already reads `implementing` with `PR1 2026-09-09 (#41)`; PR2 is unmerged, so a `shipped` claim would be premature — `/ship` owns that row |
| APP_FLOW.md | Screen Inventory | no change | no page, route, or user-facing error copy changed; images render at the same logical paths as before |
| AGENTS.md | Project Overview | no change | already states "Cloudflare R2 (uploads)" — aspirational before, accurate now; it links to the docs and duplicates no facts |
| config.json | doc_map | no change | every changed path resolved to an owner; `infra/**` was already mapped |

Guard: doc-guard --staged --dry-run -> would pass
Questions: 0 asked, 0 applied, 0 declined
Unmapped: none

DOC IMPACT: updated 5 docs
```

Two items deliberately left for a later `--full` pass rather than edited:
- `TECH_STACK.md` "Production Deployment (**Planned**)" still says Planned though M2 shipped Fly,
  Vercel, R2 and DNS. Pre-existing drift my diff does not settle; re-titling is a narrative
  rewrite. I corrected only the File Storage row, which the diff does settle.
- `REVIEW_CHECKLIST.md` was not touched: its own guidance says entries come from a *review*
  finding a repeatable bug class, and no review has run on this code. Candidate check handed to
  `/review-implementation`: "a route gated by something other than `get_current_user` carries its
  own structural assertion."

`LESSONS.md` gained five canonical rules from this PR (placed under their topical sections, not
appended blindly) plus one `## Decisions` row:
- Backend Lessons — anchor key/path regexes with `\Z`, never `$`.
- Test isolation gotchas — patch the factory, not the returned instance, when a getter
  constructs per call (with a negative control); HTTP clients normalize `../` out of URL paths,
  so route-level traversal tests can be vacuous; the visual-test stack and the integration suite
  share `todo_app_test`.
- Workflow And Trust Rules — rebuild `api-test` after backend changes; it has no bind-mount.
- Decisions — version a storage-cutover flag with the code, not as a platform secret.

## Update-docs conclusion — at ship (2026-09-11)

Three further `/update-docs` runs happened after the one recorded above: a default-mode run
after the first pre-landing review (PRD Route Protection, media-route headers/ordering/503
mapping, fail-closed storage boot, CI env, same-site constraint), a `--full` audit (split out
into its own PR, `docs-full-audit`, which this branch is stacked on), and this ship-time run:

```
DOC SYNC REPORT — default — prod-r2-storage vs docs-full-audit — 2026-09-11

| Doc | Section | Action | Summary |
|---|---|---|---|
| TECH_STACK.md | CI/CD Pipeline | updated | lint is now gated in `frontend-tests`; the "not gated" note replaced with what was fixed |
| development-commands.md | Full Stack | updated | lint command comment: gated in CI |
| PRD.md | 5.12 CI/CD & Easy Deployment | updated | "CI: Linting enforced" ticked |
| BACKEND_STRUCTURE.md | API Endpoints / Code Organization | no change | final-review edits (401 no-store, write-side transaction release) already documented by that review |
| REVIEW_CHECKLIST.md | FastAPI / Object storage | no change | final-review check already added |

Guard: doc-guard --staged --dry-run -> would pass
Questions: 0 asked, 0 applied, 0 declined
Unmapped: none

DOC IMPACT: updated 3 docs
```

## Completion

**Finished:** 2026-09-09 23:40

### What was built

M7 PR2 closes the last publicly-readable surface in the app. `GET /uploads/{key}` is now an
authenticated FastAPI route guarded by the `__Host-refresh` cookie, and the
`app.mount("/uploads", StaticFiles(...))` line is gone — the app now serves **zero** static
mounts, which is the structural property that lets the operator tear down Cloudflare Access
Application 1. Production writes uploads to Cloudflare R2 (`STORAGE_BACKEND=r2`, versioned in
`fly.toml` so a rollback reverts the flip atomically).

Underneath: the "is this session valid?" predicate is extracted once
(`tokens.refresh_row_status`) and consumed by three call sites that previously each had their
own copy; the storage-key contract is extracted once (`storage/keys.py`) and consumed by the
three paths that reach storage, with a closed subdir allowlist. Both extractions exist because
CQ1 and PR1's path-traversal CRITICAL were the same failure: a security check duplicated across
modules drifts. Reads carry `private, no-cache` + `ETag` + `304`, so a valid session revalidates
cheaply while the edge is still forbidden to cache private bytes and the guard re-runs on every
load. Stock icons keep their existing `/uploads/stock_icons/*.png` URLs via a compat branch —
which incidentally *fixes* them in production, where nothing had ever populated
`/app/uploads/stock_icons`.

Because the DB stores logical paths and `apiUrl()` resolves them at render time, both the
storage backend and the access model changed without touching a single `<img>` consumer or
migrating a single row.

### Test results

| Suite | Command | Result |
|---|---|---|
| Backend | `docker-compose exec api uv run pytest -q` | **878 passed, 3 skipped, 0 failed** (run twice) |
| Frontend unit | `docker-compose run --rm frontend npm run test:run` | **547 passed, 57 files** |
| Frontend lint | `docker-compose run --rm frontend npm run lint` | clean |
| Frontend build | `docker-compose run --rm frontend npm run build` | ✓ built in 2.00s |
| Visual regression | `--profile visual-test run --rm frontend-visual` | **7 passed** (against a rebuilt `api-test`) |
| Framework helpers | `python3 -m pytest .agents/tests -q` | **270 passed** |
| Live end-to-end | in-container script vs real uvicorn | **17/17** |

PR2 added **110 backend tests** (768 → 878): 10 predicate, 2 guard, 55 key-contract, 41 media
route, 2 structural.

**One flaky full-suite run, diagnosed not dismissed.** A single backend run reported 72 failed /
263 errors between two 878-green runs. Cause: it fired while the visual-test `api-test` container
had just been migrating and seeding the *shared* `todo_app_test` database, which the integration
suite also owns. Individual files passed in isolation throughout — the tell. Re-ran green twice
after the visual containers were removed. No code changed in response, and the gotcha is now a
LESSONS rule.

### Test-artifact coverage

Every PR2 item in `prod-r2-storage-test-artifact.md` is covered: the full read-guard rejection
matrix, `stock_icons/*` compat, manifest content-type, malformed/traversal key rejection, 404 for
missing row/object, storage-unreachable 5xx logged distinctly, `Cache-Control` + `ETag`/`304`,
and the session_version→read-access invariant tests.

**Two gaps, both operator-owned and neither automatable from here:**
1. **OQ1 live same-site check** — a real Cloudflare-proxied browser confirming the
   `SameSite=Strict` cookie transmits on an `<img>` subresource load from `mealy.dev` →
   `api.mealy.dev`, and that CF does not edge-cache `/uploads/*`. **Blocking pre-merge gate**,
   first item in the runbook.
2. **Prod durability** — an image surviving a backend redeploy. Requires the prod deploy; it is
   the `fly apps restart` step in the runbook's smoke section.

### Deviations from the plan

1. **CQ1 applied to a third call site.** The plan named `service.refresh` steps 2-4 and the read
   guard; `_refresh_case_b`'s terminal liveness re-check was a third copy. DRYed too.
2. **Key validation extracted to a new module** (`storage/keys.py`) instead of leaving the regex
   in `asset_lifecycle`, and the subdir set **closed** to the four real names. Verified against
   `23d02ef~1` that those names predate M7, so nothing legitimate is excluded.
3. **Rejection-matrix tests landed in S3, not S2** — their serve cases assert real bytes, so they
   need the route.
4. **One guardrail comment at the `apiUrl` seam, not 11 at the consumers.** All 11 resolve
   through it; 11 copies is the drift hazard CQ1 is about.
5. **`STORAGE_BACKEND=r2` in `fly.toml [env]`, not a Fly secret** — user-approved exception to
   the project convention, for rollback atomicity.
6. **Compose stock-icon copy removed** — flagged and user-approved, per the plan's "flag for
   removal, don't silently drop".

### Fixed during implementation (found by my own tests)

- `$` → `\Z` in both key regexes: Python's `$` also matches before a trailing newline, so
  `item-icons/{uuid}.png\n` classified as a valid managed key.
- Two of my tests were vacuous: `get_storage()` returns a fresh backend per call, so patching the
  returned instance patched nothing the route used. Repatched at the factory and added a negative
  control.
- Route-level literal-`../` traversal tests were passing on no-route-match, since httpx
  normalizes dot-segments. Moved to unit level; route matrix now uses `%2f`-encoded and
  leading-slash shapes that actually arrive.

### Known concerns for review

- The adversarial review's remaining `[medium]` (PR2 rollback awkwardness) is **reduced, not
  eliminated**: the flag now reverts with the code, but recovering R2 objects written after
  cutover is still manual. The runbook prefers forward-fix and documents the three windows.
- `require_media_session` deliberately does not check `users.session_version`, by design. The
  invariant it leans on is pinned by tests, including a documented-hazard test asserting that a
  bump *without* a revoke still serves — so the coupling is explicit rather than assumed.

**STATUS: DONE_WITH_CONCERNS** — implementation complete and verified; the two operator-owned
gates above (OQ1 live same-site check, prod durability) cannot be exercised from this session and
must pass before merge/teardown.
