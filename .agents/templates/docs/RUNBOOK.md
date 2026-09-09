# Release Runbook

<!-- guidance: Not generated at init. Created by the first release phase and kept current by
/update-docs. Every step is a command or a check with an expected result; a release is closed
only when every box in Post-Release is ticked. Targets and their status live in TECH_STACK.md
→ Production Deployment; this file owns the procedure. -->

Owner: {{AUTHOR}} · Base branch: `{{DEFAULT_BRANCH}}` · Last drill: <!-- guidance: date of the last full dry run -->

## 1. Pre-flight

- [ ] `{{DEFAULT_BRANCH}}` is green in CI (every required check, including `doc-guard`)
- [ ] `.agents/bin/workflow-state --history` shows the phases this release ships, all `shipped`
- [ ] Migrations on the release commit: `<show pending migrations>` — list them below with their reversibility
- [ ] Required env vars present on every target, checked names-only (see LESSONS.md → the secrets rule): `<remote> env | grep "^<PREFIX>_" | cut -d= -f1`
- [ ] Backup taken and its id recorded: `<backup command>` → `<id>`
- [ ] Release notes drafted from the phase status lines in IMPLEMENTATION_PLAN.md

Migrations in this release:

| Revision | Purpose | Reversible | Downtime |
|---|---|---|---|
| | | | |

## 2. Deploy

<!-- guidance: one subsection per target in dependency order (database → backend → workers →
frontend). Each is: the command, what "done" looks like, and the check that proves it. -->

### 2.1 Database

```bash
<!-- guidance: migrate command against production, or "runs on backend start" with the log line to look for. -->
```

Expected: `<migration head>` matches the release commit.

### 2.2 Backend

```bash
<!-- guidance: build + deploy command; how to watch the rollout. -->
```

Expected: new version reported by `GET /healthz`; process counts as documented (`web=N, worker=N, scheduler=1`).

### 2.3 Background workers

<!-- conditional: keep when the stack has job workers. -->

```bash
```

Expected: worker log shows the release version and a successful heartbeat; exactly one scheduler.

### 2.4 Frontend

```bash
<!-- guidance: build + deploy, or "auto-deploys on merge" with where to watch. -->
```

Expected: the deployed bundle reports the release commit; API base URL is the production origin.

## 3. Smoke Checks

<!-- guidance: fast, read-mostly checks a human runs in under five minutes. Each has an
expected result. Include one authenticated flow when auth exists. -->

| # | Check | Command / action | Expected |
|---|---|---|---|
| 1 | API health | `curl -fsS https://<api>/healthz` | 200, version = release |
| 2 | Frontend loads | open `https://<app>/` | first paint, no console errors |
| 3 | Sign in | sign in with the operator account | lands on `/`, session persists on reload |
| 4 | Core write | create and delete one <entity> | appears, then disappears; no 5xx in logs |
| 5 | Background job | trigger one job | completes within <n>s; log line present |
| 6 | Upload | upload one file | stored, served, referenced |

## 4. Rollback

<!-- guidance: the fastest safe path back, with the trigger conditions. Code rollback first;
data rollback only when the migration table above says reversible. -->

Trigger: any smoke check fails, or error rate rises above <threshold> for <window>.

1. Backend: `<redeploy previous release>` — expected: `/healthz` reports the previous version
2. Frontend: `<promote previous deployment>` — expected: bundle reports the previous commit
3. Database: only if the release migration is marked reversible: `<downgrade one>`; otherwise restore from the pre-flight backup (section 6) and accept data loss since the backup id
4. Re-run Smoke Checks 1–3
5. Record the rollback in LESSONS.md → Infrastructure Post-Mortems

## 5. Secret Rotation

<!-- guidance: one row per secret: where it is set, the command to rotate it, what it
invalidates, and the order when several must rotate together. -->

| Secret | Set where | Rotate with | Invalidates | Notes |
|---|---|---|---|---|
| Signing secret | | | all sessions | |
| Database password | | | connections until restart | |
| Encryption key | | | data encrypted at rest — re-encrypt first | never rotate without a migration |

Operator password rotation: `<CLI command>` — bumps the session version so existing tokens are rejected immediately.

## 6. Backup / Restore Drill

Run before the first release and at least once per <interval>.

1. Create a backup: `<command>` → record the id
2. Restore it into a scratch database: `<command>`
3. Point a scratch backend at it and run Smoke Checks 1 and 4
4. Destroy the scratch resources: `<command>`
5. Record the date at the top of this file

Expected total time: <n> minutes. If it exceeds <m>, open a TODOS.md item.

## 7. Post-Release

- [ ] Smoke Checks all passed and are recorded with the release date
- [ ] Process counts verified (`web`, `worker`, `scheduler`)
- [ ] Error rate and latency at baseline for <window>
- [ ] IMPLEMENTATION_PLAN.md status lines show `shipped <date> (#PR)` for every phase in the release
- [ ] TECH_STACK.md → Production Deployment rows say `live`
- [ ] Anything that surprised you is in LESSONS.md; anything deferred is in TODOS.md
- [ ] Next drill date set

## Release Log

| Date | Release | Phases | Rollback? | Notes |
|---|---|---|---|---|
| | | | | |
