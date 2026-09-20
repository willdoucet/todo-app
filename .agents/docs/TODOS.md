# TODOs

## P2 — Env-gate `echo=True` on the SQLAlchemy async engine  ✅ DONE (M7 PR1, 2026-09-08)
**Status:** ✅ DONE in M7 `prod-r2-storage` PR1 — `backend/app/database.py` now reads `SQLALCHEMY_ECHO` (default `false`). Kept as a record; safe to remove on the next TODOS.md prune.
**What:** Replace the hardcoded `echo=True` in `backend/app/database.py` with `echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"`. Default off in production; opt-in for local debugging via `SQLALCHEMY_ECHO=true` in compose env.
**Why:** Today every SQL statement — including auth queries against `users` / `refresh_tokens` and refresh-token hash bytes — is dumped to stdout in production. Two problems: (a) log volume explosion at any real request rate (Fly logs aren't free), (b) borderline information disclosure for any future operator with read access to fly logs. Surfaced 2026-05-03 while debugging the M3 connection-pool 500 — the engine config was found to also have this gap. Fixing it under the same PR was rejected to keep scope disciplined.
**Effort:** S (human: ~15 min / CC: ~5 min)
**Priority:** P2
**Depends on:** Nothing — can be done anytime. Recommend bundling with the next backend infra PR.

## P2 — Fix the 5 pre-existing frontend lint errors and gate lint in CI  ✅ DONE (M7 PR2, 2026-09-11)
**Status:** ✅ DONE on `prod-r2-storage` (PR: https://github.com/willdoucet/todo-app/pull/44) — `frontend/eslint.config.js` gives `playwright.config.js` Node globals and turns `react-hooks/rules-of-hooks` off under `tests/visual/**`; `.github/workflows/test.yml` runs `npm run lint` in `frontend-tests`. 0 errors / 7 pre-existing warnings remain. Kept as a record; safe to remove on the next TODOS.md prune.

**What:** `docker-compose run --rm frontend npm run lint` exits 1 with 5 errors:
`frontend/playwright.config.js:11,15,17` — `'process' is not defined` (`no-undef`; the
Playwright config is Node, not browser, and `eslint.config.js` gives it no Node globals
env); `frontend/tests/visual/fixtures/auth-base.js:104,117` — `react-hooks/rules-of-hooks`
firing on Playwright's `use()` fixture callback, which is not a React hook and never was.
Then add a `lint` step to `.github/workflows/test.yml`'s `frontend-tests` job.
**Why:** `npm run lint` is documented in development-commands.md as a check to run, but no CI
job runs it, so it has been red for an unknown length of time and nobody noticed. Both error
classes are config gaps, not code defects — an `languageOptions.globals` entry for
`playwright.config.js` and a `react-hooks` override (or ignore) for `tests/visual/**`. Until
lint is gated, "lint is clean" cannot be asserted by anyone, and a real error would land
indistinguishable from these five.
**Context:** Surfaced by `/review-implementation` on `prod-r2-storage` (M7 PR2), 2026-09-10.
All 5 confirmed present on `master` — none introduced by that branch (verified with
`git show master:frontend/tests/visual/fixtures/auth-base.js`, and `playwright.config.js` is
untouched by the branch). Worth noting: that branch's execution summary reported
"Frontend lint → clean", which is what made the gap visible. Where to start:
`frontend/eslint.config.js`, then the CI job.
**Effort:** S (human: ~45 min / CC: ~15 min)
**Priority:** P2
**Depends on:** Nothing.

## P3 — Legacy `/uploads/*` keys that the M7 read proxy cannot serve

**What:** Two shapes of stored `/uploads/{key}` column value 404 against
`GET /uploads/{key}`, permanently: (a) keys whose extension is `.jpeg` or `.gif` — pre-M7
`save_upload` (`git show 23d02ef~1:backend/app/uploads.py`) trusted the filename and accepted
`{.jpg, .jpeg, .png, .gif, .webp}`, while `storage.keys.MANAGED_EXTENSIONS` is
`("png", "jpg", "webp")`; (b) any key written before migration `b7e2c9a4f1d8`, which creates
the `assets` manifest with **no backfill** — the read route treats "no manifest row" as 404
before it ever asks storage. The same keys also fail `asset_lifecycle.managed_key`, so they
can never be adopted or reclaimed either: permanent orphans.
**Why:** Nothing is broken today and no fix is warranted yet — but the failure is silent
(a broken `<img>`, no error, no log line) and the cause is three modules away from the symptom.
Recording it turns a future afternoon of debugging into a two-minute lookup.
**Context:** Surfaced by `/review-implementation` on `prod-r2-storage` (M7 PR2), 2026-09-10,
and by its adversarial subagent independently. **Verified zero affected rows** at that date:
`family_members.photo_url`, `responsibilities.icon_url`, `items.icon_url` and
`recipe_details.image_url` all returned 0 for `LIKE '/uploads/%'` in the dev database, and
`assets` was empty. Production is shielded because `backend/fly.toml` has no `[mounts]` block,
so `/app/uploads` is ephemeral and holds nothing durable (plan OQ3). The exposure is a *future*
environment with persisted uploads predating M7. Detection query:
`SELECT photo_url FROM family_members WHERE photo_url LIKE '/uploads/%' UNION ALL SELECT icon_url FROM responsibilities WHERE icon_url LIKE '/uploads/%' UNION ALL SELECT icon_url FROM items WHERE icon_url LIKE '/uploads/%' UNION ALL SELECT image_url FROM recipe_details WHERE image_url LIKE '/uploads/%';`
then check each against `app.storage.keys.is_managed_key` and for an `assets` row.
**Remedies (pick per case):** add `jpeg` to `MANAGED_EXTENSIONS` for read-side compatibility
only (`store_upload` still mints `.jpg`, so the write side stays canonical); and/or a one-time
backfill that walks `UPLOAD_DIR`, sniffs magic bytes, and inserts
`assets(key, content_type, size_bytes, referenced=true)`.
**Effort:** S to detect (human: ~15 min / CC: ~5 min); S–M to remediate depending on the case.
**Priority:** P3
**Depends on:** Nothing. Revisit only if an environment with persisted pre-M7 uploads appears.

## P3 — Serve Vercel preview deployments from a `mealy.dev` subdomain

**What:** Give Vercel preview deployments a `*.preview.mealy.dev`-style domain instead of the
default `*.vercel.app`, so previews exercise the real private-media auth path.
**Why:** `vercel.app` is on the Public Suffix List, so every `*.vercel.app` origin is a
distinct *site* from `api.mealy.dev`. The `SameSite=Strict` `__Host-refresh` cookie is
therefore not sent on `<img>` subresource loads, and **every image 401s on every preview
deploy** as of M7 PR2. Production is unaffected (`mealy.dev` + `api.mealy.dev` share eTLD+1).
Until this is fixed, a preview cannot be used to review anything image-related, and the
breakage looks identical to a real regression.
**Context:** Surfaced by `/review-implementation` on `prod-r2-storage` (M7 PR2), 2026-09-10.
Noted inline in `infra/r2-cutover-runbook.md` so the operator does not mistake it for a
cutover failure; this TODO is the actual fix. Also confirm the preview origin is added to
`CORS_ALLOW_ORIGINS` if XHR must work there too.
**Effort:** S (human: ~30 min / CC: n/a — Vercel dashboard + DNS)
**Priority:** P3
**Depends on:** Nothing. Only worth doing if previews are actually used for review.

## P2 — App-layer rate limit on `/auth/login`, behind the Cloudflare edge rule
**What:** Limit login attempts in the app itself, backed by the Redis the app already runs (Upstash in production, `redis` in compose): a per-IP counter on `POST /auth/login` (and `/auth/register`) keyed on `resolve_client_ip`, plus a cap on failed attempts against the single household account, answering 429 before argon2 runs.
**Why:** The Cloudflare WAF rule (`infra/cloudflare-state.md`, 5 req / 10 s / IP on `/auth/*`) is the only brute-force and argon2-CPU control on login. The 2026-09-11 origin bypass showed what that costs: while the Fly origin was reachable around Cloudflare, login attempts were unlimited and the single 1 GB web VM could be pinned. The origin lock (`quickfix/origin-verify-header`) closes that path, but a future edge misstep — the rule disabled, the zone moved, the plan changed — would reopen it with no signal from the app.
**Pros:** (a) Defense in depth that does not depend on edge config; (b) a per-account cap also slows distributed guessing that a per-IP edge rule cannot see; (c) Redis is already provisioned.
**Cons:** (a) Redis joins the login path, so a Redis outage needs an explicit fail-open or fail-closed decision; (b) a per-account cap lets an attacker lock the household out by failing on purpose, so it needs a short window and a clear 429, not a hard lockout; (c) per-IP keys trust `CF-Connecting-IP`, which is only sound while the origin lock holds.
**Context:** Option (c) in the 2026-09-11 origin-bypass triage (LESSONS.md → Decisions, 2026-09-11). Deferred because it does not close the bypass, and the `v1-productionization` epic defers "app-layer rate limiting beyond the edge rule" to v1.1. Where to start: a dependency on the `/auth/login` route in `backend/app/auth/`, with its own Redis client rather than Celery's, returning a 429 shaped like the other auth errors.
**Effort:** S–M (human: ~half day / CC: ~1 hour)
**Priority:** P2
**Depends on:** The origin lock being deployed, so the IP key is trustworthy. Pairs with the P2 "Burst-test `/auth/login` against the Cloudflare rate-limit rule".

## P2 — Cloudflare config-as-code or drift-detection for M8 runbook
**What:** During the M8 release runbook milestone, introduce real reconciliation between `infra/cloudflare-state.md` (the checked-in intent file from M2) and the live Cloudflare dashboard. Two acceptable shapes: (a) a small drift-detection script that hits the Cloudflare API, dumps current Access app + bypass policies + WAF rate-limit rules, and `diff`s them against the snapshot file (run in CI on a schedule, or as a runbook step), or (b) full Cloudflare-as-code via Terraform with the `cloudflare/cloudflare` provider, where the snapshot file is replaced by `.tf` config and `terraform plan` is the drift-detection mechanism.
**Why:** M2's snapshot file fixes "no source of truth in repo," but reconciliation is still manual eyeball at Slice 7. During M2-M5 (single operator, ~5 dashboard edits across slices, active Access bypass policy gating critical plumbing-test paths), a fat-finger or forgotten edit silently survives until something visibly breaks. The M8 runbook is the natural home because it owns operational durability — once auth has been live for a while and the M5 bypass is removed, drift detection becomes the load-bearing safety net for "did someone modify the rate limit on /auth/* and not tell us?" or "did the Access policy expire?"
**Pros:** (a) Closes the loop opened by M2's snapshot file — eliminates the "snapshot was right at PR-merge time but stopped reflecting reality two weeks later" failure mode; (b) Terraform path generalizes to other CF resources later (Workers, R2 lifecycle policies, additional WAF rules); (c) script path is far cheaper and reuses the existing snapshot schema as-is.
**Cons:** (a) Adds a Cloudflare API token surface that M2 doesn't need (must be scoped read-only for drift script, scoped narrowly for Terraform); (b) Terraform locks us into a configuration management pattern earlier than necessary; (c) drift-detection-script path is duplicate effort if Terraform later replaces it.
**Context:** Captured by Eng Review #3 (2026-04-30) of `prod-deploy-skeleton-plan-20260422-214657.md`, in response to the residual adversarial finding "Cloudflare Access and WAF config still live outside git." M2 ships `infra/cloudflare-state.md` as the M2-only mitigation; this TODO is the durable solution. Recommend starting with (a) the drift-detection script — far smaller, reuses the snapshot file's schema, and produces a clean signal ("dashboard differs from snapshot, here are the fields"). Convert to Terraform later if the operational benefit warrants it. Cloudflare API endpoints needed: `GET /accounts/:id/access/apps`, `GET /accounts/:id/access/apps/:app_id/policies`, `GET /zones/:id/rate-limits`. Check the snapshot file's "Last verified" date to know when human eyeball reconciliation last passed; surface drift detected after that date as the operator-facing signal.
**Effort:** M (human ~1 day for Terraform; ~half day for drift script + CI scheduling / CC ~1-2h for either path)
**Priority:** P2
**Depends on:** M8 runbook plan being drafted. Logical predecessor: `infra/cloudflare-state.md` exists in repo (lands in M2 PR `prod-deploy-skeleton`).

## P3 — Visual Regression Test Infrastructure for Mealboard — SHIPPED 2026-04-21
> **Status (2026-04-21):** Shipped on branch `mealboard-visual-regression`. Plan: `.agents/plans/features/mealboard-visual-regression/mealboard-visual-regression-plan-20260420-210508.md`. Post-land: run 10-cycle CI soak (SC6) and flip `visual-tests` job to required after zero-flake pass. Follow-up TODOs below for pixel layer, PR-bot diff comments, mobile coverage.

### Follow-ups spawned by this PR
- **P3 — Pixel-diff layer:** add `toHaveScreenshot()` assertions alongside the geometric bbox asserts in `frontend/tests/visual/specs/*.spec.js`. Use the existing `fixtures/geometric.js` seam — add a `pixelDiffOnHover()` helper. Effort: S (human: ~half day / CC: ~1h). Priority: P3. Depends on: this P3 merged + 10-run soak green.
- **P3 — PR bot that posts visual diffs as review comments:** GitHub Actions job reads `frontend/test-results/` on failure, uploads diff images, and comments the diff set on the PR. Effort: M (human: ~1 day / CC: ~2h). Priority: P3. Depends on: pixel layer above.
- **P3 — Mobile visual coverage:** clone the desktop viewport config to a `mobile` project in `playwright.config.js` with `devices['iPhone 13']`, cover MobileDayView's swipe between days. Effort: S (human: ~3h / CC: ~30m). Priority: P3. Depends on: this P3 merged.
- **P3 — Other-surface visual coverage:** extend to Lists, Responsibilities, Calendar. Each surface adds one spec file and reuses the existing `fixtures/geometric.js`. Effort: M per surface (human: ~half day / CC: ~1h each). Priority: P3.


**What:** Add a visual regression suite (Playwright + screenshot diffs, or Chromatic) for the mealboard surface — at minimum the SwimlaneGrid, MealCard (recipe + food-item variants), UndoMealCard, and the AddMealPopover.
**Why:** Mealboard polish PRs keep hitting the same class of bug — class-assertion tests pass but the rendered card jitters, action buttons render outside the expected zone, badges overlap, breakpoint behavior flips silently. The hover-expand animation in `mealboard-meal-card-polish` (Chunk 2) is a perfect example: RTL can confirm a `max-h-[48px]` class is applied but cannot confirm it animates without flicker, that the Cooked badge stays clear of the action zone, or that Safari doesn't show clip-flicker during expand. Each polish PR rediscovers this hole as an "Open Question."
**Pros:** (a) Catches the visual class of bugs that unit tests structurally miss; (b) tightens CI signal on every Mealboard PR (currently we ship and eyeball); (c) baseline screenshots become living documentation of the intended look; (d) pays back across every future polish PR.
**Cons:** (a) Initial setup is ~1-2 days for Playwright + CI integration + baseline screenshots + flake-control; (b) screenshot tests are notoriously flaky across font rendering / OS / antialiasing differences — needs a deterministic CI environment (Docker-based runner with fixed font set); (c) baseline drift becomes a review burden ("did this PR genuinely change the look or did the renderer shift by 1px?").
**Context:** Captured by Eng Review #1 (2026-04-18) of `mealboard-meal-card-polish-plan-20260417-213900.md` Issue 6A. The plan's Chunk 2 hover-expand animation is the immediate motivating case but the value compounds across every future Mealboard polish PR. Where to start: `frontend/tests/` already has Vitest + RTL set up — extend with Playwright in a sibling directory `frontend/tests/visual/` so CI can choose to run them separately. Use the existing `docker-compose exec frontend` pattern for invocation. Pin a base image with consistent font rendering. First baseline: capture the four canonical states from this plan's test artifact (recipe card collapsed, recipe card expanded, undo card mid-countdown, food-item pill). **Additionally (added by Eng Review 2026-04-20 of `mealboard-todos-042026-plan-20260420-185106.md`):** first baselines should also include the **hover-jitter invariants** — `day-header bbox.x` and `SwimlaneGrid bbox.width` must be constant across MealCard `hover` / `rest` / `exit` transitions. That plan fixed the reported hover-jitter with a 1-line `scrollbar-gutter: stable` on `MealPlannerView.jsx:430` and deferred the regression lock-in to this P3 explicitly. The hover-jitter test is the motivating case for this P3 PR's first work; structure it so the bbox-stability assertions land alongside the initial Playwright scaffolding.
**Effort:** M (human: ~1-2 days / CC: ~3 hours including baseline capture + first 5 tests)
**Priority:** P3
**Depends on:** Nothing — can be done anytime. Recommend starting after `mealboard-meal-card-polish` ships so the first baseline includes the new hover-expand and undo states.

## P2 — Single-transaction `sync_meal_to_shopping_list` to close concurrent add/remove race
**What:** Refactor `backend/app/services/shopping_sync.py::sync_meal_to_shopping_list` so the entire ingredient-loop runs inside a single transaction. Today the function takes `with_for_update()` on the meal entry, then issues per-ingredient `_upsert_shopping_item` calls each of which can flush/commit, releasing the row lock partway through. A concurrent `remove_meal_from_shopping_list` targeting the same entry can slip in between commits, leaving `synced_to_list_id` in an inconsistent state.
**Why:** Identified as finding **H8** in the `/review` adversarial pass on 2026-04-15 against `mealboard-main-page-updates`. Not a critical (no observed corruption yet at household scale, single API instance) — but the moment the app runs more than one Celery worker or scales the meal-entry create path, this becomes a real race window. Also see `crud_items.py` and `crud_meal_entries.py` Redis/atomicity pattern (Chunk 6 H1) for the precedent: lock-and-commit-once semantics is how these flows are supposed to work.
**Context:** Deferred from the `/review` Fix-First batch on 2026-04-15 because it requires restructuring `_upsert_shopping_item` to NOT flush per-ingredient — the current SAVEPOINT-based collision handling (Chunk 6 C4 fix) needs to coexist with a single outer transaction. Approach: (a) keep the SAVEPOINT around `INSERT` only, (b) hoist the final `db.commit()` to the end of the loop (currently happens inside `_upsert_shopping_item` for the existing-row update path), (c) add an integration test that runs `sync_meal_to_shopping_list` and `remove_meal_from_shopping_list` as concurrent tasks and asserts the final state matches whichever ran last (no half-state). Pair with H8 doc in `crud_items.py`'s "row lock semantics" comment block when one is added.
**Effort:** M (human: ~4 hrs / CC: ~45 min including the concurrency test)
**Priority:** P2
**Depends on:** Nothing — can be done anytime. Recommend bundling with the H6 observability work so the new metrics catch any state-machine drift this fix introduces.

## P2 — Drop `recipes_archived` and `food_items_archived` (Mealboard Item refactor Rev 4 cleanup)
**What:** Ship a small Alembic revision that drops the `recipes_archived` and `food_items_archived` tables created during Mealboard Chunk 0 Revision 3.
**Why:** Rev 3 keeps the legacy tables as read-only safety nets for 30 days after the cutover. Without an explicit cleanup, the archive tables become permanent dead weight, accumulate stale rows in backups, and confuse future schema readers.
**Context:** Added by Eng Review #3 (2026-04-13) of `mealboard-main-page-updates-plan-20260413-135505.md`. The plan documents Rev 4 inline at §0.2 line 663 but has no follow-up tracker. Wait until: (a) Rev 3 has been promoted in production for ≥30 days, (b) zero rollback events were triggered against the archives during the soak window, (c) one full cycle of every meal-planning flow has executed cleanly (drift audit, soft-delete, undo, hard-delete, shopping sync). Implementation: one Alembic revision with `op.drop_table('recipes_archived')` and `op.drop_table('food_items_archived')`, plus a downgrade that recreates them as empty (acknowledging this is post-archive-window so empty is fine).
**Effort:** S (human: ~30 min / CC: ~5 min)
**Priority:** P2
**Depends on:** Mealboard Chunk 0 Revision 3 promoted and stable for 30 days. Verify zero rollback events in the soak window before shipping.

## P2 — "Cooked N Times" Counter Pill on Recipe + Food Item Cards
**What:** Add a small counter pill on recipe and food item cards showing "Cooked N times" (or "Never cooked" for zero). Sourced from `meal_entries` filtered by `was_cooked = true` and grouped by `recipe_id` / `food_item_id`, dedupe-aware (one meal entry marked cooked = +1). Displayed as a muted text pill near the title, visible in both grid and list view.
**Why:** Makes the collection feel alive and informed. The user can see at a glance which recipes/food items are actually part of the rotation vs. dead entries that can be safely pruned. Reflects *real consumption* (was_cooked), not planned consumption — so it's more useful than a generic "used in N meals" count, which would confusingly imply ingredients rather than cooked meals.
**Context:** Deferred from CEO review of `mealboard-main-page-updates-plan-20260413-135505.md` (EXPANSION mode, delight opportunity 2). User explicitly wanted the counter phrased as "Cooked N times," not "Used in N meals," because recipes and food items ARE meals — the latter phrasing is recursive and makes you think of ingredients. Natural to build after soft-delete lands so the counter naturally hides soft-deleted entries. Implementation: one `GROUP BY recipe_id, COUNT(*) WHERE was_cooked = true` query on GET /recipes and an equivalent for food items, plus a small React pill component. Consider caching the count on the Item row itself (denormalized column updated via trigger or application code) if the GROUP BY adds latency at scale.
**Effort:** S (human: ~3 hrs / CC: ~30 min)
**Priority:** P2
**Depends on:** `mealboard-main-page-updates` merged (soft-delete lands first)

## P2 — "Cook This Again" Quick Re-add
**What:** Surface recently-cooked meals (marked `cooked=true` in past 4 weeks) at the top of the AddMealPopover with a "Cook again" label. One-click re-add to any slot.
**Why:** Families have rotation favorites. Current flow requires typing the recipe name every time. Re-add should be one click for recent hits.
**Context:** Added by CEO review of `mealboard-main-page-updates-plan-20260404-212132.md`. Relates to a planned future feature: "track meals cooked" — the mealboard already stores a `cooked` flag on MealEntry (set via the cooked-toggle on the meal card). This TODO is the surfacing layer on top of that existing data. Could also grow into: "meals cooked this month" dashboard, rotation analytics, "you haven't cooked X in 6 weeks" suggestions. Start minimal: filter MealEntry by date range + cooked=true, dedupe by recipe_id, rank by recency, show top 5 in popover.
**Effort:** S (human: ~4h / CC: ~20min)
**Priority:** P2
**Depends on:** `mealboard-main-page-updates` merged.

## P2 — Drag-to-Reorder Meals Between Slots/Days
**What:** Let the user drag a MealCard from one swimlane cell to another to move (not copy) the meal.
**Why:** Re-planning is common ("actually let's move taco night to Wednesday"). Current flow is delete + re-add. Drag is the obvious UX.
**Context:** Added by CEO review. Deferred from `mealboard-main-page-updates` plan to keep Phase 2 (taller-rows rewrite) focused. Drag-and-drop is fiddly — needs mobile touch handling, keyboard accessibility (move via arrow keys + Enter), visual drop-zone feedback, and PATCH /meal-entries/:id endpoint for date/slot changes. The new always-visible action icons (view-recipe / cooked / delete) mean the drag-grab affordance must be on a non-icon region of the card (thumbnail area, likely).
**Effort:** M (human: ~1 day / CC: ~40min)
**Priority:** P2
**Depends on:** `mealboard-main-page-updates` merged (new card layout stable first).

## P2 — Stuck PENDING_PUSH Recovery
**What:** Add cleanup sweep in periodic sync that re-queues or resets tasks/events stuck in PENDING_PUSH for >1 hour.
**Why:** If a push to iCloud fails all 3 retries, the item stays PENDING_PUSH forever. User's edit silently fails to sync.
**Context:** Existing tech debt affecting both calendar sync and new reminders sync. The periodic sync already runs every 10 minutes — adding a 'scan for stuck items' step is ~20 lines. Decision needed on recovery strategy: re-queue (risk: infinite retry), reset to SYNCED (risk: lose edit), or surface in UI (best but more work).
**Effort:** S (human: ~4h / CC: ~15min)
**Depends on:** Nothing — can be done anytime.

## P3 — Rename CalendarIntegration → CloudIntegration
**What:** Rename model class, table name, and all FK column references across ~15 files.
**Why:** The model now serves calendars AND reminders. Current name is misleading.
**Context:** Deferred from CEO review due to high blast radius. Should be standalone PR. Touches models.py, schemas.py, all CRUD files, all routes, tasks.py, both sync engines, frontend integration references. Use Alembic `op.rename_table` + FK column renames.
**Effort:** S (human: ~4h / CC: ~15min)
**Depends on:** Phase 2 of iCloud Reminders complete.

## P2 — Extend Toast Notifications App-Wide
**What:** Use the new ToastProvider/useToast from inline-edit PR across all pages (Calendar, Mealboard, Responsibilities, Settings).
**Why:** Currently only ListsPage will use toasts. Other pages use `console.error` or red banner `error` state for API failures — inconsistent UX.
**Context:** ToastProvider added in `lists-ui-update-inline-edits` branch. Wraps App.jsx. Each page just needs to replace `setError(...)` + error banner with `useToast().error(...)`. The red banner pattern in ListsPage can serve as the migration template.
**Effort:** S (human: ~2h / CC: ~10min)
**Depends on:** Inline edit PR merged.

## P2 — Keyboard Navigation Between Tasks
**What:** Arrow keys to move between tasks, Tab to advance focus through the task list.
**Why:** Keyboard-only users can't efficiently navigate the task list. WCAG 2.1 Success Criterion 2.1.1 (keyboard accessible).
**Context:** Inline editing establishes the task-as-editable pattern. Adding arrow key nav is a natural follow-up. The `editingTaskId` state in ListsPage already tracks the active task — extend to support keyboard-driven selection. Pattern: arrow keys change selection, Enter enters edit mode, Escape exits.
**Effort:** S (human: ~4h / CC: ~10min)
**Depends on:** Inline edit PR merged.

## P3 — Fuzzy Ingredient Name Matching for Shopping Aggregation (PARTIALLY ADDRESSED)
**What:** Improve shopping list aggregation to handle ingredient name variants like "ground beef" vs "beef, ground" or "chicken breast" vs "boneless chicken breast".
**Why:** Current aggregation uses exact case-insensitive matching. Users entering the same ingredient with slightly different wording get duplicate shopping items instead of a combined quantity.
**Context:** Plural/singular handling (bananas ↔ banana) is now SOLVED by `mealboard-main-page-updates-plan-20260404-212132.md` via `canonicalize_name()` + irregulars table. REMAINING scope: typos (Levenshtein), synonyms (ground beef ↔ mince), adjective stripping (boneless/fresh/organic prefixes), word-order normalization (beef, ground → ground beef). Explicitly scoped OUT of V1 per the aggregation spec. Start with synonym table — most predictable, easiest to debug.
**Effort:** M (human: ~1 week / CC: ~30min)
**Priority:** P3
**Depends on:** `mealboard-main-page-updates` merged.

## P3 — Cross-Group Unit Conversion (Weight ↔ Volume)
**What:** Enable unit conversion between weight and volume for ingredients where density is known (e.g., "1 cup flour" = "120g flour").
**Why:** Different recipes may measure the same ingredient by weight or volume. Without cross-group conversion, "1 cup flour" and "120g flour" stay as separate shopping items.
**Context:** Requires an ingredient-density lookup table (flour, sugar, butter, milk, etc. each have different densities). Only feasible for common ingredients — uncommon ones stay separate. Start with ~50 common ingredients. Use USDA FoodData Central as the density source.
**Effort:** M (human: ~1 week / CC: ~30min)
**Priority:** P3
**Depends on:** Mealboard overhaul + predefined unit system complete.

## P3 — Copy Week / Template Weeks for Meal Planning
**What:** Allow users to duplicate a previous week's meal plan to a new week, or save a week as a reusable template.
**Why:** Many families have recurring meal rotations (e.g., Taco Tuesday, Pizza Friday). Copying a week saves re-entering the same meals.
**Context:** Implementation: "Copy from last week" button in the week selector area. Creates new MealEntry rows with the same slot types, recipes, food items, and participants but for the target week's dates. Templates: save a week's plan as a named template (new TemplateWeek model), load it to any future week. Start with copy-week, add templates later. CEO-reviewed alongside `mealboard-main-page-updates-plan-20260404-212132.md` — considered for EXPANSION but deferred to keep that plan focused. Remains high-value follow-up — amplifies the scannable-planning win from the overhaul.
**Effort:** M (human: ~1 week / CC: ~30min)
**Priority:** P3
**Depends on:** `mealboard-main-page-updates` merged.

## P3 — Adopt Expand/Contract Migration Pattern for Multi-Instance Deploys
**What:** When switching to multi-instance deploys (staging + production, or multiple replicas), adopt the expand/contract migration pattern for all database migrations.
**Why:** The current mealboard overhaul uses a simple table rename (`meal_plans` → `meal_entries`) which is safe for single-instance but would break during a rolling deploy where old and new code run simultaneously.
**Context:** Expand/contract pattern: Phase A creates the new table alongside the old one + dual-writes. Phase B drops the old table after all instances run new code. This is standard for zero-downtime deploys. Adopt when: adding a load balancer, adding staging environment, or running multiple API containers. Also need rolling deploy orchestration (health checks, graceful shutdown).
**Effort:** M (human: ~1 week / CC: ~2 hours — requires deploy infrastructure decisions)
**Priority:** P3
**Depends on:** Decision to move to multi-instance deploys.

## P2 — Keyboard Navigation for Recipe Grid
**What:** Add arrow-key grid navigation + focus management to RecipeCard grid view. Arrow keys move between cards, Enter opens RecipeDetailDrawer, Escape closes it. Tab cycles through action buttons.
**Why:** Accessibility win. Power users can browse recipes without mouse. WCAG 2.1 Level AA compliance for grid patterns. Completes the "browse + discover" experience with keyboard-only flow.
**Context:** Added by CEO review of `mealboard-main-page-updates-plan-20260405-180444.md` (EXPANSION mode). Deferred because arrow-key math for a responsive grid (5 cols → 4 → 3 etc.) requires tracking focused index, computing column count from layout, and managing focus return from drawer. The card grid must ship first to establish the layout.
**Effort:** M (human: ~1 day / CC: ~20min)
**Priority:** P2
**Depends on:** Recipe card redesign plan shipped (grid layout stable).

## P3 — Drag-and-Drop Reorder for Sections and Tasks
**What:** Add drag-and-drop UI to TaskListView for reordering tasks between sections and reordering sections within a list.
**Why:** The backend has sort_order fields and a reorder endpoint, but no drag-and-drop UX. Apple Reminders has this — without it, sections feel incomplete.
**Context:** Backend is ready (sort_order + reorder API). This is purely frontend. Libraries: @dnd-kit (well-maintained, React 19 compatible). Need smooth animations and proper state management for optimistic reorder.
**Effort:** M (human: ~1 week / CC: ~30min)
**Depends on:** Phase 1 sections UI complete.

## P3 — Fix `obsidian-workflow registry-upsert --batch` partial-upsert footgun
**What:** The `registry-upsert --batch` command in `.agents/bin/obsidian-workflow` silently drops `source_tasks` and `task_count` fields from a registry entry when those `--set` flags aren't passed on a subsequent call. Any follow-up upsert that doesn't repeat every field wipes state.
**Why:** Observed during mealboard office-hours + CEO review sessions on 2026-04-13. Caused a real partial-data regression in `workflow-registry.json` that had to be manually restored. Easy to corrupt the registry with an innocent-looking follow-up upsert.
**Context:** The helper lives at `.agents/bin/obsidian-workflow`. The registry-upsert command for `--batch` mode should merge non-provided fields rather than replacing them. Fix: in the command handler, read the existing entry first and only overwrite fields that were explicitly set via `--set` or `--append`. Or: require all batch fields on every call and fail loudly if any are missing (less friendly but explicit). Impact: low — only affects the workflow helper tooling, not the main app. Impact if unfixed: every Obsidian workflow command risks silently corrupting the registry.
**Effort:** S (human: ~2 hrs / CC: ~15 min)
**Priority:** P3
**Depends on:** Nothing — can be done anytime.

## P2 — iCloud sync silent-failure detection widget  ✅ DONE (quickfix `worker-outage-hardening`, 2026-09-11)
> **Status (2026-09-11): DONE.** `ICloudSettings.jsx` already rendered "Last synced X ago" for calendars and reminders, so the quickfix added the freshness dot (red plus "sync overdue" past 30 minutes — three 10-minute beat cycles) and fixed the naive-UTC parse that made every such timestamp read as "just now" west of Greenwich. Shipped the day a 103-day worker outage was found, which is exactly the failure this predicted. **Gap left open:** the indicator is iCloud-specific and only visible on the Settings page — see the follow-up TODO below.

**What:** Add a small "last successful iCloud sync" indicator to the Settings page (or a dedicated admin dashboard panel): timestamp + red/green status dot. Sourced from the existing `CalendarIntegration`/`CloudIntegration` model's last-sync timestamp, updated by the Celery sync task on success.
**Why:** iCloud calendar + reminders sync runs every 10 min via Celery beat → worker. If Upstash Redis has a transient outage, the Celery worker crash-loops, or the iCloud CalDAV endpoint starts 401'ing, sync silently stops — no error surfaces to the operator. Pre-production ("app is off when I'm not using it") this was fine. Post-launch (v1 productionization plan `prod-contract-freeze`) it's a slow-burn reliability bug: the operator won't notice until calendar drift compounds a week later.
**Context:** Added by CEO review of `.agents/plans/features/prod-contract-freeze/prod-contract-freeze-plan-20260421-182714.md` (2026-04-21, Section 8 observability gap). Plan explicitly defers structured logging/alerting/Sentry to v1.1 — this is the smallest observability investment that catches the highest-probability silent-failure mode. Implementation pointers: `backend/app/services/icloud_sync.py` already records sync success; surface via `GET /integrations/icloud/status` (or reuse existing endpoint), render in `ICloudSettings.jsx` next to the existing connection state.
**Effort:** S (human: ~2 hrs / CC: ~30 min)
**Priority:** P2
**Depends on:** v1 productionization complete (no point before the app is accessible to the household).

## P2 — Background-job health signal that does not depend on iCloud
**What:** A "background jobs last ran" signal that is true whenever the Celery worker is alive, independent of any integration. Smallest shape: the worker writes a timestamp on every periodic task completion (Redis key, or a one-row table), the API exposes it (e.g. on the existing app-settings or a small `/health/jobs` read), and Settings renders it with the same freshness dot as the iCloud line. Optionally assert it in the deploy runbook alongside `fly status`.
**Why:** The 2026-09-11 outage ran 103 days undetected. The sync-freshness dot shipped that day only helps when iCloud is connected and somebody opens Settings — a household that never connects iCloud gets no signal at all, and neither does an unattended deploy. The worker also runs the soft-delete purge and the abandoned-upload sweep, both of which fail just as silently.
**Context:** Follow-up to the widget TODO above (see LESSONS.md, "`fly deploy` leaves an already-stopped machine stopped"). The periodic tasks are in `backend/app/tasks.py`; the schedule is `beat_schedule` in `backend/app/celery_app.py` (two 10-minute jobs, two hourly). A Redis key avoids a migration but dies with the broker; a table survives it and is queryable from the API without touching Redis. Where to start: decide the store, then write the timestamp from a `task_postrun` signal so no task has to remember to do it. Too big for a quickfix — it adds an endpoint and a data store, so it needs a plan.
**Effort:** S (human: ~half day / CC: ~1 hr)
**Priority:** P2
**Depends on:** Nothing — the quickfix's dot is in place and covers the iCloud-connected case.

## P2 — Wire knip Into CI
**What:** Add `npm run hygiene` (knip) as a step in `.github/workflows/test.yml` so dead code is caught automatically on every PR.
**Why:** The craft pass plan introduces knip as a dev dependency with a `hygiene` script, but explicitly defers CI wiring to keep scope disciplined. Without CI enforcement, knip only runs when someone remembers to run it locally. Dead code will accumulate silently between manual audits.
**Context:** Added by eng review of `mealboard-main-page-updates-plan-20260411-180243.md`. knip is already installed and configured (`knip.json` + `npm run hygiene`). The CI step needs: (1) add `npm run hygiene` after lint/test in the workflow, (2) tune `knip.json` ignores for any false positives discovered during the craft pass, (3) consider making it a warning (non-blocking) for the first 2 weeks to build confidence. The `frontend` service in docker-compose can run it: `docker-compose exec frontend npm run hygiene`.
**Effort:** S (human: ~2h / CC: ~10min)
**Priority:** P2
**Depends on:** `mealboard-main-page-updates` merged (knip + knip.json exist).

## P3 — Jump-to-Current-Week midnight rollover refresh
**What:** The "Jump to Current Week" button's visibility (`isOnCurrentWeek`) is computed once per render from `new Date()`. If a user sits on the Meal Planner page across midnight into a new week, the button stays hidden until the next re-render event (tab switch, data fetch, navigation).
**Why:** Known deferral from mealboard polish round 2 (plan 20260415-164719, Chunk 1). Deliberately not fixed because the window is narrow (user must be on the planner at exactly the Sunday midnight boundary), and any re-render clears it. Added to TODOS so the deferral is tracked, not forgotten.
**Context:** Fix pattern: add a lightweight interval (~60s) inside `MealPlannerView.jsx` that re-evaluates `isOnCurrentWeek` and triggers a re-render if the week boundary is crossed. ~10 lines but adds a persistent timer to a page that doesn't currently need one. Alternative: hook into `visibilitychange` to recompute on tab focus, which is lighter but doesn't cover the "user stares at the page" case.
**Effort:** S (human: ~30 min / CC: ~5 min)
**Priority:** P3
**Depends on:** Nothing — can be done anytime after Chunk 1 ships.

## P3 — Offline undo queue for soft-deleted items
**What:** When a user clicks Undo on the `UndoToast` while `navigator.onLine === false`, queue the retry locally and fire it automatically on the next `online` event. If the auto-retry also fails, surface a visible "Retry now" affordance on the toast.
**Why:** Plan §1916-1936 Chunk 6 / Expansion B. Current behavior: Undo click while offline → fetch fails → toast hides silently → user thinks the undo worked but it didn't. On a family phone bouncing between Wi-Fi networks this is a real footgun.
**Context:** Deferred from Chunks 5+6 batch on 2026-04-14 as a nice-to-have — the core soft-delete + undo flow already works on the happy path. Implementation: add a tiny queue in `UndoToast.jsx` (or lift into a dedicated hook) that captures `{itemId, undoToken, expiresAt}`, listens for the `online` window event, and auto-fires one retry. If the retry still fails, flip the toast into an `offline-retrying` state (plan §1916 state matrix) with a manual "Retry now" button. Test coverage: `navigator.onLine=false → queue → online → auto-retry`, plus the failure fallback.
**Effort:** M (human: ~1 day / CC: ~30 min)
**Priority:** P3
**Depends on:** Nothing — the `UndoToast` singleton from Chunk 0 is the integration point.

## P3 — Observability metrics + structured logs for the item lifecycle
**What:** Emit structured log lines + counter metrics for the full item lifecycle: upload failures (by status code), soft-delete scheduling, undo attempts (hit / expired / 409 / 410), hard-delete sweep results, and AI suggest failures once that endpoint ships.
**Why:** Plan §1961-1966 Chunk 6 Expansion F + plan §2053. When things break in production, the current code logs only errors via `logger.error()` with no structured context. An operator can't tell "how many times did the undo window expire this week" or "how often is the upload endpoint rejecting oversized files" without grepping logs by hand.
**Context:** Deferred from Chunks 5+6 batch on 2026-04-14 because the infrastructure choice (Prometheus vs StatsD vs Datadog vs simple JSON logs) is a separate decision, and the household-scale app hasn't had an observability-demanding incident yet. Start point: add `structlog` or `python-json-logger` to the backend + a small metrics helper wrapping `counter_inc(name, **tags)`. Wire into: `crud_items.soft_delete_item`, `undo_soft_delete_item`, `hard_delete_expired_soft_deletes_async`, `save_item_icon` (both happy path and each exception branch). Log fields: `item_id, item_type, undo_token_hash, latency_ms, error_code`.
**Effort:** M (human: ~1 week / CC: ~1 hour for the wrapper + wiring; the logging infra decision is the slow part)
**Priority:** P3
**Depends on:** Observability stack decision (which is itself a P3-or-P4 conversation).

## P3 — First-error focus invariant on form save
**What:** When `ItemFormModal` save fails with Pydantic field errors, focus the first invalid input so screen readers and keyboard users immediately jump to the offending field. Needs a `useFirstErrorFocus` hook that reads the error response and finds the first matching `[name=...]` input.
**Why:** Plan §1788 Chunk 6 delight add — last remaining item from the "Mealboard delight polish bundle" (cooked pulse + Cmd+S footer already shipped). Real a11y win; most visible for keyboard-only users hitting validation failures deep in the form.
**Context:** `fieldErrors` state already tracks validation errors in `ItemFormModal.jsx:526`; the form already marks invalid inputs with red borders (line 702). Missing piece: after save fails, focus the first input whose `name` matches a key in `fieldErrors`. Should also apply to `TaskFormModal` for consistency (same Cmd+S footer pattern). Keep as a small one-commit drop-in; the plan explicitly says (§1154) "if any one of them feels distracting in QA, cut it without ceremony."
**Effort:** S (human: ~1 hr / CC: ~15 min)
**Priority:** P3
**Depends on:** Nothing.

## P2 — Structured-JSON logging on protected-route 401s
**What:** Extend the M3 `app.auth.logging_utils.emit_log_line` discipline to fire on every 401 returned by the M5 protected-route boundary (i.e., from `Depends(get_current_user)` failures, not just `/auth/*` endpoints). Implement via a FastAPI `exception_handler` for the auth-domain HTTPException raised by `get_current_user`, or via a thin dependency wrapper that emits the log line before re-raising.
**Why:** After M5, every authentication outcome on `/auth/*` (register/login/refresh/logout/status) emits one structured JSON log line with `event`, `outcome`, `reason`, `user_id`, `ip`, `request_id`, `latency_ms`. Protected-route 401s drop to FastAPI's default unstructured logging instead — meaning a future Sentry / audit-log / multi-user observability story has TWO different log shapes for the same auth boundary. Closing the gap now (or marking it for v1.1) keeps the auth boundary uniformly observable.
**Pros:** (a) Single log shape across every auth outcome — easier to grep, dashboard, alert on; (b) prerequisite for any audit-log feature (v2 territory but inevitable); (c) ~30 LOC, no new deps.
**Cons:** (a) Adds a FastAPI exception-handler shape that didn't exist before; (b) duplicates the `request_id` / `ip` sanitization helpers if not careful (use the M3 helpers as-is).
**Context:** Surfaced during CEO review of M5 prod-auth-enforcement plan (2026-05-05). Mode-locked HOLD scope deferred this from M5 to v1.1 because (a) single-family v1 has only one user, so the only 401s come from the user's own browser during a redirect-to-login flow; (b) the IMPLEMENTATION_PLAN.md L179 explicitly defers "structured JSON logging beyond /auth/*" to v1.1; (c) M5's job is to wire the dependency, not extend the observability story. Pickup recipe: register a FastAPI `@app.exception_handler` for `auth.errors.AuthError` (or whichever class `get_current_user` raises) that calls `emit_log_line(event="protected_route_401", reason=..., request=...)` and then returns the existing `errors.invalid_token()` response. Tests live alongside the M3 auth log tests.
**Effort:** S (human: ~30 min / CC: ~10 min)
**Priority:** P2
**Depends on:** M5 PR1 merged (so the protected-route boundary is live).

## P3 — Align compose and CI Postgres with production (16 → 17)
**What:** Bump `backend/docker-compose.yml`'s `db` service and both `postgres:16` service containers in `.github/workflows/test.yml` (`backend-tests`, `migration-upgrade`) to the major version production runs, and keep TECH_STACK's "Database" row in step.
**Why:** Production is unmanaged Fly Postgres Flex on `flyio/postgres-flex:17.2` (an update to 17.7 is available); dev and CI run 16, and TECH_STACK said "Managed PostgreSQL 16" until M8 PR1a corrected it. The `migration-upgrade` job therefore proves the Alembic chain on a different major than the one it runs against in production. Low risk today (plain DDL), but it is exactly the class of quiet drift M8 exists to remove, and the backup-restore drill's own re-run trigger is "after a Postgres major-version upgrade".
**Pros:** (a) Two image-tag edits; (b) CI proves migrations on the real major; (c) removes a surprise the next time a migration uses a 17-only feature or a 16-only behavior.
**Cons:** (a) Every contributor re-initializes the local `db` volume; (b) anyone restoring a production dump locally needs a matching `pg_dump`/`pg_restore` major; (c) the visual-test profile's `db` is the same service, so it moves too.
**Context:** Found by `/plan-eng-review` of M8 (`prod-launch-release`) on 2026-09-12 while checking the drill: `fly status -a mealy-app-prod-db` reports `flyio/postgres-flex:17.2`; `backend/docker-compose.yml` and `.github/workflows/test.yml` pin `postgres:16`. Where to start: change the three image tags, run `docker-compose down -v && docker-compose up --build`, run the full backend suite and the `migration-upgrade` sequence from development-commands.md, then update TECH_STACK → Infrastructure → Docker Services and Production Deployment. Decide at the same time whether to take Fly's 17.7 image update (`fly image update -a mealy-app-prod-db`), which is itself a drill re-run trigger.
**Effort:** S (human: ~1 h / CC: ~15 min)
**Priority:** P3
**Depends on:** Nothing. Best done right after M8 ships, before the next migration.

## P3 — `ICloudSettings` consumes the server-derived job staleness instead of its own 30-minute rule
**What:** Replace `SYNC_STALE_AFTER_MS` (30 min, "three missed 10-minute cycles") in `frontend/src/components/settings/ICloudSettings.jsx` with the per-task `stale` flag `/healthz.jobs` reports for `app.tasks.sync_all_icloud_integrations` and `app.tasks.sync_all_reminders`, through the shared freshness module M8 item 15 extracts.
**Why:** After M8 PR1b the server derives "overdue" per task from `celery_app.conf.beat_schedule` (three times each task's own interval). The iCloud card still carries a second, hardcoded definition of the same idea, so the two dots on one Settings page can disagree the day the schedule changes, and the freshness bug class logged 2026-09-11 would have two places to recur.
**Pros:** (a) One definition of overdue; (b) deletes a constant and its comment; (c) the iCloud line becomes a plain consumer of the module item 15 creates, so the M8 extraction is completed rather than half-done.
**Cons:** (a) The iCloud line then depends on the `/healthz` poll as well as the integrations query, so "can't check" needs a sensible fallback (keep the local rule as the fallback when `/healthz` is unreachable); (b) small enough that it is tempting to fold into PR1b, which is already the gated UI change.
**Context:** Found by `/plan-eng-review` of M8 (`prod-launch-release`) on 2026-09-12, Section 2 (DRY). Item 15's per-task thresholds and five states are specified in the plan's item 15 and open question 6; the shared module lands in `frontend/src/lib/` and `frontend/src/components/shared/` in PR1b. Where to start: read the `jobs` rows from the same `useQuery(['healthz'])` the jobs indicator uses, look up the two sync task names, and pass `stale` into the shared line; keep `parseServerTime` for the "Last synced N min ago" text, which is still the integration's own timestamp.
**Effort:** S (human: ~1 h / CC: ~15 min)
**Priority:** P3
**Depends on:** M8 PR1b shipped (`/healthz.jobs` and the shared freshness module exist).

## P3 — Small-text contrast: `text-text-muted` and `terracotta-600` text fail WCAG AA
**What:** Audit every `text-text-muted` use (190 today) and every `text-terracotta-600` used as link or button text; move the ones that carry meaning (timestamps, hints a user acts on, links) to `text-text-secondary` and `text-terracotta-700`, or decide to darken the two tokens in `frontend/src/index.css` instead of swapping call sites.
**Why:** Measured during the M8 design review (WCAG relative luminance, 2026-09-14): `text-muted` #9A9287 on `card-bg` #FFFDFB is 3.03:1; `terracotta-600` #C4613F is 4.04:1 on `card-bg` and 3.61:1 on `warm-beige`. AA needs 4.5:1 for `text-sm`/`text-xs`, which is where both are used. `FRONTEND_GUIDELINES.md` §9 already says "never use `text-muted` for critical information", and nothing enforces it. The passing replacements are `text-secondary` #6B645A (5.76:1) and `terracotta-700` #A34E32 (5.01:1 on `warm-beige`).
**Pros:** (a) Readable secondary text for everyone, including the kitchen tablet in daylight; (b) turns a guideline sentence into a checked rule; (c) M8 already moved the Background jobs card and the iCloud "Last synced" line, so the pattern exists.
**Cons:** (a) Touches roughly 50 files; (b) darkening muted text flattens the page's hierarchy if applied indiscriminately — decorative and placeholder text can stay muted; (c) the mealboard visual-regression baselines need a refresh if pixel assertions exist by then.
**Context:** Found by `/plan-design-review` of M8 (`prod-launch-release`), pass 6. Where to start: `grep -rn "text-text-muted\|text-terracotta-600" frontend/src`, classify each use as meaningful or decorative, and decide token-versus-call-site in one pass (a token change is one line but moves every placeholder too). Add a note to REVIEW_CHECKLIST → Tailwind CSS → Styling & accessibility so new code does not reintroduce it. `index.css` and `FRONTEND_GUIDELINES.md` are design-watched files; run `.agents/bin/design-sync-mark` after re-syncing the design tool.
**Effort:** M (human: ~1 day / CC: ~2 h)
**Priority:** P3
**Depends on:** M8 PR1b shipped (it establishes the `text-secondary` status-text precedent).

## P3 — Show "iCloud sync is behind" on the Calendar page, not only in Settings
**What:** When `/healthz.jobs` reports `app.tasks.sync_all_icloud_integrations` or `app.tasks.sync_all_reminders` stale, render the same one-line alert M8 adds under the Settings title at the top of the Calendar page, linking to Settings' Background jobs section — only when the household has an iCloud integration connected. The two cleanup jobs never surface there.
**Why:** M8's storyboard (item 15a, step 2) has a parent open Settings "because the calendar looks out of date", but the calendar is where they notice it, and nothing there says why. The Settings card answers the question only for someone who already thinks to look in Settings, which is the 103-day outage's shape one level down.
**Pros:** (a) Reuses `BackgroundJobsAlert` and `useBackgroundJobs` from M8 PR1b unchanged apart from a job filter; (b) the message appears where the symptom is; (c) no new data or endpoint.
**Cons:** (a) Adds the 30-second `/healthz` poll to the most-used page (cheap, but it is a request every 30 s while the calendar is open); (b) needs the integrations list to know whether iCloud is connected, so a household without iCloud never sees a sync warning; (c) a second place the alert can appear means copy and states must stay identical — derive both from `deriveJobsState`.
**Context:** Deferred by `/plan-design-review` of M8 (`prod-launch-release`), pass 7 and step 10. M8 item 15's scope is Settings (CEO review, candidate 4); the daily `ops-check` email remains the operator's between-release detector either way. Where to start: `frontend/src/components/calendar/CalendarPage.jsx`, call `useBackgroundJobs`, filter rows to the two sync task names, and render the alert with a link to `/settings#background-jobs` (focus the section `h2` on arrival, as Settings' own link does).
**Effort:** S (human: ~half day / CC: ~45 min)
**Priority:** P3
**Depends on:** M8 PR1b shipped (`BackgroundJobsAlert`, `useBackgroundJobs`, `/healthz.jobs`).

## P3 — Confirm boto3 default checksums against R2 at the first M8 release (leaked M7 finding)
**What:** During M8's first executed release, run the RUNBOOK's R2 smoke upload with boto3's default checksum settings and confirm the object lands and reads back. If it fails or R2 rejects the checksum headers, pin `request_checksum_calculation` and `response_checksum_validation` to `when_required` in `backend/app/storage/r2.py`'s client config and record the decision in TECH_STACK → Object storage.
**Why:** boto3 1.36+ sends CRC32 checksums by default. R2 had a documented incident with that default (January 2025, marked resolved) and Cloudflare's current R2 boto3 docs use the default client, so it is probably fine — but it has never been verified on this deployment. M7's final adversarial pass (PR #44, 2026-09-11) logged it as "investigate at runbook smoke" and it reached neither the M8 plan nor this file: the one M7 finding that leaked.
**Pros:** (a) One smoke upload, already in the runbook; (b) closes the last open M7 adversarial finding with evidence; (c) if it fails, the fix is two client parameters.
**Cons:** (a) Adds one line to an M8 runbook that is already long; (b) a pass proves only the current boto3 pin, so a future bump re-opens the question — note the pin in the log row.
**Context:** Found by `/plan-eng-review` of `workflow-review-resolution` on 2026-09-16 while executing that plan's Assignment (check whether M7's four `adversarial-subagent` findings logged `issues_open` at 2026-09-11T16:19:20Z were fixed before merge; the M7 plan's Final Review row lists this one as deferred). Where to start: `infra/RUNBOOK.md` smoke section once M8 PR1a lands; `backend/app/storage/r2.py` for the client; `backend/uv.lock` for the boto3 version in the log row.
**Effort:** S (human: ~30 min / CC: ~10 min)
**Priority:** P3
**Depends on:** M8 PR1a merged (`infra/RUNBOOK.md` exists) and its first executed release.

## P3 — Operator records for the re-review gate: a declared demand ("I edited the plan by hand; make eng look again") and a waiver
**What:** Two operator records, designed together so they share one log-entry shape. (1) A *declared demand*: let the operator record that a review must run again. (2) A *waiver*: let the operator clear a re-review demand without that review running. Framework 1.2.0 ships neither: `/plan-eng-review` of `workflow-rereview-utc` deferred the waiver on 2026-09-17 (UTC), so a demand clears only when the named review runs again, and `review-log --status resolved` is refused for a `stale` review. Today (after `workflow-rereview-utc`) a demand can only ride on a review's own log entry (`review-log --rereview <skill>`), so nothing can declare one for a change made outside a review: a hand edit to a plan after it passed eng review, or a review that finished before 1.2.0 existed.
**Why:** It is the one case the 1.2.0 gate cannot carry. M8 (`prod-launch-release`) is the example: its design review added a backend contract to item 15a after eng and adversarial review had passed, and because that review ran before declarations existed the tool can only *display* the concern (`Reason:` line), not block on it. Logging a second `plan-design-review` entry by hand would claim a run that did not happen, which the workflow forbids.
**Why the waiver was deferred:** it was the only path by which a log line could turn a blocked review ok without that review looking, so every fail-open risk in the design lived there. Three holes were found in it across two reviews (two union-merge timelines in the spec review; and "any entry carrying `waives_ts` is set aside", which let a hand-appended `issues_open` line with that key vanish). Demand Evidence held no case a waiver would have served, the operator's stated habit is "Agents handle it, I don't check", and scoped re-runs make a mistaken demand cost minutes. Build it when a real demand turns up that the named review genuinely cannot clear.
**Pros:** (a) Closes the last path where an overtaken approval is visible but not gating; (b) symmetric with `resolved_by=operator`, so the dashboard already has a way to show who did it; (c) small once the entry shape is decided.
**Cons:** (a) Needs either a fifth status word or a log entry that belongs to no review, and the four-word vocabulary shipped on 2026-09-17 — do not reopen it casually; (b) an agent can claim the operator asked, exactly as with the waiver, so the control is visibility, not proof.
**Context:** The demand was deferred by `/office-hours` of `workflow-rereview-utc` on 2026-09-17 (plan section Deferred, and section 11 for the M8 consequence); the waiver by that plan's `/plan-eng-review` the same day. **The waiver's full design is kept verbatim in that plan's "Appendix: the deferred operator waiver"**, with the three holes listed at its top — start there, and note the rule the third hole teaches: a waiver is an entry whose status is exactly `resolved` *and* that carries `waives_ts`; any other entry with that key is an ordinary run. Design both records together with the concern acknowledgement (next item). Where to start in code: `payload/bin/review-log` (`validate_entry`), `_lib.reviews_for_plan` (demands are collected in pass 1 from run entries only), and `_shared/obsidian-sync.md` for the vocabulary table. Decide the entry shape first; everything else follows from it.
**Effort:** M (human: ~1.5 days / CC: ~2.5 h) for both, once the shape is decided; the waiver alone is about a dozen reader tests
**Priority:** P3
**Depends on:** `workflow-rereview-utc` shipped (framework 1.3.1 in todo-app; the gate itself is 1.2.0's).

## P3 — A way to retire a displayed review `concern`
**What:** Let a concern that has been dealt with stop printing. From framework 1.2.0 a review's `concern` (`review-log --field concern="…"`) prints as a `Concern:` line on every session banner and in `--next`, from that review's latest run, until the review runs again without one or the plan ships. Nothing can mark it handled.
**Why:** The plan that introduced it (`workflow-rereview-utc`) argues in its own Status Quo that a warning which is read and ignored trains the reader to ignore warnings — that is why it removed the design-sync drift message. With eleven tiers, a plan that collects a concern at each of four plan reviews carries four standing lines through implementation, review and ship, whether or not anyone acted on them. The operator restored `concern` deliberately (premise 5: shown "whenever it exists", "with who wrote it"), so 1.2.0 keeps that behaviour; this item is about what comes after.
**Pros:** (a) Keeps the banner a signal; (b) an acknowledgement is itself a record of who decided the concern was handled, which the log lacks today.
**Cons:** (a) It is a third "entry that belongs to no review" beside the operator demand and the waiver, and the four-word vocabulary should not be reopened three times — design the three together; (b) an agent can acknowledge a concern it did not address, so the record must name who acknowledged and stay visible on the dashboard row; (c) may turn out unnecessary if concerns stay rare.
**Context:** Raised by `/plan-eng-review` of `workflow-rereview-utc` on 2026-09-17 (UTC), user chose to defer. Revisit after three or four plans have shipped on 1.2.0: count the `Concern:` lines on their banners at `ready-for-review` and how many were still true. Where to start: `_lib.reviews_for_plan` (where `concern` / `concern_ts` are carried from `last_run`), `workflow-state` (the `Concern:` lines and the de-duplication against `Reason:`), and the plan's §4.
**Effort:** S-M (human: ~half day / CC: ~1 h), less if built with the operator records above
**Priority:** P3
**Depends on:** `workflow-rereview-utc` shipped; evidence from a few plans.

## P3 — Make the re-review declaration mandatory at the ship stage
**What:** Require `--rereview none|<skill>` from the five ship-stage reviews (`review-implementation`, `adversarial-subagent`, `qa`, `design-review`, `final-review`) as framework 1.2.0 requires it from the four plan reviews. 1.2.0 accepts the flag from them and never requires it.
**Why:** Premise 4 of `workflow-rereview-utc`: a gate that depends on a reviewer remembering is the same hole the gate closes. `/final-review` auto-fixed eleven findings on `workflow-review-resolution` after other ship-stage tiers could have passed; a fix there can overtake a QA or design-audit pass exactly as a design review overtook eng on M8.
**Pros:** (a) Completes the rule; (b) the reader side already handles ship-stage demands (`can_demand` is same-stage for both stages), so this is writer validation, five skill edits and lint.
**Cons:** (a) Evidence is thin: one clear ship-stage override in three shipped plans, user-approved and harmless, plus two self-revisions; (b) `/review-implementation` writes its own entry and the subagent's in the same second, so someone must decide who declares on the subagent's behalf, and a demand written in that second reads as outstanding by the fail-closed tie rule; (c) five more call sites that fail when a locally modified skill forgets the flag.
**Context:** Open question 1 of `workflow-rereview-utc`, settled "optional for now" by its `/plan-eng-review` on 2026-09-17 (UTC), user decision. **Trigger to revisit:** a second real ship-stage override, or the first one that costs something (a fix that shipped past a QA or audit pass it invalidated). Where to start: `payload/bin/review-log` `validate_entry` (the "required when skill is one of the four plan reviews" rule), the five skills' completion sections, `tests/test_skill_lint.py`.
**Effort:** S-M (human: ~half day / CC: ~40 min)
**Priority:** P3
**Depends on:** `workflow-rereview-utc` shipped; the trigger above.

## P3 — `/execute-plan` refuses on a `blocked` or `needs-context` plan until the blocker is cleared explicitly
**What:** Today a plan whose `implementation_status` is `blocked` or `needs-context` still has `workflow-state --next` name `/execute-plan`, with the reason "resolve the blocker first: <reason>". The execute-plan guard program checks only that the named skill is `/execute-plan`, so it prints "cleared for implementation"; step 2 refuses only epics and shipped plans; step 3 then sets `implementing`. Running the skill is what clears the blocker. Proposed: `/execute-plan` step 2 also refuses when `implementation_status` is `blocked` or `needs-context`, prints the reason, and reports `NEEDS_CONTEXT`; whoever resolved the blocker clears it first with `obsidian-workflow plan-metadata-set "$_PLAN_FILE" --set implementation_status=not-started --set reason=""` (and the matching `registry-upsert`). Execute-plan's "Use when" bullet ("the plan is blocked … and the blocker is now resolved") and `_shared/completion-protocol.md`'s status table change to match.
**Why:** The reason line is the whole control, which is the same "displayed, not gated" hole `workflow-rereview-utc` closes for re-review demands (its Problem 2). It matters most in that plan's rollback: reverting PR-T converts every stale review into `blocked` + `reason` so 1.1.0 still gates, and this is the one path the conversion cannot close (`/ship` refuses on `blocked`; `/execute-plan` does not).
**Pros:** (a) A blocker becomes a real stop with an explicit, attributable clearing step; (b) closes the rollback's remaining fail-open path; (c) small: one refusal bullet, one documented sync command, one lint check, one `blocked` fixture.
**Cons:** (a) Changes how every blocked plan resumes today (run the skill → explicit unblock first), so it needs its own framework minor release and CHANGELOG note, not a ride on PR-F2; (b) zero recorded cases: no plan in this repo has ever been `blocked` or `needs-context` (registry and plan history checked 2026-09-18 UTC: 23 shipped, 2 not-started) — one since, benign: `workflow-rereview-utc` itself sat `blocked` from 2026-09-18T04:13:53Z to 04:38:19Z waiting on framework PRs #5 and #6 and resumed through `/execute-plan`, the legitimate resume this change would turn into two steps (noted by its `/review-implementation`; the trigger below fired on it without showing the risk); (c) an agent can run the unblock command itself, so the control is visibility of who cleared it, not proof.
**Context:** Found 2026-09-18 (UTC) by the scoped `/plan-eng-review` of `workflow-rereview-utc` while verifying its rollback (R2A) against framework 1.1.0 (`89f6aab`): `payload/bin/workflow-state` `_decide`, the `blocked` / `needs-context` branch (`nxt("/execute-plan", …, "resolve the blocker first …")`), and `payload/skills/execute-plan/SKILL.md` step 1's guard program plus step 2's refusal list. LESSONS.md → Patterns That Do Not Work records the behaviour. Where to start: execute-plan step 2's refusal list; then `workflow-state`'s gate comment block (lines 163–184 at `89f6aab`) if `--next` should name something other than `/execute-plan` for a blocked plan; then `tests/test_skill_lint.py` (execute-plan check) and `payload/tests/test_workflow_state.py` (a `blocked` fixture asserting the guard program exits non-zero). **Trigger to revisit:** the first plan that goes `blocked` or `needs-context`, or the first time the `workflow-rereview-utc` rollback runs.
**Effort:** S (human: ~1 h / CC: ~15 min)
**Priority:** P3
**Depends on:** `workflow-rereview-utc` shipped (its Rollback section references this item); its own framework minor release.

---

# Completed

## ~~P1 — Unified Item Model Refactor (Recipe + FoodItem → Item)~~ PROMOTED TO PLAN
**Resolved by:** `mealboard-main-page-updates-plan-20260413-135505.md` Chunk 0. The CEO review follow-up on 2026-04-13 promoted this from a deferred TODO into the polish batch itself, as the prerequisite for all subsequent chunks. The refactor adds ~2 weeks of human effort upfront but halves the work of every subsequent chunk (delete, icon upload, soft-delete, click-to-edit) and eliminates the duplication tax for future features. See the plan's "Chunk 0: Unified Item Model Refactor" section for full spec.

## ~~P3 — Remove Deprecated Mealboard Components After Overhaul~~ DONE
**Resolved by:** `mealboard-main-page-updates` craft pass plan (2026-04-11). Task 1 deletes `MealPlannerRightPanel.jsx`, `AddMealModal.jsx`, `MealDayColumn.jsx`, and 6 dead CSS classes from `index.css`. Verified by knip audit + manual grep + successful build.

## ~~P3 — `POST /items/suggest-icon` AI endpoint (Expansion C / Chunk 6 carve-out)~~ PROMOTED TO PLAN
**Resolved by:** `mealboard-ai-recipe-creator-plan-20260416-151059.md` CEO review expansion #5. The suggest-icon 501 stub is replaced with a real implementation using the shared `services/ai_client.py` layer built for the recipe import feature. ANTHROPIC_API_KEY and cost management are handled as part of the AI infrastructure setup. Verified: endpoint live at `backend/app/routes/items.py:195`.

## ~~P3 — Swap `FoodEmojiPicker` for `@emoji-mart/react`~~ DONE
**Resolved by:** Verified 2026-04-18. `FoodEmojiPicker.jsx` no longer exists in the codebase; `frontend/src/components/shared/EmojiPicker.jsx` now lazy-loads `emoji-mart` + `@emoji-mart/data` (package.json lists both deps) and is consumed by `ItemFormModal.jsx:854`. Includes search, recently-used row, and dark-mode theming.

## ~~P3 — Mealboard delight polish bundle (cooked pulse + modal shortcut footer)~~ PARTIALLY DONE
**Resolved by:** Verified 2026-04-18.
  1. **Cooked-state pulse animation** in `MealCard.jsx:177` — `meal-card-cooked-pulse` / `meal-card-cooked-pulse-dark` keyframes applied on cooked toggle. ✅ DONE
  2. **Modal shortcut footer** — `⌘S to save · Esc to cancel` strip rendered in `ItemFormModal.jsx:985` and `TaskFormModal.jsx:168`; Cmd+S handler wired via `frontend/src/hooks/useFormShortcut.js`. ✅ DONE
  3. First-error focus invariant — still pending; tracked as its own entry in the active list above.

## P3 — Add VRT-gate check to `/plan-eng-review` skill
**What:** Update `.agents/skills/plan-eng-review` (or wherever the skill is defined) to include a checklist item: "If the plan under review introduces new UI behavior or new user-visible components, does it include at least one visual invariant test?" If not, flag as a gap in the architecture review section.
**Why:** The mealboard-visual-regression plan guards against REGRESSIONS in existing tests, but nothing requires NEW mealboard/recipes/calendar PRs to add new visual tests. Without a plan-review-time gate, the recurring "Open Question: visual regression coverage for this chunk" pattern that motivated the CI infra plan could keep happening for new features.
**Pros:** (a) Catches coverage gaps at plan time, before implementation effort is sunk; (b) zero friction at PR time (no CODEOWNERS or template changes); (c) single-dev-friendly (no self-review theater); (d) reinforces the "visual invariants are a first-class test tier" mental model.
**Cons:** (a) Only applies to plans that go through `/plan-eng-review` — ad-hoc work still slips through; (b) edits a local `.claude/skills/` file that is sometimes user-scoped, sometimes project-scoped (confirm location before editing).
**Context:** Proposed during CEO review of `mealboard-visual-regression-plan-20260420-210508.md` (Issue 10A, 2026-04-20). User explicitly chose this path over PR-template checkboxes, CODEOWNERS rules, and CI lint rules. Implementation: add to the skill's Section 6 (Test Review) checklist or to the Section 1 (Architecture) new-codepaths audit.
**Effort:** S (human: ~30 min / CC: ~15 min)
**Priority:** P3
**Depends on:** `mealboard-visual-regression` plan ships and establishes the fixture pattern the gate will reference.

## P3 — Mobile viewport visual regression coverage (MobileDayView)
**What:** Add a second Playwright project configuration to `frontend/playwright.config.js` targeting 375×812 viewport. Write at least one spec exercising `MobileDayView` (mobile mealboard, `window.innerWidth < 768`): day-pill swipe navigation, card tap behavior, no layout jitter on day change.
**Why:** The first-land visual regression suite targets 1440×900 only. `MealPlannerView.jsx:67` swaps to `MobileDayView` below 768px — this is a different code path with different geometry. If a mobile-only regression lands (icon overlap, day-pill misalignment, swipe jitter), the desktop suite is blind.
**Pros:** (a) Closes a documented coverage gap; (b) reuses the existing `geometric.js` fixture verbatim (no new architecture); (c) exercises the responsive breakpoint the FRONTEND_STRUCTURE.md inventory calls out as load-bearing.
**Cons:** (a) Doubles CI wall-time for the visual-tests job (or requires parallel Playwright projects); (b) mobile touch gestures (swipe) are harder to simulate reliably than hover.
**Context:** Surfaced during CEO review of `mealboard-visual-regression-plan-20260420-210508.md` (Section 1 flag, 2026-04-20). Explicitly deferred from first-land per HOLD SCOPE mode. `MobileDayView` is at `frontend/src/components/mealboard/MobileDayView.jsx`. Implementation: add `{ name: 'mobile', use: { ...devices['iPhone 13'] } }` to the playwright config projects array, then write `mealcard-mobile.spec.js` with swipe + tap assertions.
**Effort:** S (human: ~3 hrs / CC: ~30 min)
**Priority:** P3
**Depends on:** `mealboard-visual-regression` plan ships and establishes the fixture pattern.

## P3 — Extend visual regression coverage to other app surfaces
**What:** Apply the geometric-fixture pattern from `mealboard-visual-regression` to (a) recipes page grid at custom breakpoints 400/500/800/1100, (b) ItemFormModal (recipe + food-item form transitions), (c) ListsPage inline-edit expand/collapse transitions, (d) Calendar week-view day-header geometry, (e) ICloudSettings 4-state connection UI transitions. One PR per surface, reusing `frontend/tests/visual/fixtures/geometric.js`.
**Why:** The mealboard-visual-regression plan establishes VRT for one surface (mealboard planner). Every other surface has its own class of geometric bugs waiting to happen — the recipes-page custom `@media` breakpoints are especially prone to invisible reflow bugs.
**Pros:** (a) Expands the CI safety net across the whole app; (b) each surface follows the same pattern, so incremental PRs are cheap; (c) prevents recurrence of the "VRT deferred as Open Question" pattern for non-mealboard features.
**Cons:** (a) 5 surfaces = 5 PRs = ~2 CC-hours total; (b) CI wall-time grows proportionally unless specs run in parallel; (c) each new surface may need its own data-testid additions, which is a small frontend scope creep per PR.
**Context:** Proposed during CEO review of `mealboard-visual-regression-plan-20260420-210508.md` (Section 1 EXPANSION analysis, 2026-04-20). Explicitly deferred from first-land per HOLD SCOPE mode. Recipes page is the highest-priority surface because of the custom-breakpoint grid — ItemDetailDrawer's bottom-sheet-to-side-drawer flip at 768px is another geometric transition worth guarding.
**Effort:** M (human: ~1 day / CC: ~2 hrs across 5 PRs)
**Priority:** P3
**Depends on:** `mealboard-visual-regression` plan ships and establishes the fixture pattern.

## P3 — Nightly flake-rate monitoring for visual regression suite
**What:** Add a nightly scheduled GitHub Actions job (`schedule: cron: '0 5 * * *'`) that runs the `visual-tests` suite 10 times against `master` and records the flake rate. Write rate to a status badge in `README.md` and open a GitHub issue automatically if rate >5% over a 3-day rolling window.
**Why:** The mealboard-visual-regression plan's SC6 is a one-time 10-run zero-flake gate at ship time. After ship, suite flake can silently drift (Docker image drift, new CSS animations, new viewport-dependent code) without anyone noticing until it blocks a hot-fix PR. A nightly re-soak catches drift within 24 hours.
**Pros:** (a) Catches suite-health degradation proactively; (b) creates a public badge that reinforces "our visual tests are healthy"; (c) reuses existing CI job definition verbatim.
**Cons:** (a) Adds ~30 min/day of CI compute; (b) creates issues that need triaging; (c) rate calculation is stateful (needs a small history file or GitHub Actions artifact).
**Context:** Surfaced during CEO review of `mealboard-visual-regression-plan-20260420-210508.md` (Section 8 observability follow-up, 2026-04-20). Explicitly deferred from first-land per HOLD SCOPE mode. Simplest implementation: a single job that runs the suite in a loop with `for i in {1..10}; do ...; done`, counts failures, compares against a threshold. More elegant: parallel matrix with `attempts: 10` and post-processing.
**Effort:** S (human: ~3 hrs / CC: ~25 min)
**Priority:** P3
**Depends on:** `mealboard-visual-regression` plan ships; visual-tests CI job is stable.

## P3 — Cloudflare config drift detection for M2 Access bypass + /auth/* rate-limit
**What:** Periodic verification that two Cloudflare configs M2 establishes are still active: (1) Access bypass policy on `api.todo.williamdoucet.dev` matching path `^/plumbing-test`, (2) Rate-limit rule on `api.todo.williamdoucet.dev/auth/*` (10 req/min/IP). Implement as either a nightly GitHub Actions job hitting Cloudflare API, OR an explicit checklist item in the M8 release runbook.
**Why:** Both configs are silent-failure modes. If the Access bypass is accidentally deleted in the Cloudflare dashboard, Slice 5 cookie verification fails (XHR receives 302 to Access challenge). If the rate-limit rule is disabled, M3 inherits an unprotected `/auth/*` surface — Argon2 is CPU-expensive and a single Fly VM can be CPU-pinned by an attacker, causing household DoS. Neither is detected by app-level tests because the failure is at the edge.
**Pros:** (a) Catches config drift before it bites M2-M5 plumbing or M3 auth surface; (b) automation version produces an alert vs. silent rot; (c) M8 runbook version is zero-cost to ship and forces operator awareness.
**Cons:** (a) API-token version requires a Cloudflare API token in CI secrets and rule-id parameterization; (b) runbook version is human-discipline-dependent; (c) the bypass policy concern only matters during M2-M5 (removed in M5 PR #2), so the API check has a short lifespan for one of its two assertions.
**Context:** Identified during M2 plan eng review (2026-04-22) as critical gaps #6 and #7 in the test artifact at `.agents/plans/testing/prod-deploy-skeleton-test-artifact.md`. Both configs are central to M2's split-origin cookie verification (bypass) and M3's load-bearing protection (rate-limit). Where to start: (a) MVP path is to add both checks to the M8 release runbook as explicit "verify in Cloudflare dashboard" steps, no automation; (b) automation path is a small Python or curl script using `https://api.cloudflare.com/client/v4/zones/{zone_id}/firewall/access_rules` + the rate-limit endpoint, run nightly via GitHub Actions, opens an issue if either config is missing/inactive.
**Effort:** M (human ~2-4h / CC ~30min for the automated version; S for runbook-only)
**Priority:** P3
**Depends on:** M2 shipped + Cloudflare API token provisioned in repo secrets (for automated version). Runbook version has no dependencies — can land any time after M2.

## P2 — Persisted auth event audit log (`auth_events` table)
**What:** Add an `auth_events` table + writer that logs one row per `/auth/*` event: `register`, `login_success`, `login_failed`, `refresh_success`, `refresh_failed`, `logout`. Columns: `id`, `event`, `user_id NULL`, `ip`, `outcome`, `reason TEXT NULL`, `created_at`. Writer runs in a separate try/except so audit-log failure never breaks the auth response.
**Why:** M3 ships with structured log lines (per CEO review 2026-05-01) but no persisted audit trail. Logs get rotated, dropped, or are hard to query. Auth-event records are what you want when a household member asks "did someone log in last Thursday at 2am, was that you?" or when investigating a brute-force attempt 3 weeks after the fact. Standard auth posture; explicitly deferred from M3 to keep HOLD SCOPE.
**Pros:** (a) Persistent, queryable record; (b) decoupled from log infrastructure; (c) standard auth posture once households scale beyond one user; (d) survives container/host rotation.
**Cons:** (a) New migration + model + retention policy; (b) IP storage is mild PII even for a household app; (c) double-write cost on every auth call; (d) premature for single-user-no-incidents scenario.
**Effort:** M (human: ~1 day / CC: ~30 min)
**Priority:** P2
**Depends on:** M3 ships and is observed in production for a meaningful window. Revisit after first auth incident or when multi-user-per-household lands (which makes "who did what" structurally interesting).

## P2 — Burst-test `/auth/login` against the Cloudflare rate-limit rule
**What:** Run M2's `slice6-rate-limit-burst-test.sh` (or its successor) against `/auth/login` once M3 is live in production. Verify: (a) the Cloudflare 10-req/min/IP rule fires before the single Fly `web` VM CPU pins; (b) legitimate household traffic (1-2 logins/day) is unaffected; (c) document the empirical burst tolerance number in `todo-app-notes/DevOps/`.
**Why:** Argon2 is CPU-expensive by design — that's the whole point of password hashing. The Cloudflare rate-limit rule is the only thing standing between an attacker's burst and household DoS. The rule was set up in M2 but has never been load-tested against a real argon2 endpoint. Unverified defenses are theater.
**Pros:** (a) Empirical confirmation that the security model holds under stress; (b) reuses an existing M2 script; (c) cheap to run during a low-traffic window; (d) produces a number to track if argon2 params are ever tuned.
**Cons:** (a) Hits production endpoints — needs to happen during a low-traffic window or against a cloned staging environment; (b) requires Cloudflare logs to confirm the rule fired (vs. argon2 being 'fast enough'); (c) if the test reveals the VM does pin before the rule kicks in, requires either rate-limit tightening or argon2 param tuning.
**Effort:** S (human: ~30 min / CC: ~15 min)
**Priority:** P2
**Depends on:** M3 ships and `/auth/login` is reachable. Coordinate timing window with operator's known idle hours.

## P3 — Frontend error reporting (Sentry / equivalent) for auth failure visibility
**What:** Wire a lightweight error-reporting client (Sentry free tier or equivalent) into `frontend/src/main.jsx`, gated by an env flag (`VITE_SENTRY_DSN`). Capture: uncaught render errors, axios response interceptor failures, the four `performRefresh` failure classes (401 / 5xx / network / timeout), the `handle401` redirect-storm path, and login/register/logout mutation 5xx + network errors. PII guard: scrub access tokens, the `__Host-refresh` cookie, and the `HOUSEHOLD_ACCESS_KEY` field from event payloads before send.
**Why:** M4 expands the frontend failure surface significantly (refresh fails 4 ways; mutations fail 3+ ways; redirect-storm guard, single-flight reuse, dark-mode HydrateFallback edge cases). DEV console logs cover local debugging, but when a family member reports "I got logged out for no reason" against the production deploy, today there is no signal — no stack trace, no failure class, no timing. A small reporting tool closes that visibility gap.
**Pros:** (a) Captures the failure mode + stack trace + URL + user agent at the moment of failure, instead of after-the-fact reconstruction; (b) free tier is sufficient for a single-family deploy; (c) integrates cleanly with TanStack Query's `QueryCache.onError` and `MutationCache.onError` (one wiring point, captures everything routed through `handle401`); (d) gives a baseline for any future frontend telemetry.
**Cons:** (a) New runtime dep + DSN env var; (b) Sentry SDK adds ~30KB gzipped to the bundle; (c) requires a PII-scrubbing rule that must be code-reviewed (token / cookie / access-key leakage would be worse than the visibility gap it solves); (d) if not gated, can fire on every dev save and burn quota.
**Context:** Surfaced by CEO Review of `prod-auth-frontend-session-plan-20260503-185400.md` (M4 frontend auth session). Plan adds DEV-gated structured console logs as part of M4's observability slice; this TODO is the prod equivalent. Recommend revisiting after M5 PR #2 removes the Cloudflare Access perimeter — at that point the app is reachable from any network and the failure surface that family members hit becomes representative of real-world conditions, not just operator-on-WiFi conditions.
**Effort:** S (human: ~half day / CC: ~2 hr)
**Priority:** P3
**Depends on:** M4 + M5 ship. Pair with the first non-trivial auth incident or before opening external user surface.

## P2 — Header user-menu with logout entry (M4 OQ4)
**What:** Add a user-menu component in the global header (avatar / initials button → dropdown with "Log out"). M4 places logout on `/settings` only because the page exists today and adding it there is zero scope; a header menu is the right long-term home but requires header redesign.
**Why:** Family members don't naturally look in `/settings` to log out — discoverability gap. The cost of a wrong-tab logout (lose draft state) is low, but the friction of "where do I sign out?" is a real onboarding drag.
**Pros:** (a) standard pattern users expect; (b) becomes the natural home for future profile / theme / keyboard-shortcut entries; (c) one place for the avatar to live (currently no avatar UI).
**Cons:** (a) header redesign touches every authenticated route; (b) requires a small design pass for placement on mobile (likely a hamburger or bottom-nav variant); (c) coordinates with the existing dark-mode toggle which probably also wants to live there.
**Context:** Captured by Eng Review of `prod-auth-frontend-session-plan-20260503-185400.md` (M4). Plan's OQ4 deferred this; logout button on `/settings` is the M4 stopgap. Where to start: existing pages all share no header component today — first work is extracting a `<AppHeader />` from whichever pattern is closest to canonical (likely the mealboard layout). Logout mutation already exists post-M4 in `lib/auth/queries.js` — just needs a button binding.
**Effort:** M (human: ~1-2 days / CC: ~3 hr)
**Priority:** P2
**Depends on:** M4 ships (logout mutation exists). Recommend bundling with the first post-M5 polish PR.

## P3 — Multi-tab logout broadcast (M4 OQ2)
**What:** Use `BroadcastChannel('auth')` (or `localStorage` event fallback for older Safari) to fan out logout / session-cleared events across all open tabs. When tab A logs out, tab B clears its in-memory token and navigates to `/auth` immediately, instead of waiting for its next API call to 401.
**Why:** Today (post-M4), tab B discovers logout on its next user action: 401 → axios interceptor refreshes → refresh fails (no cookie) → redirect to `/auth`. Functionally correct but leaves a stale-UI window where tab B looks logged in but every action will fail. Brief flash of protected-route UI before the redirect.
**Pros:** (a) eliminates the stale-UI window; (b) BroadcastChannel is a standard primitive supported in all evergreen browsers; (c) ~30 LOC including subscribe/unsubscribe lifecycle; (d) sets up the pattern for future cross-tab coordination (e.g., real-time meal-plan updates).
**Cons:** (a) cross-tab tests are notoriously fiddly to write deterministically; (b) BroadcastChannel is window-scoped — opening a new browser entirely doesn't get the message (acceptable, those windows refresh on next nav anyway); (c) introduces a new global side-effect surface that must be cleaned up in tests.
**Context:** Captured by Eng Review of `prod-auth-frontend-session-plan-20260503-185400.md` (M4). Plan's OQ2 explicitly deferred this with rationale "HttpOnly cookies emit no `storage` event so we'd need a separate channel anyway." Where to start: add a `lib/auth/broadcast.js` module with `subscribeToAuthEvents(callback)` and `publishAuthEvent(type, payload)`. Wire `publishAuthEvent('logout')` into the logout mutation's `onSettled`. Wire `subscribeToAuthEvents` into the root layout's mount effect. For tests, mock `BroadcastChannel` globally (jsdom doesn't provide it).
**Effort:** S (human: ~1 day / CC: ~1 hr)
**Priority:** P3
**Depends on:** M4 ships. Pair with the first user complaint about "got logged out in another tab" or the first multi-tab feature.

## P3 — Visual baselines for /auth portal surfaces (post-M5)
**What:** Capture Playwright visual baselines for the new auth surfaces introduced in M4: AuthPortalPage in LoginForm state, AuthPortalPage in SetupForm state, BootErrorScreen ("Can't reach the server. Retry."), and HydrateFallback (tiny boot spinner). Each in light + dark mode. Empty + populated input states for the forms. Disabled + enabled submit-button states.
**Why:** M4 ships ~5 new visible surfaces (login form, setup form, boot error, hydrate spinner, logout-failure warning). These have no visual baselines today. The existing P3 visual-regression infrastructure ships per-surface coverage; auth is the next surface that touches every user every session. Without baselines, future polish PRs (button restyles, focus-ring tweaks, dark-mode color audits) have no automated regression signal on the auth flow — and the auth flow is the one surface where a visual bug ("setup form rendered when login form should have") has a real UX consequence beyond aesthetics.
**Pros:** (a) auth is the highest-impact surface to baseline (every user, every session); (b) the existing `frontend/tests/visual/` scaffolding from the Mealboard P3 already supports the pattern — just one more spec file; (c) catches the "setup form vs login form" discriminator bugs that geometric assertions miss (the forms structurally differ but a wrong-form render still passes "form has 3 inputs" checks); (d) covers HydrateFallback in both color modes, which is already a CEO-review concern (A2).
**Cons:** (a) auth surface includes a HOUSEHOLD_ACCESS_KEY field that must be masked in screenshots (was originally also gated by a since-deleted env-flag bypass; M5 PR1 replaced that with Playwright `route()` interception of `/auth/refresh` plus real login-or-register at globalSetup, so baselines captured against the post-M5 stack are valid as-is); (b) BootErrorScreen requires deliberately-broken-backend test fixture, which adds setup complexity to the visual spec.
**Context:** Captured by Eng Review #2 (2026-05-03) of `prod-auth-frontend-session-plan-20260503-185400.md`. Reuses the existing P3 visual-regression scaffolding shipped in `mealboard-visual-regression`. Where to start: clone `frontend/tests/visual/specs/mealboard.spec.js` to `frontend/tests/visual/specs/auth.spec.js`. Add fixtures for (a) `account_exists: true` route stub (login form), (b) `account_exists: false` route stub (setup form), (c) `/auth/refresh` route returning 503 (BootErrorScreen). Mask `HOUSEHOLD_ACCESS_KEY` input via Playwright's `mask: [page.getByLabel('Household access key')]` option in `toHaveScreenshot()`. First baselines: 8 screenshots (4 surfaces × 2 modes).
**Effort:** S (human: ~half day / CC: ~1 hr)
**Priority:** P3
**Depends on:** M5 PR #1 ships (visual-test stack uses real login + Playwright `context.route()` interception of /auth/refresh; no bypass flag). Bundle with the existing "Other-surface visual coverage" P3 follow-up if both are scheduled together.

## P2 — `/uploads/*` asset auth strategy under M5 backend route enforcement — RESOLVED 2026-05-08 · ✅ DONE (M7, 2026-09-11)
> **Status (2026-09-11): CLOSED.** All four closure items landed. M7 PR2 (`prod-r2-storage`, PR: https://github.com/willdoucet/todo-app/pull/44) shipped R2 storage, the cookie-authenticated `GET /uploads/{key}` read proxy, and the StaticFiles mount removal; after the cutover smoke checks passed, the operator tore down Cloudflare Access Application 1 the same day. Recorded in `infra/cloudflare-state.md` and the `infra/r2-cutover-runbook.md` execution log.
> **Status (2026-05-08): RESOLVED in M5 PR2.** Strategy (a) chosen — `/uploads/*` is the FastAPI `StaticFiles` mount with no app-layer auth dependency. The wrapping `protected` APIRouter pattern from M5 PR1 cannot gate a `StaticFiles` mount, so Cloudflare Access on `api.mealy.dev` is the only thing standing between an open-internet request and an uploaded item image. **Cursor implementation review (2026-05-07) overrides the original plan's Premise 5:** Cloudflare Access stays on the API host until M7 replaces this mount with R2 + auth-proxied uploads. PRD §5.7 updated in PR2 Step 2.2 to acknowledge this. Fully closed by M7 (R2 + auth-proxied uploads + StaticFiles mount removal + CF Access removal as M7 exit step).

**What:** Decide and implement how `<img>`-rendered backend assets stay reachable after M5 PR #1 wraps non-auth API routes with `get_current_user`. `<img>` tags cannot send `Authorization: Bearer ...` headers, so the bearer-only access pattern M4 establishes will break image rendering on every protected page (recipe images, family-member avatars, food-item icons, responsibility icons) the moment M5 PR #1 ships. Four candidate strategies: (a) leave `/uploads/*` unprotected — accepts that an attacker who learns an upload path can fetch the binary, but leaks nothing structural about the household; (b) hybrid auth with a separate cookie-based session (e.g., a short-lived `__Host-asset-session` cookie issued at login alongside the bearer access token); (c) signed asset URLs — `apiUrl()` becomes `apiUrl(path, { signed: true })` and hits a backend endpoint that returns a short-lived signed URL; (d) move uploads to a CDN (R2 + Cloudflare Worker) with signed paths, decoupling asset auth from the API entirely.
**Why:** Without a decided strategy, M5 PR #1 either (1) silently breaks every image on every authenticated page, or (2) silently leaves a hole by exempting `/uploads/*` from auth without making the security trade-off explicit. M4 introduces the `apiUrl()` indirection in `frontend/src/lib/apiBase.js` exactly so this future change has a single hook point — but the strategy itself must be chosen before M5 implementation starts.
**Pros:** Captures the dependency between M4 (asset URL helper) and M5 (route enforcement) before M5 planning; lets the M5 plan author start from a shortlist of four strategies rather than rediscovering the problem during their own eng review; the `apiUrl()` hook is already in M4, so whichever strategy wins requires changes in one frontend file plus the backend.
**Cons:** Locks in a small architectural decision before it's fully needed; if M5 ends up choosing (a) "leave /uploads/* unprotected" the work to capture this TODO ends up being the only artifact (which is still net-positive — the trade-off was made consciously).
**Context:** Captured by Eng Review #3 (2026-05-03) of `prod-auth-frontend-session-plan-20260503-185400.md`. Surfaced when tracing what M4's `apiUrl()` helper must support post-M5. M4 introduces the helper at `frontend/src/lib/apiBase.js` — that file is the natural extension point for whichever strategy wins. Image-rendering callers post-M4: `MemberAvatar.jsx`, `ItemIcon.jsx`, `ItemCard.jsx`, `ResponsibilityCard.jsx`. Where to start: when scoping M5 PR #1, enumerate every `<img>` caller that constructs a backend URL and decide per-strategy. Strategy (a) is zero-implementation; strategy (b) requires a new auth dependency on the backend (`get_current_user_from_asset_cookie`); strategy (c) requires a new endpoint (e.g., `GET /uploads/sign?path=...`) plus an `apiUrl(path, { signed: true })` overload that fetches the signed URL synchronously in a `useQuery` keyed by path; strategy (d) requires standing up R2 + a signing Worker, which is the largest-blast-radius option but the most production-grade.
**Effort:** Decision: S (human: ~2 hr / CC: ~30 min). Implementation depends on chosen strategy: (a) S, (b) M, (c) M, (d) L.
**Priority:** P2
**Depends on:** M5 PR #1 planning. Recommend the M5 author resolves this TODO at the start of their planning, before scoping route enforcement.

## P3 — Real Mealy logo/wordmark glyph (M4 design review 1)
**What:** Replace the current text-wordmark + dot ('• Mealy' at 30px font-bold, 12px terracotta-500 dot) on the /auth portal with a designed brand mark. Three viable directions: (a) a custom logotype that re-letters "Mealy" with intentional shape choices; (b) a minimal glyph (the dot becomes something more deliberate — a fork, a leaf, a meal-related abstract mark); (c) a small icon-mark used together with the wordmark, similar to how Linear or Vercel pair a logo with a wordmark. Mark is reused on /auth (prominent), in /settings header (compact), and as favicon (square crop).
**Why:** The text-wordmark ships fine for M4 — restrained, on-brand, anchors the auth page well. But it's "a font in a color," not a brand. A real mark adds identity at every touchpoint (auth, header, favicon, eventually OG images and email templates). Higher craft level signals that the app is intentional, not generic. Also fixes the /vite.svg favicon, which is the most visible "this is a placeholder" tell.
**Pros:** (a) bumps craft level on the surface every user sees first; (b) replaces /vite.svg favicon (the most visible placeholder in the app); (c) once designed, easy to re-skin for any future marketing surface; (d) gives the app a memorable visual hook beyond the warm-cream + terracotta palette.
**Cons:** (a) real design effort — needs a designer or careful AI-tool iteration; (b) subjective and likely to iterate; (c) wordmark + glyph + favicon variants need consistent treatment across sizes; (d) commits the brand visually before the product is fully mature.
**Context:** Captured by Design review 1 (2026-05-04) of `prod-auth-frontend-session-plan-20260503-185400.md`. M4 ships the placeholder text-wordmark on /auth; the existing app Header.jsx and index.html still reference "Family Planner" pending the rename TODO below. Where to start: pick a direction (logotype vs. glyph vs. logo+wordmark pair), draft 3-5 SVG iterations, pick one, export at 16/32/48/192/512 sizes for favicon set + auth display.
**Effort:** M (human: ~1–2 days / CC: ~30 min for SVG iterations once direction is chosen)
**Priority:** P3
**Depends on:** M4 ships first (so the placeholder is in production). Pair with the rename TODO below so all brand artifacts update together.

## P2 — Rename "Family Planner" / "Doucet Family Planner" → "Mealy" across the existing app (M4 design review 1)
**What:** Global rename of the existing app's brand references to match the new "Mealy" name decided during this design review. Concrete touch points: (1) `frontend/index.html` `<title>Family Planner</title>` → `<title>Mealy</title>`. (2) `frontend/src/components/layout/Header.jsx:80` "Doucet Family Planner" → "Mealy" (or "Mealy — Doucet" if family personalization is wanted). (3) Any other hardcoded "Family Planner" strings (run `grep -rn "Family Planner" frontend/ backend/` to enumerate). (4) Verify the iCloud sync path doesn't externally hardcode "Family Planner" anywhere user-visible.
**Why:** Without this, the auth page (post-M4) says "Mealy" but the post-login app header still says "Doucet Family Planner." Inconsistent branding = user confusion at every navigation transition and erodes the polish the rename was meant to add. The auth surface is the user's first impression of the rename; the header is the surface they see for every subsequent minute of the session — they have to agree.
**Pros:** (a) small, mechanical PR — ~30 min of CC work covering ~3-5 files; (b) closes a brand-consistency gap before any user notices; (c) the existing app rename is the cheapest part of "Mealy as a brand" — defer the logo, do the rename now.
**Cons:** (a) the user said "for now" on the rename — if Mealy isn't the final name, this PR is wasted churn (revertible, but still churn); (b) "Doucet Family Planner" carries family-name personalization that "Mealy" alone loses — decide whether to keep ("Mealy — Doucet"), drop, or move family-name into a different surface.
**Context:** Captured by Design review 1 (2026-05-04) of `prod-auth-frontend-session-plan-20260503-185400.md`. M4 design review locked the auth surface copy to "Mealy" (auth-option-a-spec-aligned mockup). This TODO closes the gap between the auth surface and the rest of the app. Where to start: confirm Mealy is durable enough for a global rename, decide on family-name handling, then `grep -rn "Family Planner" frontend/ backend/` and rename mechanically.
**Effort:** S (human: ~30 min / CC: ~10 min)
**Priority:** P2 (do before M4 ships if Mealy is final, or ship M4 as-is and follow up within 1 week — don't let inconsistent branding linger)
**Depends on:** "Mealy" as a final-enough name that it won't change in 2 weeks. Recommend confirming this with the user before opening the rename PR.

## P3 — Post-setup onboarding nudge (M4 design review 1)
**What:** When the operator completes first-time household setup (one-time-ever event per deploy via `/auth` setup form), replace the current `navigate('/')` with a brief onboarding moment that helps them take the next step. Concrete options: (a) a one-time dismissible banner on `/` ("Welcome to Mealy. Add your first family member to get started." with a button linking to `/settings`); (b) a `/onboarding` route they pass through once with checklist steps (add family members, set meal-slot defaults, etc.); (c) a modal on first calendar load that opens directly into the family-member-add form. Recommended: option (a) for M4 follow-up — banner is the smallest delta from current behavior. Detect "first-time" via the absence of family members in the database (no flag needed).
**Why:** Currently the setup-success path lands the operator on `/` with an empty calendar. They just typed an email + password + access key; their reward is a blank screen. Emotional flat moment for what should feel like "I just set up our home." A nudge turns the empty state into a momentum moment ("here's the next thing"). Single-family deploys mean this happens exactly once per installation, but that one moment is the user's first 5 seconds with the post-auth app — which Don Norman's "Three Levels of Design" calls the visceral level, the moment that anchors all subsequent feelings about the app.
**Pros:** (a) replaces a flat first-impression with a guided moment; (b) cheap to build (~1 day human / ~30 min CC); (c) the no-family-members detection is a single API call M4 already enables; (d) extensible to future onboarding steps (recipes, meal slots) without a hard architecture commitment.
**Cons:** (a) setup happens exactly once per deploy, so ROI is bounded; (b) may be better as part of a broader "onboarding milestone" that holistically handles the empty-calendar / empty-recipes / empty-meals new-deploy state; (c) "first-time detection via empty family-members table" can false-positive if the operator deletes all members (acceptable — they get the welcome banner again, which is actually correct behavior); (d) introduces a new dismissal-state concern (localStorage flag for "banner dismissed?").
**Context:** Captured by Design review 1 (2026-05-04) of `prod-auth-frontend-session-plan-20260503-185400.md`. M4 ships setup-success → `navigate('/')` with no nudge. The plan's "NOT in scope (Deferred design decisions)" section already lists this as deferred; this TODO is the formal capture. Where to start: add a `<FirstRunBanner/>` to the calendar page that reads from `useFamilyMembers()` query — show when result is `[]` AND a `mealy:first-run-banner-dismissed` localStorage key is absent. Banner copy: "Welcome to Mealy. Add your first family member to get started." with a primary action button linking to `/settings`.
**Effort:** S (human: ~1 day / CC: ~30 min)
**Priority:** P3
**Depends on:** M4 + M5 ship; family-members management surface (`/settings`) is stable. Pair with broader onboarding work if a dedicated onboarding milestone is scheduled.

## P3 — Local dev seed-user helper (M5 Eng Review 2)
**What:** One-shot helper that creates a known-good local dev account on a fresh clone, so a contributor can run the app locally without manually hitting `/auth/register` first. Three viable shapes: (a) a Make target / `uv run` script that POSTs to `/auth/register` using `LOCAL_DEV_EMAIL` + `LOCAL_DEV_PASSWORD` + `HOUSEHOLD_ACCESS_KEY` from `.env` (only does anything if no users exist; prints credentials on success); (b) an alembic dev-only migration gated on `APP_ENV != production` that inserts a synthetic user with a pre-baked argon2 hash; (c) a `docker-compose exec api uv run python -m app.scripts.seed_dev_user` command. Recommended: (a) — smallest blast radius, no production code touched, idempotent. Documented in `CLAUDE.md` "Development Commands" section.
**Why:** After M5 PR1, every protected route 401s on a fresh clone until the contributor manually registers via `/auth/register`. Step 1.8 documents the env-var requirement (`JWT_SECRET_KEY`, `HOUSEHOLD_ACCESS_KEY`) but stops one step short — the user account itself still needs creating. This is a one-time setup step per contributor per machine; without the helper, every fresh clone re-discovers the workflow.
**Pros:** (a) closes the last fresh-clone-to-running-app friction point introduced by M5; (b) cheap (~1h CC); (c) a script-shape (option a) keeps production code clean — no dev-only code path in the production image; (d) makes the "M5 broke local dev" mental model false even for first-day contributors.
**Cons:** (a) one-time-per-contributor friction is bounded; (b) if implemented as a migration (option b), commits dev-only code into the production image (smell); (c) needs care around idempotency — running twice should not error or silently overwrite an existing user.
**Context:** Captured by Eng Review 2 (2026-05-06) of `prod-auth-enforcement-plan-20260504-213635.md`. Step 1.8 of the plan documents the env-var requirement after PR1 ships, but doesn't address the registration step. Where to start: add `backend/scripts/seed_dev_user.py` (or `backend/Makefile` target `make seed-dev-user`) that POSTs to `http://localhost:8000/auth/register` using credentials from `.env`, gated on `APP_ENV != production`. Document in `CLAUDE.md` under "Development Commands → First-time local setup."
**Effort:** S (human: ~half day / CC: ~1 hr)
**Priority:** P3
**Depends on:** M5 PR1 ships. Pair with the LESSONS.md / CLAUDE.md update from plan Step 1.8 so the seed-user step lives next to the env-var setup step.
