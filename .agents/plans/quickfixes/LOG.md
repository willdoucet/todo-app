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
