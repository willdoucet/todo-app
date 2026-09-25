# Quickfix log

## 2026-09-19 — prd-mealboard-shipped-status

- Source: free text (stale-doc finding split out of PR #55, which left it because it rewrites PRD narrative)
- What: mark the mealboard and shopping-list auto-sync as Built in PRD §5, and correct the factual drift found while verifying — aggregation bucket and unique index, count units, removal rule, pre-item-refactor data constraints, and the 1200px → 1280px nav breakpoint
- Why: IMPLEMENTATION_PLAN Phases 3.5–3.9 shipped April 2026 (commits `90cb121`…`e6d34ea`, PRs #18–#23) while PRD §5 still said "Rebuilding" and §5.5 called shipped code a "Planned Enhancement"; PRD §11 already marked the same items `[x]`, so the document contradicted itself
- Also: BACKEND_STRUCTURE's `DELETE /meal-entries/{id}` row claimed groceries are removed immediately — removal is scheduled at `UNDO_WINDOW_SECONDS + 1` and no-ops on undo. Fixed the `delete_meal_entry` docstring that the row came from; APP_FLOW:337 already had it right
- Files: .agents/docs/{PRD,APP_FLOW,BACKEND_STRUCTURE,LESSONS}.md, backend/app/crud_meal_entries.py
- Tests: tests/integration/test_meal_entries_api.py — 30 passed (Docker); only code change is a docstring, validated by AST parse in the api container
- Docs: updated 4 docs; doc-guard --staged --dry-run → would pass
- Follow-up: `test_delete_dispatches_shopping_removal` asserts the remove task is called but not its countdown, so the documented timing is not pinned by a test
- Branch: quickfix/prd-mealboard-shipped-status · PR: https://github.com/willdoucet/todo-app/pull/56

## 2026-09-11 — origin-verify-header
- Source: free text (M7 R2-cutover smoke-check finding)
- What: require a Cloudflare-set X-Origin-Verify header (matched against the ORIGIN_VERIFY_SECRET Fly secret) in the production host gate, so requests that skip Cloudflare and hit the Fly origin directly are rejected before reaching /auth/*
- Why: the gate compared only Host; Fly holds a cert for api.mealy.dev, so `curl --resolve` to the Fly IP bypassed Cloudflare's /auth/* WAF rate limit, the only brute-force/argon2-CPU control on the shared login
- Also: fixed a healthz-exemption Host-spoof bypass (scope["path"] vs request.url.path) found in security review; boot fails closed without a >=32-char secret
- Files: backend/app/main.py, backend/tests/integration/auth/test_host_gate.py, backend/tests/unit/test_origin_verify_bootstrap.py, infra/cloudflare-state.md, .agents/docs/{BACKEND_STRUCTURE,TECH_STACK,LESSONS,TODOS}.md
- Tests: backend suite 914 passed / 3 skipped (Docker); host-gate + origin-verify-bootstrap tests green; verified against a real uvicorn prod boot
- Docs: updated 4 docs; PRD §5.7 n/a (infra hardening, not product-visible auth)
- Operator: create the Cloudflare Transform Rule + Fly secret per infra/cloudflare-state.md before deploy (app fails closed without the secret)
- Branch: quickfix/origin-verify-header · PR: https://github.com/willdoucet/todo-app/pull/46

## 2026-09-11 — m7-cutover-record
- Source: free text (follow-up to the M7 R2 cutover, PR #44)
- What: record the executed R2 cutover and the Cloudflare Access Application 1 teardown; correct five runbook steps that could not run as written
- Why: M7's exit item closes only when the teardown is recorded; the runbook's header, OQ1, no-cookie curl, deploy, and sweep steps did not match what production could show
- Files: infra/r2-cutover-runbook.md, infra/cloudflare-state.md, .agents/docs/TODOS.md, .agents/docs/IMPLEMENTATION_PLAN.md, .agents/docs/TECH_STACK.md, .agents/docs/BACKEND_STRUCTURE.md, .agents/docs/LESSONS.md
- Tests: none (docs only); post-teardown checks through Cloudflare: /uploads/<key> 401, /tasks/ 401, /healthz 200, /auth/status CORS 200
- Docs: docs-only change; doc-guard passes
- Branch: quickfix/m7-cutover-record · PR: https://github.com/willdoucet/todo-app/pull/45

## 2026-09-11 — worker-outage-hardening
- Source: free text (M7 cutover sweep check found the worker machine stopped)
- What: restart policy + quieter Celery flags for the Fly worker/beat groups; sync-freshness dot in the iCloud settings card; naive-UTC timestamp parse fix; runbook `fly status` check
- Why: the worker had been stopped since at least the end of May (32,136 queued jobs, ~103 days of dead iCloud sync, soft-delete purge and upload sweep) and nothing surfaced it
- Files: backend/fly.toml, frontend/src/components/settings/ICloudSettings.jsx, frontend/tests/components/settings/ICloudSettings.test.jsx, infra/r2-cutover-runbook.md, .agents/docs/{LESSONS,TECH_STACK,FRONTEND_STRUCTURE,TODOS}.md
- Tests: frontend 550 passed; the 2 new sync-freshness tests fail without the parse fix ("just now"); lint 0 errors; local worker boots with the new flags
- Docs: TECH_STACK (Infrastructure), FRONTEND_STRUCTURE (Behavioral Notes), LESSONS (2 Bug Log rows + 2 rules), TODOS (widget closed, background-job health signal opened)
- Operator: fly.toml changes need a deploy; master carries #46, so do its Cloudflare Transform Rule + ORIGIN_VERIFY_SECRET steps first
- Branch: quickfix/worker-outage-hardening · PR: https://github.com/willdoucet/todo-app/pull/49

## 2026-09-11 — m8-acceptance-criteria
- Source: free text (findings carried out of the origin-verify-header rollout)
- What: fold two findings into M8's acceptance criteria — reconcile the process-group counts (production runs web=2, not the assumed web=1), and require the production host gate to record which check rejected a request
- Why: both surfaced during the origin-lock rollout and would otherwise be lost before M8 starts. The gate returns a byte-identical 421 for both failure modes, so a drifted secret and a mis-deployed Cloudflare rule were indistinguishable to the operator and cost a production experiment to tell apart
- Also: worded to avoid contradicting the v1.1 structured-logging deferral (one line on an existing gate, not the broader story); corrected the epic's stale header status
- Files: .agents/plans/epics/v1-productionization/v1-productionization-epic-20260421-182714.md, .agents/docs/IMPLEMENTATION_PLAN.md
- Tests: none (planning docs only)
- Docs: doc-guard — staged changes touch no documented areas. Registry milestone record deliberately untouched; criteria live in the epic body
- Branch: quickfix/m8-acceptance-criteria · PR: https://github.com/willdoucet/todo-app/pull/48

## 2026-09-14 — design-pin-sha-zsh
- Source: free text (LESSONS Bug Log 2026-09-14, found during /plan-design-review of M8)
- What: `design-sync-check --pin-sha [PATH ...]` prints the design pin SHA with each watched path as its own git argument, and exits 2 with the reason on stderr when there is none. plan-design-review, execute-plan, review-implementation, and design-review call it instead of the shell snippet
- Why: the snippet joined the watched files into one `$WATCHED` string; zsh does not word-split it, so `git log` matched nothing, exited 0, and the pin SHA came out empty
- Also: the same change, byte-identical, in ../framework/payload (uncommitted there, with README and CHANGELOG); the LESSONS Bug Log row stays on prod-launch-release to avoid a duplicate
- Files: .agents/bin/{design-sync-check,_design_sync.py}, .agents/tests/test_design_sync.py, .agents/skills/{plan-design-review,execute-plan,review-implementation,design-review}/SKILL.md, .agents/skills/plan-design-review/references/design-source-of-truth.md
- Tests: .agents/tests 273 passed; the 3 new pin-SHA tests failed before the fix; zsh and bash both print c0f7f30bcdfc1c6d2a2fdfeba8d39c6fa4c294cd
- Docs: no doc impact (all paths under .agents/, no documented surface changed)
- Branch: quickfix/design-pin-sha-zsh · PR: https://github.com/willdoucet/todo-app/pull/50

## 2026-09-14 — refresh-framework-manifest
- Source: free text (follow-up to #50)
- What: refresh `.agents/manifest.json` fingerprints for the 8 payload files #50 changed, via `framework upgrade` from framework main (ab156cd)
- Why: #50 hand-applied the framework change, so the manifest kept the 1.0.0 fingerprints and `framework doctor` warned "8 payload file(s) modified locally" for files identical to framework main
- Also: the upgrade's key reorder of two doc_map rules in config.json (no value change) was reverted; framework checkout moved to main with the merged branch deleted locally and on GitHub; prod-launch-release fast-forwarded to #50; its LESSONS Bug Log row (2026-09-14, pin SHA) updated with the fix
- Files: .agents/manifest.json
- Tests: `framework doctor` before 3 warnings incl. the modified-locally one, after 2 with it gone; helper tests pass
- Docs: no doc impact (manifest fingerprints only)
- Branch: quickfix/refresh-framework-manifest · PR: https://github.com/willdoucet/todo-app/pull/51

## 2026-09-15 — helper-list-design-sync
- Source: free text (noticed during #50)
- What: add `design-sync-check` and `design-sync-mark` to the host-side exceptions list in development-commands.md's Critical Rule
- Why: the list named six of the eight runnable helpers under `.agents/bin/`; skills now call `design-sync-check --pin-sha` for every design pin
- Files: .agents/docs/development-commands.md
- Tests: none (docs only); the listed names match the executable, non-underscore files in `.agents/bin/` exactly
- Docs: development-commands.md (Critical Rule) updated; AGENTS.md pointer unchanged
- Branch: quickfix/helper-list-design-sync · PR: https://github.com/willdoucet/todo-app/pull/52

## 2026-09-17 — m7-a1-adopt-plan-reconcile
- Source: free text (found while reading shipped plans for cross-review overrides; evidence case 2 for the workflow-rereview-utc plan)
- What: strike the never-shipped adopt-time rejection rule in the M7 `prod-r2-storage` plan (Adopt bullet + adversarial summary bullet) with a dated reconciliation note; correct the `asset_lifecycle` invariant docstring to "one key per entity, accepted not enforced"; pin the recipe form's one-key-in-two-columns flow with a test
- Why: the plan carried both Eng review A1 (accept shared keys) and the adversarial review's opposite rule (reject them); PR #44 shipped A1, so the plan claimed a control that never existed. Decided with the user: A1 stands. No behaviour change
- Files: .agents/plans/features/prod-r2-storage/prod-r2-storage-plan-20260715-201232.md, backend/app/services/asset_lifecycle.py, backend/tests/integration/test_asset_lifecycle.py
- Tests: test_asset_lifecycle.py::TestItemHooks::test_recipe_form_shares_one_key_across_icon_and_image; backend suite 915 passed, 3 skipped
- Docs: BACKEND_STRUCTURE.md (Code Organization) states the real adopt behaviour; LESSONS.md Bug Log row
- Branch: quickfix/m7-a1-adopt-plan-reconcile · PR: https://github.com/willdoucet/todo-app/pull/54

## 2026-09-19 — reconcile-stale-doc-status
- Source: free text (five doc contradictions noticed during the 2026-09-19 /final-review of an unrelated branch)
- What: fix the stale side of each: R2 runbook executed (TECH_STACK); M7 shipped 2026-09-11 (IMPLEMENTATION_PLAN ×2, PRD ×2); auth built in M3–M5 with JWT + argon2 + single-tenant isolation (PRD feature and security tables); meal entries soft-deleted with a 5-second in-place undo (APP_FLOW); index.css recipe-grid @media rules (FRONTEND_GUIDELINES)
- Why: each doc contradicted another doc in the set; code, the epic registry, and git log settled every case, and each stale line predated or coincided with the M7 merge
- Files: .agents/docs/TECH_STACK.md, .agents/docs/IMPLEMENTATION_PLAN.md, .agents/docs/PRD.md, .agents/docs/APP_FLOW.md, .agents/docs/FRONTEND_GUIDELINES.md
- Tests: none (docs only); re-grep for the stale phrases is clean; PRD.md:36 is byte-identical to prod-launch-release and `git merge-tree` against that branch is clean
- Docs: updated 5 docs; flagged, not fixed: PRD "Rebuilding" rows + 5.5 "Planned Enhancement (v1.1)" for shipped shopping auto-sync, BACKEND_STRUCTURE meal-entry DELETE "removal immediately" wording
- Branch: quickfix/reconcile-stale-doc-status · PR: https://github.com/willdoucet/todo-app/pull/55

## 2026-09-23 — pause-celery-worker
- Source: free text (M8 PR1a operator session, plan "Between the PRs" step 1)
- What: P1 TODOS entry recording that the mealy-app-prod `worker` and `beat` machines are stopped on purpose, with the resume steps
- Why: the worker had been down since a 2026-09-21 Fly host migration and crash-looped on the Upstash request cap (500,000) when started; PR #49 (restart `always`, low-usage worker flags) was never deployed. Without the record, a stopped worker looks like the next silent outage
- Files: .agents/docs/TODOS.md
- Tests: none (docs only); production state re-read 2026-09-23T17:18:47Z (worker and beat stopped, web started); resume commands checked against flyctl help and infra/incident-diagnostics.md
- Docs: no doc impact (TODOS.md entry only; no documented surface changed)
- Branch: quickfix/pause-celery-worker · PR: https://github.com/willdoucet/todo-app/pull/61

## 2026-09-24 — ops-check-fly-path
- Source: free text (M8 "Between the PRs" step 10, the first `ops-check` dispatch after the PR1b release `v1-20260924-f4a6814`)
- What: an "Expose flyctl as fly" step in `ops-check.yml` that links `$RUNNER_TEMP/flybin/fly` to `flyctl` and adds it to `$GITHUB_PATH`
- Why: `setup-flyctl` installs only `flyctl`, and `infra/release-smoke.py` runs `fly`; run 36009722470 exited 2 on `[9]` and `[5]` ("`fly` is not on PATH"). Laptops have both names through Homebrew, so no earlier run showed it
- Files: .github/workflows/ops-check.yml, infra/tests/test_ops_check_workflow.py
- Tests: infra/tests/test_ops_check_workflow.py (4: the reproduction with the script's own runner, the workflow's step run as `bash -e`, a missing flyctl fails the step, step order); red before the fix, `python3 -m pytest infra/tests -q` 165 passed after; two mutation checks red then restored; real runner: a dispatch from the branch (`gh workflow run ops-check.yml --ref quickfix/ops-check-fly-path`, run 36017858233) was green on the first attempt, `exit 0: 7 passed, 0 skipped, 1 paused`, with `[5] origin-lock` passing. `[9] restore-point` passed on the volume snapshot, with `also: fly pg backup list … unauthorized`: that read executes on the Postgres VM, which the read-only token cannot do, so the cron cannot see WAL backups. Not this fix's cause (the PATH bug hid it); recorded for M8 PR2 (RUNBOOK correction, a TODO for a narrow machine-exec token)
- Docs: updated 3 docs (TECH_STACK CI/CD row, LESSONS Bug Log, REVIEW_CHECKLIST GitHub Actions)
- Branch: quickfix/ops-check-fly-path · PR: https://github.com/willdoucet/todo-app/pull/63

## 2026-09-24 — gate-log-fly-client-ip
- Source: free text (production observation after the M8 PR1b release `v1-20260924-f4a6814`: both `host_gate` rejections logged the app's own anycast addresses as `ip`)
- What: the host gate logs `Fly-Client-IP` (the last copy) as `ip`; without it, the socket peer when there is no `X-Forwarded-For` either, else `"unknown"`
- Why: the last `X-Forwarded-For` entry it logged is Fly's own edge (`66.241.124.153` / `2a09:8280:1::10e:a0e0:0`, the A and AAAA records of `mealy-app-prod.fly.dev`), the same on every request, so `ip` named no sender
- Files: backend/app/gate_logging.py, backend/tests/integration/auth/test_host_gate.py
- Tests: test_host_gate.py::test_gate_ip_is_fly_client_ip_never_a_forwarded_entry (red first: logged `203.0.113.9`), plus the `"unknown"` fallback, last-copy and 128-cap tests; full backend suite 1059 passed, 3 skipped; two mutation checks each red on their own test; real uvicorn with `--proxy-headers --forwarded-allow-ips=*` printed the `Fly-Client-IP` value while its access line showed the forged `6.6.6.6`. Unproven until the next release: that Fly overwrites a client-sent `Fly-Client-IP` (TODOS.md P2 check, also in the PR body)
- Docs: updated 4 docs (BACKEND_STRUCTURE Production host gate, REVIEW_CHECKLIST FastAPI, LESSONS Bug Log + host-header rule bullet, TODOS release check)
- Branch: quickfix/gate-log-fly-client-ip · PR: https://github.com/willdoucet/todo-app/pull/64
