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
