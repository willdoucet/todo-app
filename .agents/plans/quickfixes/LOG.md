# Quickfix log

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
