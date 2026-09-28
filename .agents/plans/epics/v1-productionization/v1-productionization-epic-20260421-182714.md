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

Status: ACTIVE (M1–M5 and M7 shipped, M6 subsumed, M8 in its last part: PR1a and PR1b shipped, PR2 in progress)

## Goal

Take the repo from local-only Docker Compose development to a secure v1 production
deployment for one household.

## Locked architecture and decisions

- Frontend: Vercel SPA at `mealy.dev`
- Backend: Fly.io with `web`, `worker`, and `beat` process groups at `api.mealy.dev`
- Database: Fly Postgres, the unmanaged Postgres Flex app `mealy-app-prod-db` (`flyio/postgres-flex:17.2`). Corrected in M8 PR2: the platform choice is unchanged, but it was never Fly's Managed Postgres product, and the restore commands differ (`infra/backup-restore-drill.md`)
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

### What M8 shipped against these (M8 PR2, 2026-09-25)

The criteria above are kept as written. This records what met each one, per the M8 plan's
[success criteria](../../features/prod-launch-release/prod-launch-release-plan-20260911-152356.md#success-criteria).

- **Runbook, smoke and rollback checklists.** Three documents, one per runbook type, instead
  of one mixed document:
  - `infra/RUNBOOK.md` (release gates, backend-first deploy, smoke, two-doctrine rollback);
  - `infra/incident-diagnostics.md`;
  - `infra/backup-restore-drill.md`.

  The smoke checklist is also a script, `infra/release-smoke.py`, and a daily
  `.github/workflows/ops-check.yml` runs its liveness, recoverability and edge groups between
  releases. Executed twice:
  - `v1-20260923-f0a8d81`, with the rollback dry-run;
  - `v1-20260924-f4a6814`, the first release with a migration.
- **Password-rotation CLI over `fly ssh console`.** `python -m app.cli.rotate_password`
  shipped in PR1b (#62), and ran end to end in production on 2026-09-26 (RUNBOOK §6 and its
  execution log): 9 refresh tokens revoked, the old password refused, the new one accepted.
  The access-token half was not exercised in production (the kept tab was not reloaded
  first); the integration tests cover it.
- **Backup-restore dry-run against a scratch Postgres.** Both paths ran on 2026-09-23, and
  both scratch clusters were destroyed:
  - volume snapshot, 68 s;
  - point-in-time from continuous backups, 50 s.

  Continuous backups were enabled the same day. Production had no restore point on
  2026-09-12.
- **Process-group counts reconciled.** Decided `web=1`, choosing cost over a second web
  machine. Scaled 2026-09-23 and pinned in `infra/fly-scale.json`
  (`{"web": 1, "worker": 1, "beat": 1}`). Smoke check 3 asserts it at every release; the
  daily cron does not run it (release-relative, M8 plan § NOT in scope). TECH_STACK agrees. "Production runs `web=2` today" above describes the state
  before M8.
- **The host gate records which check rejected a request.** One `app.gate` WARNING per
  rejection names one of six reasons, never the secret, and the 421 body is byte-identical
  across them (PR1b). The logged `ip` is `Fly-Client-IP` since #64, which is not yet
  deployed; TODOS.md P2 proves it at the next release.

## v1.1 (ops) scope contract

Written in M8 PR2 (2026-09-25). It resolves the parent plan's open item 8 ("plan the v1.1 scope
during M8, not after launch"). "v1.1 (ops)" is the operations follow-up to this epic. It is not
PRD §11's v1.1, which is product polish. This contract starts nothing: each row still enters
through `/office-hours` or `/quickfix` by its size. Every row names where it is tracked.

| Candidate | Decision | Why | Tracked in |
|---|---|---|---|
| App-layer rate limit on `/auth/login`, and the burst test against the edge rule | **In** | With break-glass on (Mode A), no WAF limit stands in front of argon2 on a 1 GB web VM, so this is the one control that stays when Cloudflare is out of the path: its per-account cap in full, its per-IP part only once it keys on an address the caller cannot set (per-IP keys on `CF-Connecting-IP` are forgeable then; the TODO's Cons (c)). The burst test proves the edge rule the limit sits behind | TODOS.md P2 × 2 |
| Structured logs for `/auth/*` and for protected-route 401s | **In** | The `/auth/*` lines reach `fly logs` as a bare event name. M8's gate line shows the shape to copy | TODOS.md P2 × 2 |
| Recovery-point lag and a real WAL check: `archive_timeout`, check 9 asserting continuous backups on their own, then a cron that can read them | **In** | The drill found the newest WAL recovery point up to ~2 h behind. Check 9 passes when either mechanism is recent, so nothing fails on a stalled archive, and the daily cron's read-only token cannot read WAL backups at all (M8 PR1b release) | TODOS.md P2 |
| A missing `/assets/*` chunk served as year-cached HTML | **In** | It turns every rollback into a Cloudflare purge plus cleared browser caches (RUNBOOK §5.1). Fixing `vercel.json` removes that step | TODOS.md P2 |
| Approval-gated `deploy.yml` release workflow | **Gated** | Starts once one release runs the manual runbook with no procedure fix. Both M8 releases still found fixes, and automating a procedure that is still changing would hide those fixes | TECH_STACK (`deploy.yml` row); this row |
| `visual-tests` as a required check on `master` | **Gated** | Starts once its two known failures are fixed (the report-server hang to the 25-min timeout; `mealcard-undo.spec.js` width, failing every run since 2026-09-24) and ten runs in a row pass | TODOS.md P2 × 2; P3 (nightly flake-rate) |
| Vercel PR previews | **Out** | `*.vercel.app` cannot receive the `__Host-refresh` cookie scoped to `api.mealy.dev`, so a preview is an unauthenticated shell. A `mealy.dev` subdomain is the only way it could work | TODOS.md P3 (preview subdomain) |
| Password rotation as a `workflow_dispatch` action | **Out** | CI would need a token that can `fly ssh` into production, a far larger standing credential than a once-a-year operator command is worth. `fly ssh console` stays the path (RUNBOOK §6) | none |
| Sentry or equivalent error reporting | **Out** | For one household, a third-party service and a new secret are not worth it. The silent failures v1 actually had are now covered by `ops-check.yml` and the Settings jobs card | TODOS.md P3 (frontend error reporting) |
| Scheduling the Cloudflare drift script | **Out** | The RUNBOOK checks the dashboard every release, and the daily cron already probes the origin lock and cache headers. Scheduling needs a CI-held Cloudflare token | none |

Not part of the contract, because it is operations work rather than scope: resuming the paused
Celery worker and beat (TODOS.md P1) comes before any v1.1 (ops) row.

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
