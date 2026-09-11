---
plan_kind: "epic"
registry_key: "epic:v1-productionization"
updated_at: "2026-09-09T22:10:05Z"
---
# Epic: v1 productionization

Generated at framework migration on 2026-09-09 from the productionization plan that was
approved by /office-hours on 2026-04-21 and reviewed (CEO, Eng x3, Adversarial) on the
`prod-contract-freeze` branch. That plan remains the full rationale and review record:
[prod-contract-freeze-plan-20260421-182714.md](../../features/prod-contract-freeze/prod-contract-freeze-plan-20260421-182714.md).
This file is the epic: it defines the milestones and never executes.

Status: ACTIVE (M1–M5 and M7 shipped, M6 subsumed, M8 not started)

## Goal

Take the repo from local-only Docker Compose development to a secure v1 production
deployment for one household.

## Locked architecture and decisions

- Frontend: Vercel SPA at `mealy.dev`
- Backend: Fly.io with `web`, `worker`, and `beat` process groups at `api.mealy.dev`
- Database: Fly managed Postgres
- Broker and result backend: Upstash Redis over TLS (`rediss://`)
- File storage: Cloudflare R2, single provider, no S3 fallback
- Tenancy: single-tenant per household, one deployment per family
- Auth: first-party email and password, JWT access token plus `__Host-refresh` HttpOnly cookie
- Merge strategy: squash-and-merge on `master`; direct push blocked by branch protection
- Sequencing rule: infra unknowns are discovered before auth code depends on them

## Milestones

| # | Milestone | Size | Branch | Depends on |
|---|---|---|---|---|
| M1 | Contract freeze: doc alignment, branch protection, squash-merge | plan | `prod-contract-freeze` | — |
| M2 | Deploy skeleton: Fly, Upstash, R2, Vercel, DNS, healthz, edge gate, plumbing test | plan | `prod-deploy-skeleton` | M1 |
| M3 | Auth backend foundation: models, argon2, register/login/refresh/logout/status | plan | `prod-auth-backend-foundation` | M2 |
| M4 | Auth frontend session: centralized API client, /auth portal, in-memory token, boot refresh | plan | `prod-auth-frontend-session` | M3 |
| M5 | Auth enforcement: protected router, route protection, remove plumbing test | plan | `prod-auth-enforcement` | M4 |
| M6 | Config health: residual localhost cleanup | quickfix | `prod-config-health` | M5 |
| M7 | R2 storage: storage abstraction, proxied uploads, private reads, remove StaticFiles mount | plan | `prod-r2-storage` | M6 |
| M8 | Launch release: manual runbook, smoke and rollback checklists, password-rotation CLI, backup-restore drill | plan | `prod-launch-release` | M7 |

Status per milestone is derived from the registry; see `IMPLEMENTATION_PLAN.md` Phase 2 or run
`.agents/bin/obsidian-workflow epic-get --slug v1-productionization`.

## Done when

M8 ships: a manual release runbook is committed, smoke and rollback checklists exist, the
operator password-rotation CLI works over `fly ssh console`, a backup-restore dry-run has been
executed against a scratch Postgres, and the two criteria below are met.

Both were added 2026-09-11, from what the origin-lock rollout exposed
(`infra/cloudflare-state.md`, LESSONS.md → *A Host-header check does not stop direct-to-origin
bypass*):

- **Process-group counts are reconciled, not merely checked.** `fly scale show` must agree with
  `fly.toml` and the docs. Production runs `web=2` today, not the `web=1` this milestone
  assumed (`worker=1` and `beat=1` are correct). Nothing pins the count: `fly.toml` sets
  `min_machines_running = 1`, which is a floor, not a cap. M8 either scales `web` back to 1, or
  keeps 2 deliberately and updates `fly.toml`, TECH_STACK, and this criterion to match. Each web
  VM is 1024 MB (sized for argon2), so running 2 doubles that spend; a second machine also
  widens the window in which a restart leaves two machines briefly holding different secret
  values, which is what made the 2026-09-11 rollout hard to diagnose. `beat=1` is the invariant
  that must not change — a second beat double-fires the iCloud sync schedule.
- **The production host gate records which check rejected a request.** One log line per
  rejection naming the failed check (host vs origin-verify, absent vs mismatched), never the
  secret value, and with the 421 response body unchanged so the two failure modes stay
  indistinguishable to a caller. They are currently indistinguishable to the operator as well:
  during the origin-lock rollout, a drifted secret and a mis-deployed Cloudflare rule looked
  identical from outside, and telling them apart cost a production experiment. This is one line
  on an existing gate for operability — not the broader structured-logging story deferred
  below.

## Deferred to v1.1

- Approval-gated `deploy.yml` release workflow (manual runbook first)
- Vercel PR preview deployments
- `visual-tests` as a required check on `master`
- Sentry, structured JSON logging, app-layer rate limiting beyond the edge rule
- Password-rotation CLI as a `workflow_dispatch` action

## Out of scope for v1

- Automated deploy on merge
- Full mirrored staging environment
- Multi-household, multi-user, invite flows, public signup
- Magic-link login, self-service password reset, social login
- Native apps or PWA install
- Any storage provider other than Cloudflare R2

## REVIEW REPORT

See the original plan's REVIEW REPORT and Adversarial Review Summary; those reviews cover this
decomposition.
