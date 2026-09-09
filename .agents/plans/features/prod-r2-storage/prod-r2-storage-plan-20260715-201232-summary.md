# Execution Summary — M7 `prod-r2-storage` PR1 (Foundation)

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
- [ ] **S0 — Deps.** `boto3` (main) + `moto` (dev/test) via `uv`. Note in TECH_STACK.md.
- [ ] **S1 — Storage abstraction.** `app/storage/`: `base.py` (Protocol), `local.py`, `r2.py`
      (boto3 + `run_in_threadpool`), `__init__.py` (env factory, default `local`). Tests (moto for R2).
- [ ] **S2 — `assets` table.** `Asset` model + Alembic migration. Cols: `key` PK text,
      `content_type`, `size_bytes`, `created_at`, `referenced` bool (server_default false).
      Index `(referenced, created_at)`.
- [ ] **S3 — Unified validator.** `validate_and_read(file, *, max_bytes, subdir)` — streaming-abort
      reader, magic-byte PNG/JPEG/WebP, reject GIF/SVG/fake. Delete weak `save_upload`. Tests.
- [ ] **S4 — Upload endpoints.** 4 types → validate → `storage.put` → INSERT assets(referenced=false)
      → return `/uploads/{key}`; compensating `delete` on DB failure (+ log if delete also fails).
      Tests incl. failure injection.
- [ ] **S5 — Lifecycle hooks.** Adopt/replace/delete on the 4 entity write paths + `stock_icons/*`
      carve-out (no ref flip, no delete). Tests incl. A1 duplicated-key out-of-scope doc test.
- [ ] **S6 — Abandoned-upload sweep.** Celery beat task (reuse `run_async` + engine dispose per
      LESSONS): delete assets rows + objects where `referenced=false AND created_at<now()-24h`. Tests.
- [ ] **S7 — `echo=True` env-gate.** `database.py` → `SQLALCHEMY_ECHO` env. Mark TODOS.md done.
- [ ] **S8 — Full suite + docs.** `docker-compose exec api uv run pytest`; update BACKEND_STRUCTURE,
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
