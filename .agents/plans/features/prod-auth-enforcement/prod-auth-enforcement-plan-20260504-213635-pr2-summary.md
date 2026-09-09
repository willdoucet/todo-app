# Implementation Summary — M5 prod-auth-enforcement (PR2)

**Plan:** `prod-auth-enforcement-plan-20260504-213635.md`
**Branch:** `prod-auth-enforcement-pr2`
**Scope of this run:** PR2 only (Steps 2.1, 2.2, 2.6). Steps 2.3-2.5 deferred to M7.
**Started + completed:** 2026-05-08

## Pre-execution context

- `obsidian-workflow plan-metadata-get` returned `metadata: {}` — this plan does NOT participate in the Obsidian workflow. No source-note sync required.
- `design-sync-check`: CLEAN (last synced 2026-05-08, design files unchanged since 218b0a25).
- Branch state at start: clean working tree, last commit `b42364d fix: HTTPS preserved across FastAPI trailing-slash redirects (#35)`. PR1 merged via #34.

## Critical scope adjustment vs. original plan

The original plan's PR2 scope (Steps 2.3-2.5) included a manual production deploy + Cloudflare Access policy removal. **2026-05-07 Cursor implementation review constraint** (recorded in `IMPLEMENTATION_PLAN.md` L169) reverses that: keep CF Access on the API host until M7's authenticated upload serving lands.

Reasoning: the wrapping `protected` APIRouter cannot gate the `/uploads` `StaticFiles` mount. Until M7 replaces that mount with R2 + auth-proxied reads, CF Access is the only thing preventing the open internet from fetching uploaded item images. The original plan's Premise 5 ("`/uploads/*` exposure window is acceptable for v1") was overruled by the Cursor review on a defense-in-depth basis: keeping CF Access on costs ~$0 ops nuisance; one leaked private upload (a screenshot, a Slack DM, a CF analytics log entry) is irrevocable.

PR2's revised scope on this branch:

- ✓ Step 2.1 — Code: remove plumbing-test surface
- ✓ Step 2.2 — PRD §5.7 + TODOS.md reconcile (with corrected wording: CF Access stays up until M7)
- ✗ Step 2.3 — Skipped (no deploy in this PR; CF Access stays up)
- ✗ Step 2.4 — Skipped (CF Access removal deferred to M7 exit)
- ✗ Step 2.5 — Skipped (no post-CF smoke needed; CF Access still in place)
- ✓ Step 2.6 — M5 plain-English summary (with corrected wording on CF Access lifecycle)

## Steps

### Step 2.1 — Backend: remove plumbing-test surface — `[✓]`

**File:** `backend/app/main.py`

- L10: removed `plumbing_test` from the `from .routes import ...` line.
- L180: removed `app.include_router(plumbing_test.router)  # Removed in M5 PR2.` line.

**File:** `backend/app/routes/plumbing_test.py` — `git rm`'d. The file's own header comment ("Deleted in M5 PR #2 along with the bypass policy") authorizes this.

**File:** `backend/tests/unit/test_plumbing_test.py` — `git rm`'d. Imports `COOKIE_NAME` and `PROBE_SAMESITE` from the deleted route module; pytest collection would have failed without removing it.

**File:** `backend/tests/unit/test_protected_router_propagation.py`

- `PUBLIC_PREFIXES` updated: dropped `"/plumbing-test"` from the allowlist. Now just `("/auth/",)`. After PR2, `/plumbing-test` is no longer a route — if it accidentally returned, the structural test would correctly flag it as a missing-auth regression.

**File:** `backend/.env.example`

- L10: stale doc reference to `/plumbing-test/*` as a public path removed (now reads `not /, /healthz, /auth/*, /uploads/*`).

### Step 2.1 — Frontend: remove plumbing shell + AppEntry indirection — `[✓]`

**File:** `frontend/src/main.jsx` — rewritten to render `<RouterProvider>` directly, with the `setRouter(router)` side-effect lifted from `AppEntry.jsx` (still idempotent at module-eval). No more env-gate; the M2 plumbing-shell branch is gone with `VITE_M2_SHELL`.

**Files deleted (all four had self-authorizing "Deleted in M5 PR #2" header comments):**

- `frontend/src/PlumbingShell.jsx`
- `frontend/src/AppEntry.jsx`
- `frontend/tests/components/PlumbingSmoke.test.jsx`
- `frontend/tests/components/App.shell-toggle.test.jsx`

**File:** `.claude/FRONTEND_STRUCTURE.md`

- L26-29: directory-tree block updated to drop `AppEntry.jsx` + `PlumbingShell.jsx` rows; `main.jsx` description rewritten to "binds router via setRouter(), renders <RouterProvider/> directly".
- L378: routing description rewritten — `main.jsx` calls `setRouter(router)` and renders `<RouterProvider/>` directly; the M2 env-gate description removed.

### Step 2.2 — PRD §5.7 + TODOS.md reconcile — `[✓]`

**File:** `.claude/PRD.md` §5.7 Route Protection row

Replaced the original `"Only /healthz and /auth/* remain public"` sentence with the corrected, expanded boundary (CF Access acknowledged as the `/uploads/*` backstop until M7; auto-docs called out as disabled, not allowlisted).

**File:** `.claude/TODOS.md` "P2 — `/uploads/*` asset auth strategy" entry

Marked **RESOLVED 2026-05-08** with a status block at the top: Strategy (a) chosen + acknowledgment that the Cursor implementation review (2026-05-07) overrides the original plan's Premise 5, so CF Access on `api.mealy.dev` stays up until M7 closes the loop.

**File:** `.claude/IMPLEMENTATION_PLAN.md` L169 (M5 entry)

Updated to:
- mark PR1 as ✓ shipped 2026-05-06 via #34
- spell out that CF Access removal is now an M7 exit step
- link to the plan and the new M5 plain-English summary

### Step 2.6 — M5 Plain-English learning summary — `[✓]`

**File:** `todo-app-notes/DevOps/Learning/M5 Auth Enforcement - Plain English Summary.md` (new)

7-section summary modeled on M4's structure:

1. One-paragraph milestone summary (M3 taught backend login, M4 taught frontend usage, M5 *requires* it)
2. Three user-facing questions (logged-in user, unauthenticated visitor, local-dev contributor)
3. The wrapping `protected` APIRouter pattern (with code from `main.py`, structural test, ordering rule for `/uploads/item-icon`, auto-docs disabled rationale)
4. The bypass-via-real-login design (with code from `auth-base.js`, why we rejected env-flag-in-`get_current_user`, why `__Host-refresh; Secure` couldn't be reused for tests, `.vrt-token` in `.gitignore`)
5. Why CF Access stayed during PR1 — and through PR2 (the Cursor reasoning generalized: wrapping pattern can't gate `StaticFiles`, asymmetric leak cost, M7 closes it)
6. The `auth_headers` fixture pattern (autouse `install_auth_config`, `auth_user`, direct `tokens.encode_access_token` mint, the asyncpg event-loop scope rationale)
7. What stays open after M5 (the `/uploads/*` mount and CF Access — both closed by M7)

### Verification — `[✓]`

**Backend test suite (`docker-compose run --rm api uv run pytest tests/unit tests/integration -q`):**

- **724 passed, 3 skipped, 56 warnings** — vs PR1's 728 passed, 3 skipped. The −4 delta is exactly the 4 tests in the deleted `test_plumbing_test.py`. No regressions elsewhere.
- The two key auth tests pass: `test_protected_router_propagation.py` (3 tests, structural) and `test_auth_enforcement.py` (3 tests, behavioral).

**Frontend test suite (`docker-compose run --rm --no-deps frontend npm run test:run`):**

- **544 passed across 57 test files** — vs PR1's 551 passing. The −7 delta is exactly the 4 tests in `PlumbingSmoke.test.jsx` + 3 tests in `App.shell-toggle.test.jsx`. No regressions elsewhere.

**Frontend production build (`docker-compose run --rm --no-deps frontend npm run build`):**

- ✓ built in 1.82s, 788 modules transformed.
- Bundle does NOT contain `PlumbingShell` or `VITE_M2_SHELL` references (verified with `grep` on `dist/assets/*.js`).

## Files changed

```
backend/app/main.py
backend/.env.example
backend/app/routes/plumbing_test.py                     [DELETED]
backend/tests/unit/test_plumbing_test.py                [DELETED]
backend/tests/unit/test_protected_router_propagation.py
frontend/src/main.jsx
frontend/src/AppEntry.jsx                               [DELETED]
frontend/src/PlumbingShell.jsx                          [DELETED]
frontend/tests/components/PlumbingSmoke.test.jsx        [DELETED]
frontend/tests/components/App.shell-toggle.test.jsx     [DELETED]
.claude/PRD.md
.claude/TODOS.md
.claude/IMPLEMENTATION_PLAN.md
.claude/FRONTEND_STRUCTURE.md
todo-app-notes/DevOps/Learning/M5 Auth Enforcement - Plain English Summary.md  [NEW]
```

## Things I didn't touch (intentionally)

- **Cloudflare Access policies on `mealy.dev` and `api.mealy.dev`** — stay up until M7 per the 2026-05-07 Cursor constraint.
- **`/plumbing-test` Bypass Application in CF** — drift, but harmless; tied to the same M7 cleanup pass.
- **`production_host_gate` middleware** — load-bearing separate concern (rejects direct *.fly.dev traffic).
- **`/uploads` `StaticFiles` mount** — replaced in M7, not now.
- **Historical M2/M3/M4 plan files referencing `VITE_M2_SHELL` / `PlumbingShell`** — frozen historical record per LESSONS.md "Merge review artifacts surgically".
- **Vercel `VITE_M2_SHELL` env var (if set in production)** — operator-side cleanup. The frontend code no longer reads it, so a stale env var is inert. Surface as a manual cleanup item in the PR description if the operator wants to remove it.

## Potential concerns / things to verify

- **Pre-existing dev-container restart loop:** `backend-api-1` was restart-looping on `cp: cannot stat '/app/stock_icons_src': No such file or directory` BEFORE I made any edits. It's a docker-compose entrypoint bug (the volume mount `./app:/app/app:ro` doesn't include `stock_icons_src`, and the entrypoint's `&&` chain stops on cp's non-zero exit). Unrelated to PR2; not in scope to fix here. Tests run cleanly via `docker-compose run --rm` (which spawns a fresh container outside the entrypoint loop).
- **Vercel env var `VITE_M2_SHELL`** — if it's still set in Vercel project settings, the new `main.jsx` doesn't read it. Inert, but worth removing for hygiene during the next ops touch.
- **CF Access `/plumbing-test` Bypass Application** — points at a route that's gone after PR2 deploys. Inert, but the policy line is drift; clean it up in the M7 ops pass.

## Next steps

1. Open PR2 against master with this branch. PR body should:
   - Note the Cursor-constraint-driven scope adjustment (CF Access stays through M7, not removed in PR2 as originally planned).
   - Cross-link to the plan, PR1's summary, this PR2 summary, and the new M5 plain-English summary.
   - Call out the inert Vercel `VITE_M2_SHELL` env var as a manual cleanup hint.
2. After PR2 merges, the operator can manually deploy frontend (Vercel) and backend (Fly) following the existing manual procedure. Smoke checks: `https://api.mealy.dev/plumbing-test` → 404; main bundle does not reference `PlumbingShell`. CF Access stays on; **do not** remove it.
3. CF Access removal moves to M7's exit checklist — once R2 + auth-proxied uploads ship and the `/uploads` `StaticFiles` mount is gone, CF Access is no longer load-bearing.
