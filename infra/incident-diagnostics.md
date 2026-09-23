# Incident diagnostics

A lookup table, not a procedure: one entry per known failure mode, each with its symptom, the
signal that tells it apart from the others, and its recovery in order. Deep rationale lives in
the files it links, not here. Releasing is [`RUNBOOK.md`](./RUNBOOK.md). The restore drill is
[`backup-restore-drill.md`](./backup-restore-drill.md).

| | |
|---|---|
| Owner | willdoucet |
| Last reviewed | 2026-09-21 (written for M8 PR1a; never executed, because it is a lookup table) |
| Plan | `.agents/plans/features/prod-launch-release/prod-launch-release-plan-20260911-152356.md` (M8) |

Never run a bare `env` or `printenv` while diagnosing, on any machine (LESSONS.md). Filter on
the remote side: names only, or an existence check.

## Where a failure line sends you

Every `FAIL` line from `infra/release-smoke.py`, and every `ops-check` failure email, ends
with a link into this file.

| Check (smoke / ops-check) | Entry |
|---|---|
| `[1] healthz`, `[2] groups-started` | [Web or a process group is down](#web-or-a-process-group-is-down) |
| `[3] scale-reconciled` | [Machine counts drifted](#machine-counts-drifted) |
| `[4] worker-roundtrip`, `[jobs] jobs-fresh` | [Background jobs (dead worker or beat)](#background-jobs-dead-worker-or-beat) |
| `[5] origin-lock` | [421 from the origin gate](#421-from-the-origin-gate) |
| `[glass] break-glass-off` | [Break-glass: the origin gate during a Cloudflare outage](#break-glass-the-origin-gate-during-a-cloudflare-outage) |
| `[6] private-media-headers`, `[7] vercel-cache-headers` | [Cache headers changed](#cache-headers-changed) |
| `[8] commit-frontend`, `[8] commit-backend` | [Deployed commit does not match the release](#deployed-commit-does-not-match-the-release) |
| `[9] restore-point` | [No recent restore point](#no-recent-restore-point) |
| any `ERROR` line, `exit 2 tooling:` | [Tooling failures (exit 2)](#tooling-failures-exit-2) |

**The alert-fatigue rule.** A daily check that flaps trains its reader to ignore it, which is
worse than having no check. If `ops-check` produces a false failure, fix or remove the
check that produced it. Do not mute the workflow. The rule is strictest in the workflow's
first month.

**What logs cannot tell you.** Fly keeps logs for a short window, far shorter than three
weeks, and v1 has no log shipping (structured logging is a v1.1 item). A failure found days
later usually has no log left to read. The host gate's rejection line is not rate-limited, so
a scanner hitting the origin IP can fill that short window with noise. This is accepted.

---

## Web or a process group is down

- **Symptom:** the app does not load, or check 1 or check 2 fails.
- **Signal:**
  - `/healthz` fails by **both** paths: web itself is down. Read
    `fly status -a mealy-app-prod` and `fly logs -a mealy-app-prod --no-tail`.
  - It fails **only through Cloudflare**, while the Fly hostname answers 200: see
    [Cloudflare is down or degraded](#cloudflare-is-down-or-degraded).
  - Check 2 names a machine that is not `started`: a deploy leaves a stopped machine
    stopped. Nothing else says so, because `worker` and `beat` have no health check.
- **Recovery:**
  1. `fly machine start <id> -a mealy-app-prod`, for the machine check 2 names. Check 2
     never names a standby. Never start one by hand: a started `beat` standby is a second
     beat.
  2. `worker` and `beat` carry `[[restart]] policy = "always"`. If one stopped anyway, read
     why before starting it: `fly machine status <id> -a mealy-app-prod` (its events).
  3. Re-run `python3 infra/release-smoke.py --only=liveness` and confirm it exits 0. Until
     PR1b is live, `/healthz` has no `jobs` key, so add `--skip=healthz_jobs`.

## Machine counts drifted

- **Symptom:** check 3 fails with `<group>: expected N, found M`.
- **Signal:** counts are pinned in [`fly-scale.json`](./fly-scale.json) (`web=1`, `worker=1`,
  `beat=1`) and set with `fly scale count`, never by `fly.toml`. `min_machines_running` is
  a floor, not a cap.
- **Recovery:**
  - `beat` above 1 is **urgent**: every beat fires the iCloud sync schedule, so two double it.
    Run `fly scale count beat=1 -a mealy-app-prod`.
  - `web=2` means `fly deploy` recreated the platform default. Run
    `fly scale count web=1 -a mealy-app-prod`. Do not re-scale after every deploy; this
    check is the detector.
  - A group that `fly-scale.json` does not list, or a key that does not match
    `fly.toml [processes]`, means the file and the config disagree. Fix the file in a
    pull request; do not scale to match a typo.

## Background jobs (dead worker or beat)

This is the in-app name. From PR1b, Settings shows a **Background jobs** card, and the
`ops-check` email uses the same labels:

| Label (Settings, email) | Celery task (`beat_schedule`) | Runs every |
|---|---|---|
| iCloud calendar sync | `app.tasks.sync_all_icloud_integrations` | 10 min |
| iCloud reminders sync | `app.tasks.sync_all_reminders` | 10 min |
| Deleted item cleanup | `app.tasks.hard_delete_expired_soft_deletes` | hour |
| Unused photo cleanup | `app.tasks.sweep_abandoned_uploads` | hour |

A household report of "Unused photo cleanup is behind schedule" maps to
`sweep_abandoned_uploads`.

- **Symptom:** silence, not an error. The API stays healthy, beat keeps queueing, and jobs
  pile up in Upstash. On 2026-09-11 the worker had been stopped for 103 days and 32,136 jobs
  had queued.
- **Signal:** the **worker's** `succeeded` line, not beat's `Sending due task` line. Beat
  queueing proves nothing ran.
  ```bash
  fly logs -a mealy-app-prod --no-tail | grep -E 'Task app\.tasks\.[a-z_]+\[.*\] succeeded'
  ```
  Smoke check 4 proves the worker **now**. It enqueues `health_check` from a web machine
  and reads the result back.
  - `worker round-trip unverified` (30 s timeout): not yet proof of death. Check the queue
    depth first; a deep backlog delays `health_check`:
    ```bash
    fly ssh console -a mealy-app-prod -g web -C "/app/.venv/bin/python -c \"import sys; sys.path.insert(0, '/app'); from app.celery_app import celery_app; print('queue depth', celery_app.connection_for_write().default_channel.client.llen('celery'))\""
    ```
  - `worker round-trip failed on the machine: …OperationalError…`: the broker refused the
    connection. See [Upstash or broker failure](#upstash-or-broker-failure).
- **What the card and the cron say (from PR1b).** The card reads `/healthz.jobs`, and every
  row's `stale` flag is computed by the server. The heartbeat's error flag is stored in the
  same database whose failure it reports. So the card cannot tell a broken heartbeat
  recorder from a dead worker when the database itself is the problem:

  | Web reads `job_heartbeats` now? | Worker's writes | Card | `ops-check` |
  |---|---|---|---|
  | yes | success upsert fails, the error write lands | "Can't record job runs" once that row is stale | exit 1, stale labels plus "can't record runs" |
  | yes | both writes fail (worker cannot reach the database, handler bug) | rows age into "behind", then "Stopped"; no `write_error` | exit 1, stale labels |
  | no, last good read under 2 min old | any | last reading, with a "Couldn't refresh" footnote | passes or fails on that reading |
  | no, last good read over 2 min old, or never read | any | "Can't check right now" | exit 1 "web cannot read job_heartbeats" |

  "Stopped" therefore means the web reads fine and nothing is writing. **The tiebreaker** is
  the worker log's `Task … succeeded` lines next to the heartbeat handler's WARNING lines.
  If `succeeded` lines are present, the recorder is broken and the jobs are running. If they
  are absent, the worker or beat is dead.
- **Do not restart web to clear "Waiting" or "hasn't run yet".** A job that has never run
  is given 3× its interval from the moment *this web process* started. Restarting web (a
  crash, a deploy, or an operator restart while answering the alarm) re-arms that grace
  for every job still at NULL. The cron then goes quiet for up to 3 h while the worker may
  still be dead. Look at `fly status` for `worker` and `beat` first.
- **Recovery:**
  1. `fly status -a mealy-app-prod`, or smoke check 2, names the stopped `worker` or `beat`
     machine. Never a standby: starting a `beat` standby by hand runs two beats.
  2. If the queue holds a stale backlog (thousands of jobs), purge it **before** starting
     the worker, which begins replaying days of iCloud syncs the moment it is up (the
     2026-09-11 order). Run it on a web machine: `fly ssh console` needs a started machine,
     and web has the same image and secrets. The next beat tick requeues what is due:
     ```bash
     fly ssh console -a mealy-app-prod -g web -C "sh -c 'cd /app && /app/.venv/bin/celery -A app.celery_app purge -f'"
     ```
  3. Start the machine step 1 named: `fly machine start <id> -a mealy-app-prod`.
  4. Confirm a `succeeded` line for each of the four tasks within an hour (the two syncs
     within about 10 minutes).

## 421 from the origin gate

The production host gate (`backend/app/main.py`) returns the same
`421 {"detail":"host_not_allowed"}` body for every rejection, on purpose. A caller cannot
tell the checks apart.

- **Symptom:** real traffic, or check 5 through Cloudflare, gets 421. Or check 5
  straight-to-origin gets anything **other than** 421, which means the lock is open.
- **Signal (from PR1b).** One `app.gate` WARNING per rejection names the check that failed.
  It never includes the secret or the presented header value. Read the reason first,
  instead of guessing:
  ```bash
  fly logs -a mealy-app-prod --no-tail | grep '"event": "host_gate"'
  ```

  | `reason` | Means | Seen in production? |
  |---|---|---|
  | `public_api_host_unconfigured` | `PUBLIC_API_HOST` unset: operator misconfiguration | yes |
  | `host_mismatch` | a `Host` other than `api.mealy.dev` (for example the `*.fly.dev` name) | yes |
  | `origin_verify_absent` | no `X-Origin-Verify`: the request went around Cloudflare, or the Transform Rule is not applied | yes |
  | `origin_verify_mismatch` | the header is present but wrong: the Fly secret and the rule's value have drifted | yes |
  | `host_absent` | no `Host` header | **no.** uvicorn's HTTP layer answers 400 first. Defense in depth only |
  | `origin_verify_secret_empty` | empty `ORIGIN_VERIFY_SECRET` at request time | **no.** Production refuses to boot below 32 characters. Tests only |

  Do not wait for either of the last two; they cannot appear. Before PR1b the gate logs
  nothing, and the two drift cases look identical from outside.
- **Recovery:** the ordered steps in
  [`cloudflare-state.md` → Transform Rules — origin lock](./cloudflare-state.md#transform-rules--origin-lock-modify-request-header).
  `origin_verify_mismatch` → re-sync the Fly secret to the rule's value (step 1 there).
  `origin_verify_absent` through Cloudflare → the rule is not deployed or not matching
  (step 2 there).
- **Lock open** (the direct request is not 421): either the break-glass flag was left on
  (check `[glass]`, next entry) or the gate regressed. That second case is a release bug:
  roll back ([RUNBOOK §5](./RUNBOOK.md#5-rollback)).

## Break-glass: the origin gate during a Cloudflare outage

The gate fails closed by design, and every lever other than a deliberate flag still fails
closed. Blanking `ORIGIN_VERIFY_SECRET` makes the app refuse to boot. Blanking
`PUBLIC_API_HOST` 421s everything. Rolling back to a previous image no longer removes the
gate: every image since PR #46 contains it. `APP_ENV != production` is **not** a break-glass
either: it also disables fail-closed secret validation and re-derives CORS.

**There are two modes, and they are different problems.**

- **Mode A: Cloudflare's proxy or WAF is degraded, and DNS still resolves.** Grey-clouding
  the records sends traffic straight to Fly and Vercel. There is then no Transform Rule, so
  no `X-Origin-Verify`, and the gate 421s everything unless the flag is on.
  - **Status: not available until PR1b is deployed.** The `GATE_BREAK_GLASS` flag ships in
    PR1b. Against a PR1a image, `-e GATE_BREAK_GLASS=1` is a no-op.
  - **Blast radius while it is on.** There is no WAF rate limit on `/auth/*`, so argon2 on a
    1 GB web VM can be DoS'd by anyone who finds the origin. And `resolve_client_ip` trusts
    the attacker-supplied `CF-Connecting-IP`, so auth logs can be forged. Keep the flag's
    lifetime to minutes.
  - **Enable** (PR1b+). This takes about a minute and needs no build. `-e` overrides
    `fly.toml`'s `GATE_BREAK_GLASS = "0"` for this release only. Only the exact string `"1"`
    enables it. Run it from a checkout of the **running** release (its tag): `fly deploy
    --image` re-applies the checked-out `fly.toml [env]`, the trap RUNBOOK §5.2 describes:
    ```bash
    fly releases --image -a mealy-app-prod          # current image ref
    git checkout <running-release-tag>
    (cd backend && fly deploy -a mealy-app-prod --image <current-ref> -e GATE_BREAK_GLASS=1)
    ```
    Then grey-cloud both DNS records (Cloudflare → DNS → proxy status off). With the flag
    on, the gate still checks `Host` and skips only the origin-header check. Every
    admitted request logs one `app.gate` WARNING with `outcome="bypassed"`.
  - **Clear.** Orange-cloud the records again, then redeploy the image that is running,
    without `-e`, from the same checkout of the running release's tag. Its `fly.toml` sets
    `GATE_BREAK_GLASS = "0"`, and nothing new ships. A deploy from `master` would also
    release any merged but unreleased code or migration, past every RUNBOOK gate
    (/final-review, M8 PR1a):
    ```bash
    fly releases --image -a mealy-app-prod          # the running image ref, the one Enable deployed
    git checkout <running-release-tag>
    (cd backend && fly deploy -a mealy-app-prod --image <current-ref>)
    ```
    **The last step is always** to confirm the flag is off and the lock holds:
    ```bash
    curl -s https://api.mealy.dev/healthz        # expect "gate_break_glass": false
    python3 infra/release-smoke.py --only=edge   # expect exit 0; check 5 direct = 421
    ```
    If `gate_break_glass` is still `true`, the `-e` value stuck as a machine-level env. Do
    **not** `fly secrets set` it. A secret survives a rollback and overrides the toml.
    Override it on each web machine with the toml's own default. flyctl v0.4.102 can set
    a machine env but not remove one, and only `"1"` enables the flag:
    ```bash
    fly machine update <web-machine-id> -a mealy-app-prod --env GATE_BREAK_GLASS=0
    ```
    Repeat until `/healthz` reads false. Then record here that `-e` was sticky, so the next
    incident does not repeat it.
  - **Detection of a flag left on:** the daily `ops-check` asserts
    `/healthz.gate_break_glass` is false *and* that the direct-to-origin probe still 421s.
    `fly secrets list -a mealy-app-prod` must never show `GATE_BREAK_GLASS`.
  - **Rehearse it** only in a local `APP_ENV=production` compose run, never in production.
- **Mode B: Cloudflare DNS itself is down. Accepted risk for v1.** Neither hostname
  resolves, and grey-clouding does not help, because the records are still Cloudflare's
  DNS. The only reachable name is `mealy-app-prod.fly.dev`, which the `Host` check rejects.
  And a SPA on `*.vercel.app` is not same-site with the API, so the `SameSite=Strict`
  `__Host-refresh` cookie would not be sent and login breaks regardless. There is nothing
  to do but wait for Cloudflare and tell the household.

## Cloudflare is down or degraded

Cloudflare is a single point of failure in three places: DNS, the proxy, and the WAF rate
limit on `/auth/*`.

- **Symptom:** "nothing works", while `fly status` and the Vercel dashboard both look
  healthy.
- **Signal:** <https://www.cloudflarestatus.com> first. `https://mealy-app-prod.fly.dev/healthz`
  answering 200 while `https://api.mealy.dev/healthz` fails puts the fault at the edge.
- **The trap:** the documented fallback, grey-clouding the proxy so traffic goes straight to
  Fly and Vercel, **defeats itself on its own**. It removes the Transform Rule, so the gate
  421s every request, and it removes the `/auth/*` rate limit. Grey-cloud only together
  with the break-glass flag, and only in Mode A (previous entry). Before PR1b is deployed,
  there is no working fallback for the API. Wait.

## No recent restore point

- **Symptom:** none. The app is perfectly healthy, and `/auth/status` still returns
  `{"account_exists":true}`. Only check 9 (release and daily) sees it.
- **Signal:** both mechanisms are old or missing:
  ```bash
  fly volumes list --json -a mealy-app-prod-db                         # the volume id, at run time
  fly volumes snapshots list <vol> -a mealy-app-prod-db --json        # scheduled snapshots
  fly pg backup list -a mealy-app-prod-db                              # WAL / point-in-time backups
  ```
  Always pass `-a mealy-app-prod-db`. From `backend/`, flyctl infers `mealy-app-prod` from
  `fly.toml` and fails with "volume does not belong to app". `fly volumes list` hides
  detached volumes; add `--all` to see an outgoing one.
- **The usual cause: the database moved hosts, and the snapshot history did not follow.**
  A Fly host migration creates a new volume in a new zone, marks the old one
  `pending_destroy`, keeps the data, and resets the snapshot timeline to zero. Nothing warns
  you. `Scheduled snapshots: true` means only that the daily cycle will begin again. Found
  2026-09-12, when production was running with no restore point at all.
- **Recovery:**
  1. Confirm continuous backups are on. If `fly pg backup list` says they are not enabled,
     enable them:
     ```bash
     fly pg backup enable -a mealy-app-prod-db
     ```
  2. Wait for the first scheduled snapshot (daily) or the first WAL backup, and re-run
     `python3 infra/release-smoke.py --only=recoverability`.
  3. Treat "the volume id changed" as a backup incident. Record the gap, meaning the time
     with no restore point, in [`backup-restore-drill.md`](./backup-restore-drill.md)'s
     log. A new volume id is also one of the drill's re-run triggers.

## A real restore into production

This is different from the drill, which restores into a scratch app where none of this
applies. It is the one path in this milestone that can lose real data.

- **Why it is dangerous.** Restoring an older snapshot reverts `assets.referenced` for every
  object adopted after the snapshot. The hourly abandoned-upload sweep deletes
  `referenced = false` rows older than 24 h **together with their R2 objects**. So a
  restore followed by a running worker can delete live photos that a restored entity still
  points at. Objects created after the snapshot are the milder case: they have no manifest
  row, so the media route 404s them. They become unreadable, not deleted.
- **Recovery, in order:**
  1. **Stop the worker and beat before the restore:**
     `fly machine stop <worker-id> <beat-id> -a mealy-app-prod`. Beat does not replay
     missed schedules, so stopping both avoids a backlog when they restart. Both carry
     `[[restart]] policy = "always"`: confirm with `fly machines list -a mealy-app-prod`
     that both read `stopped`, now and again right before step 3. A worker that comes back
     runs the sweep this entry exists to prevent.
  2. Restore (the commands and traps are in the drill document; the target is a *new*
     cluster, and pointing the app at it is a `DATABASE_URL` secret change, which
     restarts web). Reshape the connection string the new cluster prints before setting
     it: `postgresql+asyncpg://` and `?ssl=disable` on the internal endpoint, never
     `sslmode=`. Pasted as printed, the app fails to connect
     ([LESSONS.md → Fly Postgres + asyncpg setup](../.agents/docs/LESSONS.md#fly-postgres--asyncpg-setup)).
  3. **Reconcile `assets` against the R2 bucket before anything runs.** For every object an
     entity row references (icons, photos, recipe images), make sure its `assets` row exists
     with `referenced = true`. List object keys that have no row. Use
     `fly pg connect -a <cluster>` for the SQL, and the R2 bucket listing in the Cloudflare
     dashboard.
  4. Only then start the worker and beat again, and confirm check 2.
- `job_heartbeats` rows restored with old timestamps read as behind until each job runs
  again. That is expected. A snapshot taken before the table existed has no table at all:
  the card reads "Can't check" until `alembic upgrade head` recreates it.

## Upstash or broker failure

- **Symptom:** iCloud sync stops (and so do the cleanups), while the web app stays healthy.
  Smoke check 4 fails with `worker round-trip failed on the machine: …OperationalError…`,
  or times out.
- **Signal:** Redis connection errors in the worker log (`redis.exceptions.ConnectionError`,
  `kombu` reconnect lines):
  ```bash
  fly logs -a mealy-app-prod --no-tail | grep -iE 'redis|kombu|OperationalError'
  ```
  Then look at the Upstash console for status and plan limits. Upstash bills per command.
- **Recovery:** once Upstash answers again the worker reconnects on its own, so restart it
  only if it does not (`fly machine restart <worker-id> -a mealy-app-prod`). Then confirm
  `succeeded` lines as in [Background jobs](#background-jobs-dead-worker-or-beat).

## Migration failure mid-release

- **Symptom:** `fly deploy` reports that `release_command` failed.
- **Signal:** the previous image is still serving. `fly status -a mealy-app-prod` shows the
  old version. Alembic runs the whole upgrade in **one transaction** on Postgres, so a
  failed upgrade leaves `alembic_version` where it was, unless a revision used an
  autocommit block (for example `CREATE INDEX CONCURRENTLY`). Check where production
  stands:
  ```bash
  fly ssh console -a mealy-app-prod -g web -C "sh -c 'cd /app && /app/.venv/bin/alembic current'"
  fly logs -a mealy-app-prod --no-tail | grep -i alembic
  ```
- **Recovery:** **forward-fix** is the default. Fix the revision in a new pull request and
  release it with the runbook. Nothing was released, so there is nothing to roll back. If
  the failure was a lock timeout on a revision that needed writers paused, redeploy with
  [RUNBOOK §3](./RUNBOOK.md#3-deploying-a-migration-that-requires-quiescing-writers).
- **Why `--skip-release-command` is mandatory when rolling back across a migration:** the
  previous image's Alembic tree does not contain the newer revision now stored in
  `alembic_version`. Its `alembic upgrade head` fails with "Can't locate revision", and a
  rollback that runs the release command aborts on exactly the case it exists for
  ([RUNBOOK §5.2](./RUNBOOK.md#52-backend-roll-back-the-code-never-the-schema)).

## Deployed commit does not match the release

- **Symptom:** check 8 fails on one tier.
- **Signal and recovery:**
  - **frontend, empty, or placeholder never substituted:** Vercel's "Automatically expose
    System Environment Variables" is off, so `VERCEL_GIT_COMMIT_SHA` never reached the
    build. `vercel.json`'s build command then sets `VITE_GIT_COMMIT` empty, and the tag
    reads `""`; the literal placeholder appears only when the variable is not set at all.
    Turn the setting on, redeploy, and promote.
  - **frontend, differs from the release in `frontend/`:** the promotion was forgotten, or
    the wrong staged deployment was promoted. Promote the one whose SHA equals the release
    commit (RUNBOOK §2 step 4). The check compares code, not commits: a release that did
    not touch `frontend/` passes on the previous build.
  - **backend, `unknown`:** the deploy ran without `--build-arg GIT_COMMIT` (from PR1b on,
    `/healthz` reports it). Redeploy with the argument.
  - **backend, differs from the release in `backend/`:** the deploy was skipped or failed,
    a different branch was deployed, or a rollback is in place. Deploy the release commit.
  - **"not in local history":** your checkout is behind. Run `git fetch` and re-run the
    check.

## Cache headers changed

- **Check 6** (a no-cookie private-media 401):
  - A `max-age` in `cache-control`, or anything other than `private, no-store`: Cloudflare's
    Browser Cache TTL is no longer "Respect Existing Headers", or the origin regressed.
    Reset it (Caching → Configuration). The logged-in 200 must also arrive as
    `private, no-cache`, which is RUNBOOK §2 step 7's DevTools check.
  - `cf-cache-status: HIT`: the edge cached a private-media response. Purge `/uploads/*`
    from the Cloudflare cache and find the rule that made it cacheable.
- **Check 7** (Vercel): `/index.html` or a SPA route without `max-age=0, must-revalidate`
  breaks the chunk-load recovery invariant. Real routes rely on Vercel's default (observed
  on `/mealboard` 2026-09-12). If that default changes, add a `headers` entry to
  `frontend/vercel.json` that matches SPA routes. `/assets/*` not `immutable` means the
  `vercel.json` asset rule changed.

## Postgres primary stops and starts hourly (open question 4)

- **Observed 2026-09-12:** the `mealy-app-prod-db` machine logs `exit stopped` and, about
  10 minutes later, `start starting proxy`, every hour. The Fly proxy wakes a machine that
  idled out. It is not yet known whether this is deliberate or a default that arrived with
  the host migration.
- **What it can cause:** connection errors that look like something else. `pool_pre_ping`
  (PR #30) absorbs most of them. Smoke check 4 can time out while the primary wakes: wait
  and retry once. From PR1b the web process reads `job_heartbeats` every 30 s, which will
  probably keep the primary awake; PR2 records which happened.

## Tooling failures (exit 2)

`exit 2 tooling:` means the check could not run. It says nothing about production.

- `fly` not on PATH, or older than v0.4.102: install or upgrade flyctl.
- The Fly token was rejected: `fly auth whoami`, then `fly auth login`. In `ops-check`
  (from PR1b), the `FLY_API_TOKEN` secret has expired (one-year token): create a new
  read-only token and record the rotation date in the RUNBOOK header.
- `fly ssh console` failed (tunnel, WireGuard): run `fly doctor`, then retry.
- `curl` could not resolve or connect: the network, not the app.
- A Cloudflare challenge page where JSON was expected: Bot Fight Mode or a managed
  challenge is intercepting the request. Its intended state is recorded in
  `cloudflare-state.md`.
- "did not print JSON" or "shape changed?": flyctl's output changed. Capture the new
  output, redact it, update `infra/tests/fixtures/`, and fix the parser. Never loosen a
  check until it passes.
- "restore point unverified": at least one restore mechanism could not be queried. It is
  never a pass.
- Cloudflare drift script: `CLOUDFLARE_API_TOKEN` is unset, or lacks a scope listed in the
  RUNBOOK header.
