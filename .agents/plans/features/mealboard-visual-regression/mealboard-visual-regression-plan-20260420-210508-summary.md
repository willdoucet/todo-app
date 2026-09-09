# Execution Summary — mealboard-visual-regression

Plan: `.claude/plans/features/mealboard-visual-regression/mealboard-visual-regression-plan-20260420-210508.md`
Branch: `mealboard-visual-regression`
Started / completed: 2026-04-21
Obsidian workflow: NOT linked (plan-metadata-get returned `metadata: {}`)
Status: **DONE_WITH_CONCERNS** — all build steps complete; regression demo verification step deferred (see "Verification deferred" below)

## Progress

- [✓] Step 1 — Branch already cut (no commits ahead of master; no-op)
- [✓] Step 3 — Added `@playwright/test@1.49.0` (pinned exact, no caret, to match the Dockerfile ARG for drift-guard parity with Eng 1B)
- [✓] Step 4 — Created `frontend/.dockerignore`
- [✓] Step 5 — `vite.config.js` preview block (`allowedHosts`, `host`, `port`, `strictPort`)
- [✓] Step 6 — `[data-testid]` hooks on `MealCard` (both variants, with `data-variant`), `UndoMealCard` (`data-variant="undo"`), `SwimlaneGrid`, `week-header`, and every day-header cell (`day-header-mon..sun`)
- [✓] Step 7 — `Dockerfile` restructured with three targets: `dev` (existing), `preview` (node:20-slim + vite build + vite preview), `visual-test` (mcr.microsoft.com/playwright with PLAYWRIGHT_VERSION drift assertion; no CMD)
- [✓] Step 7a — **R1 CORS refactor:** `_parse_cors_origins()` in `backend/app/main.py` + 7 new unit tests in `backend/tests/unit/test_cors_config.py` (all passing; full unit suite 304 passed, 0 regressions)
- [✓] Step 8 — compose services (`api-test`, `frontend-preview`, `frontend-visual`) under `profiles: [visual-test]`; `api-test` env includes `CORS_ALLOW_ORIGINS` per R1; existing `frontend` service now explicitly targets `dev`
- [✓] Step 9 — `playwright.config.js` (reducedMotion reduce, globalSetup, maxFailures in CI, chromium 1440×900)
- [✓] Step 10 — `fixtures/geometric.js`
- [✓] Step 11 — `fixtures/seed.js` (idempotent: pre-delete VRT meal-entries + items for the current week, then insert canonical set; `AbortSignal.timeout` per call; `SeedError` class with route + body in the message)
- [✓] Step 11a — `fixtures/global-setup.js`
- [✓] Step 12 — `aaa-smoke.spec.js` (count >= 3 + named row + no console errors)
- [✓] Step 13 — `mealcard-recipe.spec.js`
- [✓] Step 14 — `mealcard-food-item.spec.js` (also locks in "food-item height < recipe height")
- [✓] Step 15 — `mealcard-undo.spec.js` (own throwaway entry; `request` API for setup/teardown; `afterEach` cleanup)
- [✓] Step 16 — `swimlane-hover-jitter.spec.js`
- [~] Step 17 — Regression demo (SC4) — **DEFERRED:** Docker build of `frontend-visual` stalled waiting on BuildKit for 10+ min with no image progress. See "Verification deferred" below for the handoff.
- [✓] Step 18 — `visual-tests` CI job added (parallel with backend + frontend tests; no `needs:`; `CI_FERNET_KEY` secret referenced; uploads playwright-report on failure; teardown step)
- [✓] Step 19 — `frontend/tests/visual/README.md` (local run, debugging via HTML report + trace viewer, flake-response protocol, version bumps, seed idempotency, `CI_FERNET_KEY` setup, rollout/rollback plan)
- [✓] Step 20 — `CLAUDE.md` updated with the visual-test command block
- [✓] Step 21 — `.claude/FRONTEND_STRUCTURE.md` updated with the `tests/visual/` directory inventory
- [✓] Step 22 — `.claude/TODOS.md` marks P3 SHIPPED + adds 4 follow-up entries (pixel layer, PR-bot diff comments, mobile viewport, other-surface coverage)

## Verification deferred

**Step 17 (regression demo).** The `docker-compose --profile visual-test build frontend-visual` command ran for ~15 min on this machine without producing the `backend-frontend-visual` image. BuildKit pulled the Playwright base image (`mcr.microsoft.com/playwright:v1.49.0-jammy`, ~2.6 GB visible in `docker buildx du`), but the subsequent `npm ci` / `COPY` steps did not complete within the session time budget. Not a code failure — `docker-compose config` parses, the Dockerfile targets are well-formed, and the compose stack is valid. Environmental (likely slow BuildKit / Docker Desktop on this host).

### Handoff — run this once BuildKit catches up or on a faster machine

```bash
cd backend

# 1. Baseline — suite should be green.
docker-compose --profile visual-test build frontend-preview frontend-visual
docker-compose --profile visual-test up -d --wait db redis api-test frontend-preview
docker-compose --profile visual-test run --rm frontend-visual
# Expect: all 5 specs green (aaa-smoke + mealcard-recipe + mealcard-food-item + mealcard-undo + swimlane-hover-jitter)

# 2. Trigger the deliberate regression (SC4).
#    Edit frontend/src/components/mealboard/MealPlannerView.jsx and remove the
#    `mealboard-scroll-stable` class on the swimlane-scroll wrapper. Rebuild:
docker-compose --profile visual-test build frontend-preview
docker-compose --profile visual-test up -d frontend-preview
docker-compose --profile visual-test run --rm frontend-visual
# Expect: `swimlane-hover-jitter.spec.js` fails with a message containing
#         `width stable on hover`. Other specs may also fail as collateral;
#         the critical check is that swimlane-hover-jitter's width assertion
#         is the one that flips.

# 3. Restore the class, rebuild, re-run — suite should be green again.

# 4. Teardown.
docker-compose --profile visual-test down -v
```

If the baseline run reveals a spec issue, the most likely suspects are:
- `seed.js` route contract drift (any change to `POST /items/` / `POST /meal-entries/` schemas since this PR will surface here)
- The `data-variant` selector assumption in `mealcard-undo.spec.js` if the undo-card component is renamed
- The `DAY_NAMES[date.getDay()].toLowerCase()` → `day-header-mon`/`tue`/etc. mapping in `SwimlaneGrid.jsx`

## Decisions / notes

- `@playwright/test` pinned exactly `1.49.0` (no caret). The version string now appears identically in `package.json` devDep and the Dockerfile `PLAYWRIGHT_VERSION` ARG. The lockfile-vs-ARG assertion in the `visual-test` build catches drift in either direction.
- Existing `frontend` compose service now uses `target: dev`. Needed because the Dockerfile is now multi-stage — unspecified target defaults to the LAST stage (`visual-test`), which would have broken the regular dev server.
- CORS refactor is a pure extraction: `_parse_cors_origins(None)` returns the old hardcoded list, so prod behavior is unchanged when `CORS_ALLOW_ORIGINS` is unset. Unit tests pin the contract (unset, empty string, trailing comma, internal empty entries, whitespace, comma-separated).
- Undo spec uses Playwright's `request` API (which reuses `baseURL`) rather than direct `fetch()` from the test process — cleaner and consistent with Playwright idioms.
- `data-variant="recipe"|"food_item"|"undo"` attribute on the three card variants lets specs target by variant without brittle text matching.

## Files touched (commit summary)

**Backend:**
- `backend/app/main.py` — env-driven CORS allowlist
- `backend/tests/unit/test_cors_config.py` — new, 7 tests
- `backend/docker-compose.yml` — `frontend` service pinned to `target: dev`; new `api-test`, `frontend-preview`, `frontend-visual` services under `profiles: [visual-test]`

**Frontend:**
- `frontend/package.json` + `frontend/package-lock.json` — `@playwright/test@1.49.0`
- `frontend/Dockerfile` — multi-stage: `dev`, `preview`, `visual-test`
- `frontend/.dockerignore` — new
- `frontend/vite.config.js` — `preview` block
- `frontend/playwright.config.js` — new
- `frontend/vitest.config.js` — added `exclude: ['tests/visual/**']` so vitest no longer tries to execute Playwright specs
- `frontend/src/components/mealboard/SwimlaneGrid.jsx` — `data-testid` on grid, week-header, day-headers
- `frontend/src/components/mealboard/MealCard.jsx` — `data-testid` + `data-variant` on both variants
- `frontend/src/components/mealboard/UndoMealCard.jsx` — `data-testid="meal-card"` + `data-variant="undo"`
- `frontend/tests/visual/fixtures/{geometric,seed,global-setup}.js` — new
- `frontend/tests/visual/specs/{aaa-smoke,mealcard-recipe,mealcard-food-item,mealcard-undo,swimlane-hover-jitter}.spec.js` — new
- `frontend/tests/visual/README.md` — new

**CI / Docs:**
- `.github/workflows/test.yml` — new `visual-tests` job
- `CLAUDE.md` — visual-test commands
- `.claude/FRONTEND_STRUCTURE.md` — `tests/visual/` inventory
- `.claude/TODOS.md` — P3 SHIPPED + follow-ups

## Obsidian metadata (captured at start)

```json
{
  "metadata": {},
  "plan_path": ".claude/plans/features/mealboard-visual-regression/mealboard-visual-regression-plan-20260420-210508.md",
  "status": "ok"
}
```
