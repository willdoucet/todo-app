# M8 — `prod-launch-release` — execution summary

- Plan: .agents/plans/features/prod-launch-release/prod-launch-release-plan-20260911-152356.md
- Test artifact: .agents/plans/testing/prod-launch-release-test-artifact.md
- Branch: prod-launch-release
- Started: 2026-09-21T22:40:22Z
- Metadata: {"plan_kind":"feature","plan_mode":"feature","registry_key":"plan:prod-launch-release","parent_epic":"v1-productionization","milestone":"M8","ui_scope":true,"risk_tags":["infra","security","auth","data","migration"],"implementation_status":"implementing","review_status":["ceo-reviewed","eng-reviewed","adversarial-reviewed","design-reviewed"],"workflow_status":"implementing"}
- Gate: `workflow-state --next` named `/execute-plan`, `unreadable == 0` (cleared for implementation).
- Epic: `v1-productionization` M8; inherited constraints read (plan § Inherited constraints).
- Design source of truth: HTML mockup `mockups/background-jobs-card-option-a.html` present;
  `design-sync-check --pin-sha` printed `628891f08a93549a472a78ce8b7dfcf81baf735c`, equal to
  the plan's pin (no drift warning). `modules.design_sync` is `false`.

## Scope of this run: PR1a

The plan ships in sequence (Eng review 0): **PR1a** (docs, scripts, config; no application
code, no migration), then the operator's "Between the PRs" steps 0–6, then **PR1b** (gate
logging, rotation CLI, `/healthz` version and jobs, `job_heartbeats`, Settings card,
`ops-check.yml`), steps 7–11, then **PR2** (evidence and corrections). This run implements
PR1a only and stops at ready-for-review, following the M7 precedent (PR1 summary, ship, then
a second run). PR1b is a later `/execute-plan` run that reconciles this file and appends its
own steps.

## Scope of this run: PR1b

- Started: 2026-09-23T17:59:05Z (the start sync), after PR1a merged as #60 (squash `91edffa`); `origin/master`
  (`f0a8d81`, with #61) merged into the branch as `37334a5`.
- Metadata: {"implementation_status":"partially-shipped","milestone":"M8","parent_epic":"v1-productionization","plan_kind":"feature","plan_mode":"feature","pr":"https://github.com/willdoucet/todo-app/pull/60","registry_key":"plan:prod-launch-release","review_status":["ceo-reviewed","eng-reviewed","adversarial-reviewed","design-reviewed","impl-reviewed","final-reviewed"],"risk_tags":["infra","security","auth","data","migration"],"ship_parts":["PR1a","PR1b","PR2"],"shipped_parts":[{"commit":"6f0a608","part":"PR1a","pr":"https://github.com/willdoucet/todo-app/pull/60","shipped_at":"2026-09-23T16:07:56Z"}],"ui_scope":true,"workflow_status":"partially-shipped"}
- Gate: `workflow-state --next --json` named `/execute-plan`, `unreadable == 0`. #60 `MERGED`.
- Design source of truth: mockup present; `design-sync-check --pin-sha` printed
  `628891f08a93549a472a78ce8b7dfcf81baf735c`, equal to the plan's pin.
- Scope (plan § Recommended Approach, Eng review 0): items 5, 6, 13, 14, 15, 15a, the
  `GATE_BREAK_GLASS` flag, the `job_heartbeats` migration, and every test. Plus the user's
  approved addition of 2026-09-23: a checked-in pause declaration (`infra/paused.json`) that the
  smoke script and `ops-check.yml` read, because production's worker and beat are paused on
  purpose at the Upstash request cap (TODOS.md P1).

## Scope of this run: PR2

- Started: 2026-09-25T03:01:22Z (the start sync), after PR1b merged as #62 (squash `f4a6814`,
  `MERGED` 2026-09-24T04:02:36Z); `origin/master` (`56e0c39`, with #63 and #64) already merged
  into the branch as `f72e3f3`. Local `master` was behind (`29f4b75`) and was fast-forwarded to
  `56e0c39` so every `$BASE_BRANCH` diff is against the real base.
- Metadata: {"implementation_status":"partially-shipped","milestone":"M8","parent_epic":"v1-productionization","plan_kind":"feature","plan_mode":"feature","pr":"https://github.com/willdoucet/todo-app/pull/62","registry_key":"plan:prod-launch-release","review_status":["ceo-reviewed","eng-reviewed","adversarial-reviewed","design-reviewed","impl-reviewed","final-reviewed"],"risk_tags":["infra","security","auth","data","migration"],"ship_parts":["PR1a","PR1b","PR2"],"shipped_parts":[{"commit":"6f0a608","part":"PR1a","pr":"https://github.com/willdoucet/todo-app/pull/60","shipped_at":"2026-09-23T16:07:56Z"},{"commit":"394dccf","part":"PR1b","pr":"https://github.com/willdoucet/todo-app/pull/62","shipped_at":"2026-09-24T03:39:26Z"}],"ui_scope":true,"workflow_status":"partially-shipped"}
- Gate: `workflow-state --next --json` named `/execute-plan`, `unreadable == 0`. #62 `MERGED`.
- Design source of truth: mockup present; `design-sync-check --pin-sha` printed
  `394dccf02ea348e66d02b512c1c0536aec97be81`, not the plan's `628891f…` (PR1b's own commit
  touched a watched file). PR2 changes no UI, so the warning has nothing to act on.
- Scope (plan § PR2 — evidence and corrections): the Between the PRs 7–11 evidence recorded
  above folded into the runbooks, every correction the execution revealed, the M7 runbook's two
  open items, the v1.1 scope contract (parent plan open item 8), and the epic, roadmap and
  TODOS reconciliation. Documentation only: no application code, no migration.

## Steps
- [✓] Step 1 — Pin the scale: `infra/fly-scale.json` `{"web": 1, "worker": 1, "beat": 1}` and the `backend/fly.toml` comment pointing at it (item 7) (2026-09-21T23:06:20Z)
- [✓] Step 2 — `infra/release-smoke.py` (nine checks, four groups, exit 0/1/2, `--only`, `--skip`, `--release-commit`, `--self-test`, the `/healthz.jobs` contract reader) with `infra/tests/test_release_smoke.py` (item 4; Eng 2.3, 2.4, 3A) (2026-09-21T23:15:05Z)
- [✓] Step 3 — `infra/cloudflare-drift.py` (read-only diff against `cloudflare-state.md`, structural redaction) with `infra/tests/test_cloudflare_drift.py` (item 9; CEO 3G) (2026-09-21T23:18:04Z)
- [✓] Step 4 — Check 8's frontend tier and CI: `<meta name="build-commit">` in `frontend/index.html`, `buildCommand` in `frontend/vercel.json`, a `VITE_GIT_COMMIT` build-and-grep step in `frontend-tests`, a new `infra-tests` job (item 4 check 8; Eng 1.5, 3A) (2026-09-21T23:19:32Z)
- [✓] Step 5 — `infra/RUNBOOK.md`: the release procedure, deploy order, migration listing, rollback doctrines, execution log (item 1) (2026-09-21T23:22:12Z)
- [✓] Step 6 — `infra/incident-diagnostics.md`: one entry per known failure mode (item 2) (2026-09-21T23:25:45Z)
- [✓] Step 7 — `infra/backup-restore-drill.md`: both restore paths, the volume-move failure mode, execution log (items 3, 12) (2026-09-21T23:27:17Z)
- [✓] Step 8 — `infra/cloudflare-state.md`: replace the expired break-glass line with a pointer; record Bot Fight Mode for the drift script (item 2, Eng 7; item 4) (2026-09-21T23:28:06Z)
- [✓] Step 9 — `.agents/config.json` doc_map: route `backend/app/cli/**`, `gate_logging.py`, `job_health.py`; exempt `infra/*.md` with the reasoning recorded (item 10) (2026-09-21T23:28:44Z)
- [✓] Step 10 — PR1b: host-gate rejection reasons: pure `gate_reason()` in `main.py` (six reasons, decision-tree comment), `backend/app/gate_logging.py` emitter under `app.gate`, wrapped so it never changes a 421 (item 5; Eng 2.2, CEO 2A) (2026-09-23T18:13:08Z)
- [✓] Step 11 — PR1b: `GATE_BREAK_GLASS` flag: `fly.toml [env]` `"0"`, strict parse, bypass skips only origin-verify and logs `outcome="bypassed"` (open question 3; Eng 7) (2026-09-23T18:14:43Z)
- [✓] Step 12 — PR1b: `/healthz` reports `version` and `gate_break_glass` with `Cache-Control: no-store`; `GIT_COMMIT` build arg in the Dockerfile's `prod` stage; `test_healthz.py` rewritten (item 14; CEO 5D, Eng 1.2, 2.6) (2026-09-23T18:16:17Z)
- [✓] Step 13 — PR1b: `JobHeartbeat` model and the additive `job_heartbeats` Alembic revision with a real `downgrade()` (open question 6; Eng 1A, Eng 4 2A) (2026-09-23T18:17:26Z)
- [✓] Step 14 — PR1b: `backend/app/job_health.py` (`beat_intervals()`, `JOB_LABELS`, `build_jobs_payload`, refresher) and `/healthz.jobs` per the pinned contract, from memory only (item 15; Eng 1.2, Eng 4, Eng 5) (2026-09-23T18:24:19Z)
- [✓] Step 15 — PR1b: `task_postrun` heartbeat writer: SUCCESS and `beat_schedule` names only, upsert, error write, clears on success (item 15; Eng 3, Adversarial) (2026-09-23T18:26:57Z)
- [✓] Step 16 — PR1b: password rotation: `auth/service.rotate_password` (one commit, inside `logout`) and `backend/app/cli/rotate_password.py` (item 6; Eng 2.1, CEO 2D) (2026-09-23T18:30:32Z)
- [✓] Step 17 — PR1b: smoke script: the pause declaration `infra/paused.json` (user-approved addition), and check 1 asserting `/healthz` reports a version (item 13) (2026-09-23T18:36:05Z)
- [✓] Step 18 — PR1b: `.github/workflows/ops-check.yml`: daily schedule and `workflow_dispatch` with `self_test`, retry once, read-only Fly token (item 13; CEO 8A, 2F, Adversarial) (2026-09-23T18:37:20Z)
- [✓] Step 19 — PR1b: shared `frontend/src/lib/serverTime.js` and `FreshnessDot.jsx`; `ICloudSettings.jsx` consumes them (sage dot, secondary gray) (item 15; CEO 4B-A, Design 5A, 6A) (2026-09-23T18:39:01Z)
- [✓] Step 20 — PR1b: `useBackgroundJobs.js` with the pure `deriveJobsState(jobs, now)` on a server-aligned clock (item 15a; Eng 4, Eng 5) (2026-09-23T18:42:34Z)
- [✓] Step 21 — PR1b: `BackgroundJobsSection.jsx`, `BackgroundJobsAlert.jsx`, Settings page header and mount, MSW `/healthz` default handler (item 15a) (2026-09-23T18:59:31Z)
- [✓] Step 22 — PR1b: sign-in bounce banner copy with the likely causes (item 6, Design review 10) (2026-09-23T19:00:04Z)
- [✓] Step 23 — PR1b: runbooks for the PR1b surfaces: RUNBOOK password rotation, `FLY_API_TOKEN`, break-glass availability, the pause; diagnostics entries for gate reasons, the jobs card and cron, the pause (items 1, 2, 13) (2026-09-23T19:02:30Z)
- [✓] Step 24 — PR2: `infra/RUNBOOK.md`: the `v1-20260924-f4a6814` execution-log row and "Last executed"; the procedure fixes from steps 7–10 (`${RELEASE:?}`, keep or verify the migration output, late scheduled runs, who runs production commands, §0 "Save, then reload"); the `FLY_API_TOKEN` first-run criterion rewritten for the read-only token's WAL gap (2026-09-25T03:17:27Z)
- [✓] Step 25 — PR2: `infra/incident-diagnostics.md`: break-glass available since `v1-20260924-f4a6814` and its local rehearsal command (step 11); the Cloudflare-down entry; the `also: … unauthorized` WAL line; open question 4 recorded as observed (2026-09-25T03:20:05Z)
- [✓] Step 26 — PR2: `infra/backup-restore-drill.md` §0: the corrections from enabling backups (the 512 MB floor, the interactive Tigris terms prompt, `fly secrets deploy` after enable) (2026-09-25T03:20:53Z)
- [✓] Step 27 — PR2: `infra/r2-cutover-runbook.md`: strike the `fly status` box citing `git log -S`; re-record the sweep's `succeeded` line as open behind the worker pause (2026-09-25T03:21:26Z)
- [✓] Step 28 — PR2: the v1.1 scope contract (parent plan open item 8): written into the epic, the parent plan's item 8 closed with a pointer, IMPLEMENTATION_PLAN's deferred list aligned (2026-09-25T03:22:38Z)
- [✓] Step 29 — PR2: epic and roadmap reconciliation: epic status line and M8 Done-when matched to what shipped, "Fly managed Postgres" corrected to unmanaged Flex 17.2 (epic, IMPLEMENTATION_PLAN, PRD), IMPLEMENTATION_PLAN Phase 2 text (2026-09-25T03:23:53Z)
- [✓] Step 30 — PR2: TODOS.md and LESSONS.md reconciliation: the `machine-exec` token TODO linked to the WAL-lag P2, M8 entries closed or re-pointed, the 2026-09-23 worker incident in the Bug Log (2026-09-25T03:25:13Z)

## Step notes

Assumptions 1–13 (stated at step 7 of the skill) were approved by the user as written,
PR1a only. Fixtures are built from flyctl's documented shapes; no production call is made
during implementation (assumption 5).

### Step 1 — scale pin
- Files: `infra/fly-scale.json` (new), `backend/fly.toml` (comment on the `beat` process
  line; the stale "enforced via `fly scale count beat=1` post-deploy" sentence replaced).
- Decision: the comment says counts are out-of-band, names the file and smoke check 3, and
  repeats that `min_machines_running` is a floor.
- Verification: `tomllib` still parses `fly.toml`; `set(fly-scale.json) == set([processes])`
  (`beat`, `web`, `worker`); `doc-guard --explain` routes both files to TECH_STACK →
  Infrastructure.
- Not done here, by design: `fly scale count web=1` is Between-the-PRs step 1 (operator).

### Step 2 — release smoke script
- Files: `infra/release-smoke.py` (new, executable, stdlib only);
  `infra/tests/conftest.py`, `infra/tests/test_release_smoke.py`,
  `infra/tests/fixtures/{healthz_healthy.json, fly_machines_list.json, fly_ips_list.json,
  fly_volumes_list.json, fly_volumes_snapshots_list.json, fly_pg_backup_list.txt, README.md}`.
- Shape: one `Runner` seam for every `fly`, `curl` and `git` call; a memoized `Context`, so
  `/healthz` and the machine list are read once per run; twelve registered assertions
  (checks 1–9, plus `jobs-fresh` and `break-glass-off`, with check 8 split into its frontend
  and backend tiers so the backend tier alone is skippable); the group × exit class ×
  `--skip` matrix is in the module docstring (the plan's inline-diagram row for this file).
- Decisions within the plan's latitude:
  - Check 6 is the credential-free half (assumption 4): a no-cookie
    `/uploads/stock_icons/release-smoke.png` through Cloudflare must be a 401 carrying
    `private, no-store` unmodified, no `max-age`, and not `cf-cache-status: HIT`. The
    logged-in `private, no-cache` check stays a manual DevTools step (RUNBOOK, step 5).
  - Check 9's WAL half reads timestamps out of `fly pg backup list` (no `--json` in
    v0.4.102), not columns. A "not enabled" error means disabled, and any other error
    means exit 2. The check passes if either mechanism is under 48 h. With neither recent
    and one mechanism unverifiable it is exit 2, never a pass. With both answered and
    neither recent it is exit 1.
  - Check 4 runs `fly ssh console -a mealy-app-prod -g web -C '/app/.venv/bin/python -c "…"'`
    with `sys.path.insert(0, '/app')`, so it does not depend on the remote cwd. A Celery
    `TimeoutError` gives exit 1 "worker round-trip unverified". Any other failure without
    the result marker gives exit 2.
  - Check 8 treats a deployed SHA missing from local history as not an ancestor (exit 1),
    with a `git fetch` hint.
  - `--release-commit` is required when the release group runs, and is resolved with
    `git rev-parse --verify` (assumption 6).
  - `--self-test` runs exactly one check, against a built-in bad fixture, through a runner
    that refuses every command. The failing check is 3 (release), `jobs-fresh`
    (liveness), 9 (recoverability) or `break-glass-off` (edge), chosen as the first
    selected group in that order. The last line still reads `exit 1 production:`, which
    criterion 17's email check relies on.
  - Every FAIL line links a `infra/incident-diagnostics.md#<anchor>`, and every ERROR line
    links `#tooling-failures-exit-2`. Step 6 must create those headings, and a test there
    pins them.
- Verification: `python3 -m pytest infra/tests/test_release_smoke.py -q` → **72 passed**.
  Mutation check: five deliberate bugs, each applied alone and then restored (the file was
  `cmp`-identical afterwards), and each turned the suite red. The five were skipped
  reported as pass (1 failed), 429 treated as pass (1), stale rows checked before the
  unusable rule (2), self-test reaching the runner (4), and a missing `stale` read as
  fresh (2). CLI on the host, without contacting production: `--self-test` gave exit 1
  naming `[3] scale-reconciled`; `--only=liveness,recoverability,edge --self-test` gave
  exit 1 naming `[jobs] jobs-fresh`; `--only=release` without `--release-commit` gave
  exit 2; an unknown `--skip` key gave exit 2.
- Test-artifact coverage: every `release-smoke.py` bullet under Key interactions is
  covered, and so is the jobs half of critical paths 12, 16 and 17. Gap, by design: no
  fixture was captured from production, so the first real run is the integration point
  for the flyctl shapes (the fixtures README says so).

### Step 3 — Cloudflare drift script
- Files: `infra/cloudflare-drift.py` (new, executable, stdlib `urllib` only);
  `infra/tests/test_cloudflare_drift.py`; five `infra/tests/fixtures/cloudflare_*.json`
  following the v4 response envelope.
- It compares five things: the WAF rate-limit rule (expression, 5 / 10 s, per IP via
  `ip.src`, block, 10 s, enabled), the origin-lock Transform Rule (present, enabled,
  expression, and that it *sets* `X-Origin-Verify`), Browser Cache TTL (0 = Respect Existing
  Headers), Access applications (the ones the file does not mark REMOVED, so 0 today), and
  Bot Fight Mode. Bot Fight Mode is reported but counts as drift only once the file records
  an intent (assumption 8).
- Intent is read from named fields of `cloudflare-state.md`: account and zone ids, the
  `Threshold:` / `Action:` / `Duration:` / `Status:` / `Match:` lines, the Transform Rule's
  name, expression and header name, and the Browser Cache TTL setting. A missing field is
  exit 2, meaning the file's shape changed (assumption 7).
- Redaction is structural. `sanitize_transform_rule` keeps `{header name: operation}` and
  nothing else, and the raw ruleset is `del`eted right after. API errors print Cloudflare
  error *codes*, never the body. A 401 or 403 names `CLOUDFLARE_API_TOKEN` and the scope it
  lacks, never the value.
- Minimum token scopes, per the endpoints (OQ 1, carried; the operator confirms them at
  step 6): Zone WAF Read, Transform Rules Read, Zone Settings Read, Bot Management Read
  (zone `mealy.dev`), and Access: Apps and Policies Read (account).
- Verification: `python3 -m pytest infra/tests -q` gave **92 passed** (72 smoke + 20
  drift). Leak mutants, each applied alone and then restored (`cmp`-identical afterwards),
  all turned the suite red: the error body printed (1 failed), the token echoed on a 401
  (2), and the raw rule in a drift message (3). CLI with `CLOUDFLARE_API_TOKEN=` gave exit 2
  naming the variable. No live API call was made (the token is operator-held; the first run
  is Between-the-PRs step 6).
- Test-artifact coverage: critical path 13's offline half, and the drift bullets under Key
  interactions (a dummy header value never printed, a missing WAF rule is exit 1, a missing
  or rejected token is exit 2 and never echoed).

### Step 4 — build-commit stamp and CI
- Files: `frontend/index.html` (`<meta name="build-commit" content="%VITE_GIT_COMMIT%" />`
  plus a comment); `frontend/vercel.json` (`"buildCommand": "VITE_GIT_COMMIT=$VERCEL_GIT_COMMIT_SHA npm run build"`,
  assumption 10); `.github/workflows/test.yml` (a `frontend-tests` step "Build with the commit
  stamp", and a new `infra-tests` job on Python 3.12 that installs only pytest and runs
  `python3 -m pytest infra/tests -q`).
- Verification, through Docker Compose per the command policy:
  - `VITE_GIT_COMMIT=<HEAD> npm run build` put the full SHA into `dist/index.html`'s
    meta tag.
  - Without the variable, the tag stays the literal `%VITE_GIT_COMMIT%`, as the plan
    expects.
  - A CI-faithful build of a copy of `frontend/` with no `.env.local` and
    `VITE_API_BASE_URL` unset exited 0 and stamped `cafe1234`. `apiBase.js` throws at page
    load, not at build.
  - The smoke script's meta parser read the real Vite output, rejected the placeholder
    with its named message, and found the `/assets/index-*.js` reference.
  - The workflow parses as YAML (five jobs).
  - The CI grep accepts the real SHA and rejects the placeholder (both cases run in a
    shell).
- Not verified here, by design: Vercel exposes `VERCEL_GIT_COMMIT_SHA` only once
  "Automatically expose System Environment Variables" is on (Between-the-PRs step 0).
  Until then a Vercel build carries the placeholder, and check 8's frontend tier fails
  loudly, which is correct.

### Step 5 — `infra/RUNBOOK.md`
- File: `infra/RUNBOOK.md` (new).
- Header: owner, last executed (never), duration, risk, and minimum flyctl v0.4.102. It
  also records that the repo is public and that 50 days without a commit re-arms the
  60-day disable (criterion 17), plus both tokens by name. The `FLY_API_TOKEN` rotation date
  is left for PR1b, when the token is created.
- Sections:
  - §0 before you start (tell the household; counts are out-of-band).
  - §1 gates: CI on the release commit, doc-guard, the ops-check gate reading `n/a` until
    PR1b, the migration listing, the quiesce question, a recoverability pre-check, and
    both Vercel toggles.
  - §2 deploy, backend first: the downtime-measuring loop, `fly deploy --build-arg
    GIT_COMMIT`, `fly status`, promoting by SHA + Ready, the smoke commands (full, and the
    PR1a skip list), the Cloudflare dashboard steps, the three manual checks, tagging
    `v1-<UTC date>-<short sha>`, and the log row.
  - §3 the quiesce path.
  - §4 both fallbacks for when auto-promotion cannot be turned off.
  - §5 rollback: triggers, frontend first, backend `fly releases --image` → checkout of
    the target commit → `fly deploy --image <ref> --skip-release-command`, and
    forward-fix / downgrade / restore.
  - The execution log table, with a downtime column.
- Decisions:
  - The migration listing uses production's `alembic current` over SSH (the `%(here)s`
    `script_location` and an `env.py` that never prints the URL make this safe), then
    `docker-compose exec api alembic history -r <prod>:head`. No `v1-*` tag exists yet, so
    a tag diff could not answer the first release.
  - The quiesce path stops the machines and relies on "a deploy leaves a stopped machine
    stopped", then starts them again. The only binding header today is
    `a1b2c3d4e5f1_item_model_expand`, which has already shipped.
  - The password-rotation sequence is **not** in this file. The CLI ships in PR1b, so
    PR1b adds the section. This avoids documenting a command that does not exist yet.
- Verification: all 23 bash blocks pass `bash -n` (with `<placeholders>` substituted).
  Every documented `release-smoke.py` invocation was re-run with `--self-test` appended
  (nothing contacted) and parsed: exit 1, the forced failure, never exit 2. The three
  diagnostics anchors it links (`no-recent-restore-point`,
  `migration-failure-mid-release`, `a-real-restore-into-production`) are created in
  step 6, and a test there pins them.

### Step 6 — `infra/incident-diagnostics.md`
- Files: `infra/incident-diagnostics.md` (new); `infra/tests/test_runbook_links.py` (new);
  `infra/release-smoke.py` + `infra/tests/test_release_smoke.py` (one fix, below).
- The header carries owner and "last reviewed" (criterion 1: a lookup table, never executed).
  A check → entry table, the alert-fatigue rule (item 13) and the log-retention limit
  (CEO 8B) come next. The entries, each with symptom, distinguishing signal and ordered
  recovery:
  - web or a process group is down;
  - machine counts drifted;
  - **Background jobs (dead worker or beat)**: the four labels beside their Celery task
    names (Design 4A), the `succeeded`-line signal, a queue-depth command, item 15's
    web-reads-now truth table (Eng review 5), the web-restart re-arm warning, and a purge
    command;
  - 421 from the origin gate: the six reasons, with the two that cannot appear named as
    such;
  - break-glass Mode A / Mode B: PR1a status "not available until PR1b", the blast radius,
    enable / clear / confirm `gate_break_glass: false`, the sticky `-e`, never a secret;
  - Cloudflare down, including the grey-cloud trap;
  - no recent restore point, including the host-migration cause;
  - a real restore into production: stop worker and beat first, reconcile `assets` against
    R2;
  - Upstash / broker failure;
  - migration failure mid-release: one transaction, and why `--skip-release-command`;
  - deployed commit mismatch;
  - cache headers changed;
  - the Postgres hourly stop (OQ 4, carried open, recorded as observed);
  - tooling failures.
- Deviation found and fixed while writing the broker entry: check 4 classified a Python
  traceback from the probe as exit 2 (tooling). The probe had *run* in the app's environment
  and failed there (broker refused, broken import), which is evidence about production, so
  it is now exit 1, "worker round-trip failed on the machine: <last line>", with
  credentials masked. A test was written first and seen red, then green. SSH-level failures
  with no traceback stay exit 2.
- Checked against local help: `fly machine update` can set `--env` but not remove one, so
  the sticky-`-e` fix sets `GATE_BREAK_GLASS=0`. That is the toml default, and the strict
  parse keeps it off.
- Verification:
  - `python3 -m pytest infra/tests -q` gave **98 passed, 1 skipped**. The skip is the drill
    doc, which step 7 writes.
  - The anchor-link test was negative-controlled: renaming two headings turned three
    assertions red, and the file was restored and `cmp`-identical.
  - All 12 bash blocks pass `bash -n`.
  - The queue-depth one-liner splits into one `python -c` argument that compiles. Run
    through Docker Compose against the local stack, it printed `queue depth 0`.
  - Check 4's exact probe code, run the same way, completed a real enqueue → worker →
    result-backend round trip (`SMOKE_ROUNDTRIP {"status": "ok"}`). Only the `fly ssh`
    transport is left for the operator's first run.

### Step 7 — `infra/backup-restore-drill.md`
- File: `infra/backup-restore-drill.md` (new).
- Header: owner, last executed (never), duration, risk, cadence, minimum flyctl, and the
  ROLLOUT.md precedent. Cadence is "every 3 months as a starting point; the operator sets
  it at the first execution", which states a cadence while keeping OQ 2's call with the
  operator.
- Contents:
  - the product, and a table of its two mechanisms;
  - the volume-move failure mode (item 12's third bullet);
  - the rules that are never skipped (dated scratch names, destroy leftovers first, never
    target `mealy-app-prod-db`, always `-a mealy-app-prod-db`, scratch credentials stay
    in the terminal);
  - §0 item 12's confirm/enable plus the first-snapshot observation;
  - §1 leftovers;
  - §2 the snapshot path;
  - §3 the PITR path;
  - §4 the counting SQL, including `alembic_version`, `assets`, and `job_heartbeats` as
    `n/a` when the table is absent;
  - §5 re-run triggers, including "the volume id changed";
  - the execution log;
  - a restore-point log, seeded with the 2026-09-12 finding.
- Decisions: syntax taken from local flyctl v0.4.102 help. `fly pg backup restore
  <destination> -a <source>`. Both restores pin `--image-ref flyio/postgres-flex:17.2`, so
  the scratch cluster runs the major version the data came from. The pg_create flags are
  `--name/--snapshot-id/--region/--initial-cluster-size/--vm-size/--volume-size`. The
  scratch app goes with `fly apps destroy <app> --yes`.
- Verification: all 12 bash blocks pass `bash -n`. §4's SQL ran through
  `docker-compose exec -T db psql` against the local `todo_app` schema (SELECT only) and
  returned `alembic_version`, the seven counts, and `job_heartbeats_exists = f` (the PR1a
  case the doc answers with `n/a`). The macOS `date -u -v-15M +%FT%TZ` prints an RFC 3339
  UTC time. The link test now covers this file: `infra/tests` gave **99 passed**, no skips.
- Not executed, by design: the drill itself is Between-the-PRs step 5 (operator,
  criterion 7).

### Step 8 — `infra/cloudflare-state.md`
- The expired break-glass line (rollout recovery step 3) is replaced with a pointer to
  `incident-diagnostics.md#break-glass-…`, plus a dated note of why it expired (LESSONS
  Decisions, 2026-09-11: re-read and date-stamp every break-glass once the control ships).
- New `## Security — Bot Fight Mode` section, `Setting (…): **not yet recorded**`
  (assumption 8). It explains why smoke treats a challenge page as exit 2, and that the
  first drift run records the value.
- The intro no longer says drift detection "is M8 runbook scope". It names
  `cloudflare-drift.py` and the runbook's by-eye check, and lists the fields the script
  reads, so an edit keeps their shape.
- Deviation caught while verifying: the drift parser expected `Setting: **…**`, but the file
  uses the `Setting (<dashboard path>): **…**` shape of its Browser Cache TTL line. The
  regex now accepts a parenthetical, and the test edits the real line.
- Verification: `parse_intent` on the edited file returns bot `None`, WAF 5 / 10,
  TTL 0, no Access apps. `infra/tests` gave **99 passed**; the link test resolves the new
  pointer.

### Step 9 — doc_map
- File: `.agents/config.json`. The BACKEND_STRUCTURE → Code Organization rule gains
  `backend/app/cli/**`, `backend/app/gate_logging.py` and `backend/app/job_health.py` (all
  three are PR1b files, routed ahead of time so they cannot ship unrouted). `exempt` gains
  `infra/*.md`. A new `doc_map.exempt_notes` object records why, including the breadth: it
  also un-routes `cloudflare-state.md` and `r2-cutover-runbook.md` (assumption 9; doc-guard
  reads only `exempt` and `rules`).
- Verification: the file parses as JSON. `doc-guard --explain`, before and after:
  `infra/RUNBOOK.md` went from TECH_STACK → Infrastructure to exempt, and the cli and
  gate_logging paths went from unmapped to BACKEND_STRUCTURE → Code Organization. After,
  every touched path resolves:
  - the five `infra/*.md` files are exempt;
  - `release-smoke.py`, `cloudflare-drift.py` and `fly-scale.json` go to TECH_STACK →
    Infrastructure;
  - `infra/tests/**` is exempt;
  - `cli/**`, `gate_logging.py` and `job_health.py` go to BACKEND_STRUCTURE → Code
    Organization;
  - `vercel.json` goes to TECH_STACK → Infrastructure;
  - `frontend/index.html` is exempt;
  - `test.yml` goes to TECH_STACK → CI/CD Pipeline.

  `ctx` and `workflow-state` still load the config. This meets criterion 13.

### Step 10 — PR1b: host-gate rejection reasons (item 5)
- Files: `backend/app/gate_logging.py` (new: six reason constants in decision-tree order,
  `REASONS`, `emit_gate_rejection`, `emit_gate_bypass` for step 11); `backend/app/main.py`
  (`_origin_verified` → `_origin_verify_reason`, new pure `gate_reason()`, `_log_gate` wrapper,
  the `:193` comment rewritten as the decision tree); `backend/tests/integration/auth/test_host_gate.py`
  (every existing 421 test asserts its one `app.gate` record and reason; new: `Host: :443` →
  `host_absent`, byte-identical bodies across all six reasons, the raising emitter, the record's
  contents); `backend/tests/unit/test_gate_reason.py` (new: one test per branch, including a
  request with no `Host` header, which h11 and httpx cannot send).
- Decisions: `main.py` calls `gate_logging.emit_gate_rejection` through the module, so the
  raising-emitter test patches `app.gate_logging` and records the call as its negative control.
  The wrapper catches `Exception`, not `BaseException`. A present-but-empty `X-Origin-Verify` is
  `origin_verify_mismatch`; only a missing header is `origin_verify_absent`. The record carries
  `ip` (socket peer), `request_id`, `path` (128), and `host_present`/`host_length`,
  `origin_verify_present`/`origin_verify_length`; no header value.
- Verification: `docker-compose exec api uv run pytest tests/unit/test_gate_reason.py
  tests/integration/auth/test_host_gate.py tests/integration/auth/test_log_hygiene.py` →
  41 passed. Mutation: removing the `try/except` in `_log_gate` turned
  `test_gate_logging_failure_does_not_change_response` red; `main.py` restored `cmp`-identical.

### Step 11 — PR1b: `GATE_BREAK_GLASS` (open question 3; Eng review 7)
- Files: `backend/fly.toml` (`[env] GATE_BREAK_GLASS = "0"` with the why: versioned, never a
  secret); `backend/app/main.py` (`break_glass_enabled()`, the bypass branch in `gate_reason`
  after the Host checks, one `emit_gate_bypass` per admitted request while on, decision tree
  updated); tests in `tests/unit/test_gate_reason.py` (strict parse: `1` on; `0`, empty,
  `true`, `yes`, `TRUE`, `" 1 "`, `"1 "`, `01`, unset off; the flag skips all three origin
  checks and no Host check) and `tests/integration/auth/test_host_gate.py` (admitted and logged
  `bypassed`; every admitted request logged, `/healthz` not; wrong Host still 421; loose values
  stay off). Both fixtures now clear `GATE_BREAK_GLASS` so a stray container env cannot open
  the gate under test.
- Decision: the flag is read per request, like `PUBLIC_API_HOST` and `ORIGIN_VERIFY_SECRET`,
  so tests and the local rehearsal flip it with the environment alone.
- Verification: 55 passed. Mutation: a loose parse (`strip().lower() in ("1", "true", "yes")`)
  turned 8 tests red; `main.py` restored `cmp`-identical.

### Step 12 — PR1b: `/healthz` version, break-glass flag, `no-store` (item 14)
- Files: `backend/Dockerfile` (`ARG GIT_COMMIT` + `ENV GIT_COMMIT` in the **prod** stage,
  last before `USER`, with the why); `backend/app/main.py` (`deployed_version()`; `/healthz`
  returns `status`, `version`, `gate_break_glass` and sets `Cache-Control: no-store`);
  `backend/tests/unit/test_healthz.py` rewritten (its docstring and exact-body assertion forbade
  this change, Eng review 2.6): version from the env, `unknown` when unset/empty/blank,
  `no-store`, the flag's strict parse as reported, and the exact key set.
- Verification: `pytest tests/unit/test_healthz.py tests/integration/auth/test_host_gate.py` →
  37 passed; the three other files that mention `/healthz` → 16 passed. The running local api
  answers `{"status":"ok","version":"unknown","gate_break_glass":false}` with
  `cache-control: no-store`. A real `docker build --target prod --build-arg GIT_COMMIT=deadbeef`
  image carries `GIT_COMMIT='deadbeef'`; without the arg it is `''`, which the handler reports as
  `unknown` (test images removed afterwards). Trap confirmed while checking: the prod image's
  relative `PATH` entry means a bare `python` does not resolve; `/app/.venv/bin/python` does,
  as item 6 already requires for the rotation CLI.

### Step 13 — PR1b: `JobHeartbeat` model and the `job_heartbeats` revision (open question 6)
- Files: `backend/app/models.py` (`JobHeartbeat`, with the row-lifecycle diagram the plan's
  inline-diagram table asks for); `backend/alembic/versions/1b6b462491fa_add_job_heartbeats_table.py`
  (generated with `docker-compose exec api alembic revision -m`, written by hand: `task_name`
  Text PK, `last_success_at` / `last_error_at` timestamptz, `last_error` Text, `error_count` int
  default 0; `downgrade()` drops the table).
- Decisions: autogenerate was not used, because the dev database still holds the M-era
  `recipes_archived` / `food_items_archived` tables no model declares, so it would have
  proposed dropping them. `last_error` will hold the exception class name only (step 15),
  per the test artifact's log hygiene. No index beyond the PK: the refresher reads all rows
  (four) every 30 s.
- Verification: `alembic heads` → one head `1b6b462491fa`; `upgrade head` on the dev database,
  `\d job_heartbeats` shows the columns and types above; `downgrade -1` → `to_regclass` empty;
  `upgrade head` again → present. A one-off `alembic.autogenerate.compare_metadata` run (with
  `compare_type` and `compare_server_default`) filtered to `job_heartbeats` → `[]`, so the model
  and the migrated schema agree. The repository has no standing models-vs-migrations test
  (REVIEW_CHECKLIST → Alembic → Testing); not added here, noted as a gap.

### Step 14 — PR1b: `job_health.py` and `/healthz.jobs` (item 15; Eng reviews 1.2, 4, 5)
- Files: `backend/app/job_health.py` (new: `JOB_LABELS`, `humanize`, `beat_intervals()`
  (raises on a non-number / non-`timedelta` / non-positive / duplicate schedule),
  `scheduled_intervals()` (derived once), the frozen `Reading` / `HeartbeatRow` the refresher
  replaces wholesale, the pure `build_jobs_payload(reading, now, started_at, intervals)`, the
  `JobRow` / `JobsReading` Pydantic contract model, `serve_jobs()` (validates, and returns the
  unusable reading instead of raising or serving a malformed body), `read_heartbeats(session)`,
  `refresh_once`, `refresh_forever`; the module docstring carries the data-flow diagram the
  plan's inline-diagram table asks for); `backend/app/main.py` (lifespan: `mark_started()`,
  starts the refresher, cancels and awaits it on shutdown; `/healthz` adds `jobs`);
  `backend/tests/unit/test_job_health.py` (new, 44), `backend/tests/unit/test_healthz.py`
  (the contract key set, the served reading, zero database calls with a negative control, and a
  real-lifespan run with the store stubbed to hang), `backend/tests/integration/test_job_health_read.py` (new).
- Decisions: timestamps serialize at second precision with a `Z`; `interval_s` is an int when
  integral. `refresh_forever`'s defaults resolve per cycle so the lifespan-run test can swap the
  reader and timeout. The contract model validates before serving: a naive timestamp, an empty
  schedule, or an uncomputable schedule all serve `read: "unavailable"`, never a 500 on the probe.
- Bug found and fixed during the step: Pydantic compiles `Field(pattern=...)` with Rust's regex
  engine, which rejects `\Z`; the dev api's hot reload died at import. `\z` is the Rust anchor;
  LESSONS.md → "Anchor Python key/path regexes" gained the rule.
- Verification: 57 passed (`test_job_health.py`, `test_healthz.py`, `test_job_health_read.py`).
  The live dev api (hot reload) serves the contract: `read: "ok"`, four rows in
  `beat_schedule` order with the server's labels, `interval_s` 600/600/3600/3600, all NULL and
  not stale inside the post-start grace. Mutations, each turning `test_job_health.py` red:
  `>` → `>=` on staleness (4 failed), `<=` → `<` on the `write_error` window (1 failed), a NULL
  row never stale (3 failed); file restored `cmp`-identical.

### Step 15 — PR1b: `task_postrun` heartbeat writer (item 15; Eng review 3, Adversarial review)
- Files: `backend/app/tasks.py` (`record_job_heartbeat` on `task_postrun`, `_write_heartbeat`,
  `_in_app_session`, and the flow diagram the plan's inline-diagram table asks for);
  `backend/app/job_health.py` (`upsert_heartbeat_success` and `record_heartbeat_error`, the two
  `INSERT … ON CONFLICT (task_name)` writes, next to the one read); tests:
  `backend/tests/unit/test_job_heartbeat_writer.py` (13: SUCCESS-only, `beat_schedule` names
  only including `health_check` and `extract_recipe_from_url`, the error write with the class
  name, the second failure's one extra WARNING and no raise, an uncomputable schedule, and the
  receiver really connected to Celery's `task_postrun`), and
  `backend/tests/integration/test_job_heartbeat_store.py` (5: clean insert, idempotent
  redelivery, error keeps `last_success_at` and counts, error before any success creates the
  row, a later success clears the error).
- Decisions: `last_error` stores the exception class name only, bounded to 200 characters (the
  message can quote a connection string; the unit test asserts `hunter2` never reaches a log).
  The filter uses `job_health.scheduled_intervals()`, the same definition the payload uses.
  The handler catches everything, including a failing filter, so a heartbeat never taints a task.
- Verification: 18 passed. Live on the local Compose stack (never production): restarted the
  local `celery_worker`, enqueued `hard_delete_expired_soft_deletes` and `health_check` with
  `celery call`; the worker log shows both `succeeded`, `job_heartbeats` gained exactly one row
  (`hard_delete_expired_soft_deletes`, `error_count` 0), and within one refresher cycle
  `/healthz.jobs` showed "Deleted item cleanup" `last_success_at 2026-09-23T18:26:16Z`,
  `stale: false`, with the other three still NULL inside the grace (test artifact critical
  paths 4 and 14).

### Step 16 — PR1b: password rotation (item 6; Eng review 2.1, CEO 2D, Adversarial review)
- Files: `backend/app/auth/service.py` (`RotationRejected`, `RotationSummary`,
  `rotate_password()`: refuses empty and >128 before any lookup or hashing, CITEXT lookup like
  login, sets the hash on the session, counts live rows, `logout()` is the only commit, re-reads
  the version; the module diagram names it and states why the order is fail-closed; `logout`'s
  docstring gains the one-line CLI exception); `backend/app/cli/__init__.py`,
  `backend/app/cli/rotate_password.py` (argparse email only, `getpass` twice, exit 0 / 1 / 2,
  engine disposed before the loop closes, the operator sequence and both SSH traps in the
  docstring); tests `backend/tests/integration/auth/test_rotate_password.py` (7) and
  `backend/tests/unit/test_rotate_password_cli.py` (10).
- Decisions: exit 2 covers any database-layer failure (`DBAPIError`, `OSError`, a timeout), not
  only "unreachable": a missing table is `ProgrammingError`, which would otherwise surface as a
  traceback and exit 1, the code for "refused, nothing written". Its message says "the rotation
  did not complete" rather than "nothing was changed", which cannot be promised if the
  connection drops during the commit.
- Verification: 17 passed plus `test_logout.py`'s 8. Mutation: a second commit after setting
  the hash turned the crash test red; `service.py` restored `cmp`-identical. End to end in a
  scratch database on the local Postgres (`rotation_scratch`, created, migrated, dropped): the
  real `python -m app.cli.rotate_password HOUSEHOLD@example.com` with both passwords on stdin
  printed the summary and the household line and exited 0; the new password verifies, the
  session version went 0 → 1, 0 live refresh rows remain; a mismatch and an unknown email each
  exited 1. The `fly ssh console --select` run on production is the operator's criterion 6
  (Between the PRs step 9).

### Step 17 — PR1b: smoke script: the pause declaration and `[1] version-reported`
- Files: `infra/paused.json` (new: worker and beat, since 2026-09-23, review_by 2026-10-23,
  reason "Upstash request cap (500,000 requests/month); TODOS.md P1"); `infra/release-smoke.py`
  (the docstring states the pause rules next to the check matrix; `PAUSE_FILE`,
  `PAUSABLE_GROUPS`, `Paused`, `Pause`, `read_pauses`, `pause_verdict`, `Context.pauses()`;
  check 2 requires a declared group to be stopped and never suggests starting it; check 4 and
  jobs-fresh go through `pause_verdict`, and jobs-fresh applies the unusable-reading rule
  first; a `PAUSE` outcome and a summary that counts it; the self-test ignores the file; a new
  liveness check `[1] version-reported` under the existing `healthz_version` key);
  `infra/tests/conftest.py` (autouse `no_declared_pause`: every test starts from `{}`);
  `infra/tests/test_release_smoke.py` (22 new tests; two summary counts updated for the new
  check; the skip-key test now pins the exact key-to-check map, since `healthz_version`
  legitimately covers check 8's backend comparison and `version-reported`).
- The user-approved spec, point by point: a paused group must be stopped (check 2 fails if it
  runs) — done; check 4 and jobs-fresh print PAUSED, never pass — done; the summary counts
  paused — `exit 0: 11 passed, 0 skipped, 2 paused (beat, worker declared in infra/paused.json)`;
  past review_by fails — on every run, not once (assumption 2, approved); `ops-check.yml` needs
  no pause logic (step 18 runs the same script); worker and beat declared since 2026-09-23,
  review_by 2026-10-23; the Settings card unchanged. Docs: step 23 and `/update-docs`.
- Decisions: a missing file declares nothing (the strict reading); only worker and beat can be
  declared (web is the app); a malformed file or entry is exit 2 on the three checks that read
  it. Paused jobs-fresh still fails an unusable reading, because it is the cron's only sign that
  the web cannot reach the database.
- Verification: `python3 -m pytest infra/tests -q` → 155 passed. Both self-tests still exit 1
  (check 3; jobs-fresh), with the real pause file present. Mutations, each turning one test red:
  the review-date boundary `>` → `>=`, the self-test honouring the pause, check 2 ignoring a
  running paused group; script restored `cmp`-identical.

### Step 18 — PR1b: `.github/workflows/ops-check.yml` (item 13; CEO 8A, 2F; Adversarial review)
- Files: `.github/workflows/ops-check.yml` (new): daily at 14:17 UTC and `workflow_dispatch`
  with a boolean `self_test`; runs `python3 infra/release-smoke.py
  --only=liveness,recoverability,edge` (plus `--self-test` when asked); `permissions: contents:
  read`, a `concurrency` group, `timeout-minutes: 10`; `actions/checkout@v4`,
  `actions/setup-python@v5` (3.12), `superfly/flyctl-actions/setup-flyctl@1.6` pinned to flyctl
  `0.4.102`; retry once as two steps (the first `continue-on-error`, the second only when it
  failed, after 60 s); the script's output goes to the job summary. `FLY_API_TOKEN` comes from
  `secrets`, is never echoed, and no pull-request trigger exists, so forks never receive it.
- Decisions: no pause logic in the workflow (the script reads `infra/paused.json`); retry on
  any failure class, because a Postgres primary waking (open question 4) or a network blip can
  fail either; the self-test fails both attempts, so its email proves the alert (criterion 17).
- Verification: the YAML parses (triggers `schedule`, `workflow_dispatch`; six steps). The
  run blocks' shell logic under `bash -e` with the self-test args: the script's lines are
  printed and the step exits 1. `actionlint` is not installed on the host; GitHub validates the
  file on push. Operator steps after merge (Between the PRs 10): create the read-only token,
  `gh secret set FLY_API_TOKEN`, confirm it can run `fly volumes snapshots list`,
  `fly pg backup list` and `fly ips list`, then `gh workflow run ops-check.yml` and the
  `self_test=true` run (step 23 writes them into the RUNBOOK).

### Step 19 — PR1b: shared `serverTime.js` and `FreshnessDot.jsx` (item 15; CEO 4B-A, Design 5A, 6A)
- Files: `frontend/src/lib/serverTime.js` (new: `parseServerTime` and `relativeTime` moved from
  `ICloudSettings.jsx`, `relativeTime` now takes an optional `now`; new `durationSince` → "45
  min" / "3 hr" / "2 days"); `frontend/src/components/shared/FreshnessDot.jsx` (new: one `tone`
  prop, `ok` sage / `bad` red / `unknown` muted, `aria-hidden`, no text, caller placement
  classes); `frontend/src/components/settings/ICloudSettings.jsx` (imports both; the fresh dot is
  `sage-500` and the fresh text `text-text-secondary`; `syncIsOverdue` and
  `SYNC_STALE_AFTER_MS` stay, per 15a's file table and the P3 TODO); tests
  `frontend/src/lib/serverTime.test.js` (new, `TZ=America/Los_Angeles`: naive parsed as UTC,
  `Z` and offsets kept, words against a passed-in `now`), `frontend/tests/components/shared/FreshnessDot.test.jsx`
  (new), and two new cases in `ICloudSettings.test.jsx` (sage dot and secondary gray when fresh;
  red when overdue).
- Decision: `relativeTime`'s `now` defaults to the browser clock, so the iCloud line behaves
  exactly as before; only the Background jobs card passes the server-aligned one (Eng review 4).
- Verification: `docker-compose exec frontend npx vitest run` on the three files → 37 passed
  (the existing freshness tests, including the no-`Z` fixture under Los Angeles time, unchanged).

### Step 20 — PR1b: `useBackgroundJobs.js` and `deriveJobsState` (item 15a; Eng reviews 4, 5)
- Files: `frontend/src/hooks/useBackgroundJobs.js` (new: `HEALTHZ_QUERY_KEY`, `POLL_MS`,
  `cadence`, `deriveJobsState(jobs, now)` with the first-match ladder 1 → 6 and state 2's
  evidence predicate commented as the plan's inline-diagram table asks, `announcementFor`,
  `jobsViewFromQuery(query, browserNow)` for the server-aligned clock and the footnote, and the
  hook itself: raw `fetch(apiUrl('/healthz'), { cache: 'no-store' })` throwing a plain `Error`,
  `queryKey ['healthz']`, `refetchInterval 30_000`, `staleTime 0`, `retry: false`, derived on
  every render, never in `select`); `frontend/tests/hooks/useBackgroundJobs.test.js` (new, 41).
- Decisions: the "What this means" lines are keyed by task name here, labels come from the
  server (Eng review 4, 3A). The footnote's age uses `durationSince`, so it reads "1 min ago"
  rather than "just now". The announcement lowercases the headline's first letter, per the plan's
  text ("Background jobs: all running on schedule."); the mockup kept the capital, and the plan
  wins where they differ. A row whose `last_success_at` is present but unparseable is part of an
  unusable reading.
- Verification: 41 passed under `TZ=America/Los_Angeles`: all six states and loading; every
  unusable form outranking every-row-stale; state 2's three fixtures plus the null-success body;
  row text by the row's own values (a fresh flagged row reads "ran 1 hr ago", not red); the
  Waiting split; skewed browser clocks (±10 min) giving the same view; failed polls aging the
  same data into state 1; the footnote; a `/healthz` without `jobs`; and the real hook against
  MSW (no `Authorization`, every 30 s, still polling after a 500, silent after unmount).
  Mutations, each turning tests red: state 2's predicate without the unflagged-row clause (2),
  Stopped checked before Can't record (3), the 2-minute cap `>` → `>=` (1); file restored `cmp`-identical.

### Step 21 — PR1b: `BackgroundJobsSection`, `BackgroundJobsAlert`, Settings wiring (item 15a)
- Files: `frontend/src/components/settings/BackgroundJobsSection.jsx` (new: the card shell,
  `h2#background-jobs` with `tabIndex={-1}` and `scroll-mt`, the description, one visually
  hidden `role="status"`, headline with the dot at `mt-[7px]`, consequence lines, the `<dl>`
  rows with `<time dateTime title>`, the footnote, the 200 ms "Checking…"); `…/BackgroundJobsAlert.jsx`
  (new: states 2–4 only, inline text `red-700`, the underlined `terracotta-700` link with
  `whitespace-nowrap` and a 44 px hit area on phones, `preventDefault` + scroll + focus the
  `h2`, `auto` under reduced motion; no role, no dismiss, no banner); `frontend/src/pages/FamilyMembersPage.jsx`
  (`<header>` around the `h1` and the alert, the `h1` drops its margin, the card directly above
  Account); `frontend/src/hooks/useBackgroundJobs.js` (see decisions); `frontend/tests/mocks/handlers.js`
  (`HEALTHZ_HEALTHY`, the contract's healthy example, as the default `/healthz` handler);
  `frontend/tests/components/settings/BackgroundJobsSection.test.jsx` (new, 12, in `StrictMode`).
- Decisions: the status region's text is written to its empty node from an effect, with the
  previous state in a ref, because the repo's lint forbids `setState` in an effect and the test
  artifact forbids render-time ref mutation. ESLint's `react-hooks/purity` forbids `Date.now()`
  in render, so the hook reads the browser clock as TanStack's timestamp of the latest fetch
  outcome (`max(dataUpdatedAt, errorUpdatedAt)`) — a poll, success or failure, is what re-renders
  the card anyway, so failed polls still age the reading into state 1. That exposed a gap the
  plan did not name: a `/healthz` request that hangs never fails, so it would freeze the card on
  its last reading; the fetch now carries `AbortSignal.timeout(10_000)`. A hook test pins "three
  minutes of failed polls → state 1".
- Verification: `vitest run` on the hook and component files → 54 passed; `eslint` on every new
  and edited frontend file → 0 problems. In a real browser (the visual-test stack's preview build,
  signed in by its synthetic user; `/healthz` served per state by route interception; a
  temporary, uncommitted spec, deleted afterwards): six states × 1440 and 375 px × light and dark,
  24 passed; nothing in the Settings header or the card crosses the viewport; the link focuses the
  `h2` and leaves the URL unchanged. Screenshots reviewed: state 6 desktop (two-column rows, sage
  dot), state 4 at 375 px (the alert wraps as a sentence, "See background jobs" whole, rows
  stacked, only stale rows red), state 2 fixture (c) and state 3 in dark mode, state 1.
- Found, pre-existing, not changed (scope): at 375 px `FamilyMemberManager`'s terracotta "Add"
  button extends 33 px past the viewport, so the Settings page scrolls sideways on a phone. The
  branch does not touch that component. Candidate TODO, raised at completion.

### Step 22 — PR1b: the sign-in bounce banner says why (item 6, Design review 10)
- Files: `frontend/src/pages/AuthPortalPage.jsx` (`COPY.bounce` → "Your session ended. Someone
  may have signed out on another device, or the household password changed. Sign in to pick up
  where you left off.", with the reason the specific message is not derivable); its test gains
  an assertion on the full sentence. No backend, auth or schema change.
- Verification: `vitest run src/pages/AuthPortalPage.test.jsx` → 17 passed (the two existing
  `/your session ended/i` tests unchanged); eslint clean.

### Step 23 — PR1b: the runbooks for the PR1b surfaces (items 1, 2, 13; the pause)
- Files: `infra/RUNBOOK.md`: the `FLY_API_TOKEN` header bullet now says how to create it
  (`fly tokens create readonly -o personal -n ops-check -x 8760h | gh secret set …`, piped so
  it never prints), how to prove its reads (the first `gh workflow run ops-check.yml` green,
  the `self_test=true` run failing with the right email), and what to do if a read is refused;
  §2 step 5 explains a declared pause's `PAUSE` lines and its failures; §5.2 step 4 adds
  `healthz_version` to the skip list when rolling back to a pre-PR1b image (the new
  `[1] version-reported` check); a new **§6 Rotate the household password** (the sequence
  deferred from PR1a, deviation 7: tell the household first unless the password leaked,
  `fly ssh console --select`, the absolute interpreter, the expected output and exit codes, and
  the sign-in banner the household will see). `infra/incident-diagnostics.md`: a new entry
  **A deliberate pause (worker or beat)** (the file's format, the check table, declare /
  extend / resume, the Settings card not being pause-aware), a pointer to it at the top of the
  Background jobs entry, the index table (`[1] version-reported`; `PAUSE` lines), the deployed
  commit entry (`[1] version-reported` between releases), and the tooling entry (a malformed
  pause file). `.agents/docs/TODOS.md` → P1: the resume steps gain "empty `infra/paused.json`".
- Not changed, deliberately: the diagnostics' "(from PR1b)" and "not available until PR1b is
  deployed" sentences describe what is deployed, so they stay true until the PR1b release; PR2
  corrects them against the executed release, like the other runbook corrections.
- Verification: `python3 -m pytest infra/tests -q` → 155 passed, including
  `test_runbook_links.py` (every new anchor link resolves). `fly tokens create readonly --help`
  confirmed `-o`, `-n` and `-x` (flyctl v0.4.102); no token was created.

### Step 24 — PR2: `infra/RUNBOOK.md` (the PR1b release's evidence and corrections)
- Files: `infra/RUNBOOK.md` only.
  - Header: "Last executed" is now `v1-20260924-f4a6814`; `FLY_API_TOKEN` "first dispatched
    2026-09-24".
  - `FLY_API_TOKEN` first-run rule rewritten: with a read-only token `[9]` always ends in
    `also: fly pg backup list exited 1: … unauthorized` (the read execs on the DB VM), so the
    cron watches snapshots and only the laptop smoke reads WAL. "Drop to credential-free
    checks" now applies only to a refused snapshot or `fly ips list` read. The email result
    (both annotations shown) is recorded, with "check again after a rotation".
  - §0: Vercel toggles "take effect only after Save; reload and confirm" (the #60
    auto-promote); a new "Who runs the production commands" item (auto mode refused
    `fly ssh console`; operator runs them, or narrow rules removed afterwards); the `$RELEASE`
    bullet explains `${RELEASE:?}`.
  - Every command that reads `$RELEASE` now writes `${RELEASE:?}` (8 sites: §1 CI gate, §2
    steps 2, 4 ×2, 5 ×2, 8 ×2). The prose `${RELEASE:0:7}` in §1's Staged check stays prose.
  - §1 ops-check gate: past tense for the n/a state; scheduled runs can be hours late, so the
    gate is the newest run's age.
  - §2 step 2: the deploy is `tee`d to `${TMPDIR:-/tmp}` (outside the checkout, so the clean
    tree stays clean), and a migration release re-runs §1's `alembic current` to prove the
    head landed, instead of reading the scrolled-away `release_command` lines.
  - §2 step 7: a one-time item pointing at the TODOS `Fly-Client-IP` proof for the first
    release that includes #64 (the TODO said it was kept out of the RUNBOOK only because PR2
    was rewriting it; step 30 updates that sentence).
  - Execution log: the 2026-09-24 row (gates, migration listing, smoke line, downtime, the
    gate-`ip` finding, the four `ops-check` runs and the email, break-glass, the fixes).
- Decisions: the rotation (§6) gets its own row when the operator runs it (the user chose
  option A: run it before `/ship`), rather than being folded into the release row.
- Not changed: §0's and §2 step 5's "first execution only (PR1a)" notes. They are historic
  now, but removing them is a removal, and they still describe a rebuild from a pre-PR1b tag.
- Verification: `${RELEASE:?}` stops with an error when unset in both bash (`parameter null
  or not set`, exit 127) and zsh (`parameter not set`, exit 1), and expands normally when set.
  Both execution-log rows have 7 cells. `python3 -m pytest infra/tests -q` → 165 passed
  (including the RUNBOOK anchor-link test).

### Step 25 — PR2: `infra/incident-diagnostics.md` (break-glass, the WAL line, open question 4)
- Files: `infra/incident-diagnostics.md`; one resolution paragraph under the plan's open
  question 4; one observed line on the test artifact's matching edge case.
  - "Last reviewed" is now 2026-09-25, against `v1-20260924-f4a6814`.
  - The four sentences that described PR1b as not yet deployed now name the release
    instead (Status of Mode A, the Cloudflare-down "no fallback", the gate logging nothing,
    the `--skip=healthz_jobs` hint). They stay useful after a rollback to an older image. The
    other "(from PR1b)" markers are still true and were left alone.
  - Break-glass → "Rehearse it": the local command, three `curl` probes, the log grep, and an
    expected-results table for flags `0`, `1` and `true` (step 11, criterion 15).
  - No recent restore point: a "not this entry" bullet for the cron's expected
    `also: fly pg backup list … unauthorized`, and what the cron reports if snapshots stop
    while WAL continues (exit 2 `restore point unverified`, per `check_restore_point`).
  - Postgres primary (open question 4): the observed answer, the command to re-read it (the id
    from `fly machines list`, `fly machine status` without `-d`), and what a returning stop
    means.
- Evidence, open question 4 (read-only, run by the agent in this session; the classifier
  allowed it): `fly machine status 6835444b795398 -a mealy-app-prod-db` at 2026-09-25T03:17Z
  → `State: started`, `Updated 2026-09-24T04:45:25Z`, Memory 512, image
  `flyio/postgres-flex:17.2`. Event log, newest first: `started` 04:45:25Z (proxy wake at
  04:45:23Z, two minutes before the PR1b deploy), `stopped exit_code=0 requested_stop=false`
  2026-09-23 22:50:05Z, `started` 21:50:03Z. So about 22.5 h with no stop, against a
  one-hour idle stop the day before.
- Evidence, break-glass: re-ran the rehearsal (throwaway `bg-rehearsal` container on :8099,
  secrets from `openssl rand`, never printed). Flag `0`: `/healthz` false; 421
  `origin_verify_absent`; 200 with the header; 421 `host_mismatch`. Flag `1`: true; 200
  `outcome="bypassed"` twice; 421 `host_mismatch`. Flag `true`: identical to `0`. Matches
  step 11. The container was stopped and removed (`--rm`).
- Verification: `python3 -m pytest infra/tests -q` → 165 passed (anchor links resolve).

### Step 26 — PR2: `infra/backup-restore-drill.md` §0 (enabling continuous backups)
- Files: `infra/backup-restore-drill.md`: §0's first item now gives the three steps that
  enabling took on 2026-09-23. (1) Resize the DB machine to 512 MB first
  (`fly machine update <id> --vm-memory 512`, which restarts Postgres). (2) Run
  `fly pg backup enable` in your own terminal, because of the Tigris terms prompt.
  (3) `fly secrets deploy -a mealy-app-prod-db`, then expect a base backup in
  `fly pg backup list`. The restore-point log's 2026-09-23 row gains the secrets-deploy fact.
- Sources: the resize and the terms are in the repo already (the restore-point log row). The
  `fly secrets deploy` step and "a restart did not apply them" come from the agent's session
  notes of Between the PRs step 0a (2026-09-23T16:46Z), and nothing in the repo recorded them.
  **The operator should confirm that detail in review.** The notes also do not say why 512 MB
  was needed, so the text says only that enabling ran after the resize, not that a smaller
  machine fails.
- Verification: `fly pg backup enable --help` (flyctl v0.4.107) has no flag to accept the
  terms, so the step is interactive by construction. `fly secrets deploy --help` and
  `fly machine update --help` (`--vm-memory`) confirm the commands. The DB machine reads
  `Memory 512` today (step 25's status read). `infra/tests` → 165 passed.

### Step 27 — PR2: `infra/r2-cutover-runbook.md` (M7's two open items)
- Files: `infra/r2-cutover-runbook.md`.
  - The `fly status` box is **struck, not ticked**. Its checkbox is gone, and its text is
    struck through with a dated note citing `git log -S` and pointing at smoke check 2 and
    RUNBOOK §2 step 3.
  - The sweep box stays open with "Still open, re-recorded 2026-09-25".
  - The execution log row says why it is still open (the deliberate worker and beat pause)
    and what closes it (TODOS P1's resume step 5).
- Verification: `git log -S 'shows **every** process group' -- infra/r2-cutover-runbook.md`
  → only `651ff27` (#49, 2026-09-11T15:07:30-07:00); `git log -S '| 2026-09-11 | willdoucet | Pass |'`
  → only `3f14222` (#45, 13:12:22-07:00). So the box postdates the only run, as the plan said.
  `infra/tests` → 165 passed.

### Step 28 — PR2: the v1.1 (ops) scope contract (parent plan open item 8)
- Files:
  - The epic's `## Deferred to v1.1` became `## v1.1 (ops) scope contract`: a ten-row table
    (candidate, In, Gated or Out, why, and where it is tracked), a note that it is not PRD §11's
    product v1.1, and that resuming the paused worker comes first.
  - `prod-contract-freeze` plan → open item 8 is struck and resolved, with a link and the
    one-line outcome. The original text is kept.
  - `IMPLEMENTATION_PLAN.md` → "Explicitly deferred to v1.1" is now a short In, Gated, Out
    summary that links to the contract, so the reasons live in one place. Its closing bullet
    ("any other hardening the first few releases reveal") is dropped, because the contract
    is that reckoning.
- Decisions (assumption 5, not corrected):
  - In: the `/auth/login` rate limit and burst test, structured `/auth/*` and 401 logs, the
    recovery-point lag, and the stale-chunk fix.
  - Gated: `deploy.yml` (after a fix-free release) and `visual-tests` required (after its two
    flakes are fixed and ten runs pass in a row).
  - Out: previews, rotation as `workflow_dispatch`, Sentry, and a scheduled drift script.
  - The WAL-reading cron token is P3 (step 30), since the laptop smoke reads WAL every release.
- Verification: no anchor links pointed at either renamed section (grep). The contract's
  anchor `#v11-ops-scope-contract` follows GitHub's slug rule, and both links to it use it.

### Step 29 — PR2: epic and roadmap reconciliation
- Files:
  - The epic:
    - the `Status:` line (M8 in its last part, not "not started");
    - Locked architecture's Database line: unmanaged Flex 17.2, with the reason the restore
      commands differ;
    - a new "What M8 shipped against these" block under Done when, one bullet per criterion
      with its evidence. The criteria keep their original wording, per the plan's
      "PR2 updates the epic text to match what shipped".
  - `IMPLEMENTATION_PLAN.md`: Known Gaps → Active work, and Prioritization item 5 (M8 is in
    its last part); Locked architecture's Database line.
  - `PRD.md` §11 v1.0: "Fly Postgres (unmanaged Flex)".
- Left for `/ship`: the M8 milestone row's status and the Phase 2 milestone count.
  `/ship`'s second `/update-docs` owns both (ship SKILL "Then the roadmap").
- Left, deliberately: the M8 plan's "Locked decisions (from the epic, verbatim)" item 3 still
  quotes "Fly managed Postgres", because it is a verbatim quote of the epic at the time.
  PRD §11's unticked v1.0 boxes (auth shipped in M3–M5) are `/update-docs`' factual-drift call.
- **Open in the epic until the operator runs it:** the rotation bullet reads "pending"
  (option A). The step that records the run turns it to met.
- Verification: `grep -rn 'managed Postgres'` over `.agents/docs`, the epic and AGENTS.md now
  finds only the two correction sentences. TECH_STACK already said `Fly Postgres Flex
  (unmanaged)` and `web=1` (PR1a). The epic's link targets `#success-criteria`, which exists
  in the plan (line 2110).

### Step 30 — PR2: TODOS.md and LESSONS.md reconciliation
- `TODOS.md`:
  - New **P3 "Let the daily cron read WAL backups"**, placed after the WAL-lag P2. It holds
    the `unauthorized` evidence, what goes unwatched, a `machine-exec` token restricted to
    one command as the next step (flags from `fly tokens create machine-exec --help`,
    v0.4.107), and the "never a deploy-capable token" constraint. P3, not P2, because the
    laptop smoke reads the WAL backups every release.
  - `Fly-Client-IP` P2: "deliberately not in the RUNBOOK" becomes "RUNBOOK §2 step 7 points
    here".
  - P1 resume, step 5: the sweep's `succeeded` line also closes the M7 runbook's last item.
  - Rotation P2: records the operator's 2026-09-25 choice (run before PR2 ships).
  - Already reconciled by earlier parts, and left as they are: both Cloudflare drift items
    (DONE and SUPERSEDED, PR1a), the background-job health signal (DONE, PR1b), and boto3
    checksums (DONE, PR1a release).
- `LESSONS.md`:
  - Bug Log row for 2026-09-23 (the host-migration stop, #49 merged but never deployed,
    `on-failure`, the Upstash cap). It carries the "To write up: LESSONS Bug Log" item from
    the agent's 2026-09-23 notes.
  - Canonical rule "Merged is not deployed" in the `fly deploy` section.
  - `${RELEASE:?}` rule in "Runbook checks must be runnable". Both are rules the codebase
    taught, not user corrections, so there is no Corrections Log row.
- Verification: the new Bug Log row has the table's 4 cells. The RUNBOOK's reference
  "Let the daily cron read WAL backups" matches the new TODO's heading exactly.

## Doc impact

- Step 1: TECH_STACK → Infrastructure / Production Deployment: state the counts
  (`web=1`, `worker=1`, `beat=1`), that they are set with `fly scale count` and pinned in
  `infra/fly-scale.json`, and asserted by smoke check 3.
- Step 2: TECH_STACK → Infrastructure (the `infra/` operator tooling: `release-smoke.py`, its
  groups and exit classes, a pointer to RUNBOOK) and the §8 file-structure tree (`infra/`
  contents); development-commands.md + AGENTS.md: `infra/` scripts and `infra/tests` are a
  host-side exception, with the command `python3 -m pytest infra/tests -q`.
- Step 3: TECH_STACK → Infrastructure / External integrations: the Cloudflare API (read-only
  token, operator-held, `CLOUDFLARE_API_TOKEN`) used by `infra/cloudflare-drift.py`; the
  env-var name belongs in TECH_STACK's variables list as operator-only (not app runtime).
- Step 4: TECH_STACK → CI/CD Pipeline: five jobs, not four; `infra-tests`; `frontend-tests`
  now also builds with `VITE_GIT_COMMIT` and greps the stamp. TECH_STACK → Production
  Deployment (Vercel row): `vercel.json` `buildCommand` stamps the commit, and the "Expose
  System Environment Variables" setting must be on. development-commands.md: CI job list
  (four → five).
- Steps 5–6: the runbooks are `infra/*.md`, which step 9 exempts from the doc map, so they
  need no owning-doc edit themselves. TECH_STACK → Production Deployment should *point at*
  `infra/RUNBOOK.md` (the release procedure) and `infra/incident-diagnostics.md`, and its
  "git-integration auto-deploys" line becomes "builds on merge, staged; the runbook promotes"
  (item 8). The file-structure tree's `infra/` line lists the new files.

- Step 10 (PR1b): BACKEND_STRUCTURE → Code Organization (`gate_logging.py`, already routed by PR1a) and the middleware / error-handling description of the gate (six logged reasons, body unchanged); incident-diagnostics → 421 entry (first step: read the `reason`) — step 23.

- Step 11 (PR1b): TECH_STACK → Infrastructure / env vars (`GATE_BREAK_GLASS`, `fly.toml [env]`); incident-diagnostics → Break-glass Mode A is now live (step 23).

- Step 12 (PR1b): BACKEND_STRUCTURE → the `/healthz` endpoint row (`:781`, stale audit) now reports `version`, `gate_break_glass` and (step 14) `jobs`, `no-store`; TECH_STACK → env vars (`GIT_COMMIT`, build arg). RUNBOOK §2 step 2 already passes `--build-arg GIT_COMMIT`.

- Step 13 (PR1b): BACKEND_STRUCTURE → Database Schema (`job_heartbeats` definition) and the ER diagram (`:45`, stale audit); RUNBOOK's migration-listing row for the PR1b release names `1b6b462491fa` as additive and reversible (step 23 notes it; the release row is PR2's).

- Step 14 (PR1b): BACKEND_STRUCTURE → Code Organization (`job_health.py`, routed in PR1a), the `/healthz` row (the `jobs` contract), Background Job Pattern (the web-side refresher); TECH_STACK — none. LESSONS: Pydantic pattern anchor (done in this step).

- Step 15 (PR1b): BACKEND_STRUCTURE → Background Job Pattern (the `task_postrun` heartbeat, beat tasks only, the error write) and REVIEW_CHECKLIST → Celery "sync intervals … documented in BACKEND_STRUCTURE"; incident-diagnostics → Background jobs (the WARNING lines as the tiebreaker) — step 23.

- Step 16 (PR1b): BACKEND_STRUCTURE → Code Organization (`app/cli/`, routed in PR1a) and the auth service description; RUNBOOK → a password-rotation section (step 23; deferred from PR1a, deviation 7).

- Step 17 (PR1b): TECH_STACK → Operator tooling (`paused.json` row; `release-smoke.py`'s PAUSE outcome and the new liveness check); RUNBOOK (a declared pause in the smoke expectations; the rollback skip list gains `healthz_version` for a pre-PR1b image), incident-diagnostics (a deliberate pause; the overdue review date), TODOS P1 ("empty infra/paused.json" in the resume steps) — step 23.

- Step 18 (PR1b): TECH_STACK → CI/CD Pipeline (a second workflow, `ops-check.yml`: schedule, groups, retry, `FLY_API_TOKEN`) and Environment Variables / secrets (`FLY_API_TOKEN` GitHub secret); development-commands → CI parity (the cron runs the documented operator command); RUNBOOK → token creation and rotation, the first dispatch (step 23).

- Step 19 (PR1b): FRONTEND_STRUCTURE → the shared `lib/serverTime.js` and `components/shared/FreshnessDot.jsx`, Settings; FRONTEND_GUIDELINES → §1 status colors (sage success, stock red error) and §5 the freshness-dot pattern (design-watched; expect design-sync drift).

- Step 20 (PR1b): FRONTEND_STRUCTURE → hooks (`useBackgroundJobs.js`, the first non-auth `useQuery`); REVIEW_CHECKLIST's TanStack polling exception is recorded in the hook's docstring (the plan's recorded exception).

- Step 21 (PR1b): APP_FLOW → Settings (the Background jobs card and the top alert, their states and copy) and the screen inventory; FRONTEND_STRUCTURE → Settings (`BackgroundJobsSection`, `BackgroundJobsAlert`, the page header); FRONTEND_GUIDELINES → §5 patterns (the freshness dot, the inline status alert).

- Step 22 (PR1b): APP_FLOW → §4 Error Handling (the redirect is not silent: the bounce banner, now with its likely causes; the "silent one-shot redirect" note is stale — stale audit).

- Step 24 (PR2): none outside `infra/` (exempt from the doc map: `infra/*.md`). The RUNBOOK is itself the owning doc for the release procedure.

- Step 25 (PR2): none outside `infra/`. The plan's open question 4 and the test artifact's edge case now point at the diagnostics entry.

- Step 26 (PR2): none outside `infra/`.

- Step 27 (PR2): none outside `infra/`; TODOS P1's step 5 gains a pointer to the M7 sweep item (step 30).

- Step 28 (PR2): IMPLEMENTATION_PLAN → Phase 2 "Explicitly deferred to v1.1" (applied in the step, since the contract is the step's deliverable); the epic body; the parent plan's open item 8.

- Step 29 (PR2): IMPLEMENTATION_PLAN (Known Gaps, Prioritization, Locked architecture), PRD §11 (applied in the step); the M8 row and Phase 2 count are `/ship`'s.

- Step 30 (PR2): TODOS.md and LESSONS.md (applied in the step).

## Update-docs conclusion

```
DOC SYNC REPORT — default — prod-launch-release vs master — 2026-09-21

| Doc | Section | Action | Summary |
|---|---|---|---|
| TECH_STACK.md | Infrastructure (Production Deployment) | updated | Vercel builds Staged and the runbook promotes after Fly; build-commit stamp needs "expose System Env Vars"; web=1/worker=1/beat=1 set out-of-band, pinned in infra/fly-scale.json; database is unmanaged Postgres Flex 17.2 (snapshots; WAL backups are item 12) |
| TECH_STACK.md | Infrastructure (Environment Variables) | updated | VITE_GIT_COMMIT (build-time); CLOUDFLARE_API_TOKEN (operator-only, never CI) |
| TECH_STACK.md | Infrastructure (Operator tooling, new) | updated | three runbooks, release-smoke.py, cloudflare-drift.py, fly-scale.json; host-side; tests |
| TECH_STACK.md | CI/CD Pipeline | updated | five jobs: infra-tests added; frontend-tests builds with VITE_GIT_COMMIT and greps the stamp; deploy.yml row links RUNBOOK |
| TECH_STACK.md | ToC; §8 File Structure | updated | ToC now lists §6–§8; infra/ line lists the new files |
| development-commands.md | Critical Rule; CI paragraph; Operator Scripts (new) | updated | infra/ host-side exception; five CI jobs; operator-script commands; header links to AGENTS.md/CLAUDE.md fixed (broken since the PR #42 move) |
| AGENTS.md | Development Commands | updated | host-side exceptions include infra/ scripts and infra/tests |
| IMPLEMENTATION_PLAN.md | Phase 2 → M8 row | updated | status implementing (epic-get), plan link |
| LESSONS.md | Decisions | updated | one row from /execute-plan: a remote probe's exit class follows where the failure happened |
| BACKEND_STRUCTURE.md | Code Organization | no change | no backend code in PR1a; the doc_map routes for PR1b's cli/gate_logging/job_health are in place |
| IMPLEMENTATION_PLAN.md | Locked architecture | no change | "Fly managed Postgres" quotes the epic's locked decision; the plan assigns epic-text reconciliation to PR2 |
| PRD.md | 5.12 Hosting / 7 Tech Stack | no change | "Managed PostgreSQL" is scope wording; same PR2 reconciliation |
| REVIEW_CHECKLIST.md | Alembic, PostgreSQL → Operations | no change | the two RUNBOOK.md citations now resolve to a real file (criterion 19) |
| config.json | doc_map | updated | (step 9) cli/**, gate_logging.py, job_health.py → BACKEND_STRUCTURE Code Organization; infra/*.md exempt, reason in exempt_notes |

Guard: doc-guard --staged --dry-run -> would pass
Questions: 0 asked
Unmapped: none

DOC IMPACT: updated 5 docs
```

The index is staged (update-docs step 8) and nothing is committed; `/ship` commits.
`doc-guard --worktree` also passes.

### PR1b

```
DOC SYNC REPORT — default — prod-launch-release vs origin/master — 2026-09-23

| Doc | Section | Action | Summary |
|---|---|---|---|
| BACKEND_STRUCTURE.md | Database Schema; ER diagram | updated | JobHeartbeat entity and ERD box; `job_heartbeats` table definition (revision 1b6b462491fa) |
| BACKEND_STRUCTURE.md | API endpoints (/healthz row); host gate paragraph | updated | /healthz reports version, gate_break_glass, jobs (memory-only, no-store); six logged gate reasons, 421 body unchanged, GATE_BREAK_GLASS bypass |
| BACKEND_STRUCTURE.md | Code Organization (tree) | updated | app/cli/, gate_logging.py, job_health.py |
| APP_FLOW.md | Settings; "Checking background jobs (M8)"; §4 Error Handling | updated | the card and top alert, their six states and copy; the bounce banner now names its likely causes (the "silent redirect" note was stale) |
| FRONTEND_STRUCTURE.md | lib, hooks, pages/settings, shared inventories; behavioral notes | updated | serverTime.js, useBackgroundJobs.js, BackgroundJobsSection/Alert, FreshnessDot; counts 11/11 |
| FRONTEND_GUIDELINES.md | Status colors; patterns | updated | fresh/overdue status colors; the freshness line (dot + words); the inline status alert (not a banner) |
| TECH_STACK.md | Environment Variables; CI/CD Pipeline; Operator tooling; §8 tree | updated | GATE_BREAK_GLASS, GIT_COMMIT, FLY_API_TOKEN; ops-check.yml row; release-smoke PAUSE outcome and check 1 version-reported; infra/paused.json |
| development-commands.md | Multi-target Dockerfile; CI paragraph | updated | prod stage takes GIT_COMMIT; ops-check.yml runs the operator command daily |
| PRD.md | 5.7 User Authentication (Password Recovery) | updated | pointer: the CLI shipped in M8 as app.cli.rotate_password, procedure in RUNBOOK §6 (behavior text already matched) |
| TODOS.md | P1 Resume the Celery worker and beat | updated | resume step 3: empty infra/paused.json in a pull request |
| LESSONS.md | Pydantic pitfalls; Verify current state; Corrections Log | updated | Rust-regex `\z` bullet; the blocker-vs-signal rule; two 2026-09-23 rows (one user, one self) |
| IMPLEMENTATION_PLAN.md | Phase 2 → M8 row | no change | stays `implementing` with PR1a's link until /ship records PR1b |
| REVIEW_CHECKLIST.md | Pydantic | no change | the `\z` rule lives in LESSONS; the checklist is not doc-map-owned by this diff |
| AGENTS.md | — | no change | no new command, service or host-side exception (infra/ was added in PR1a) |
| infra/RUNBOOK.md, infra/incident-diagnostics.md | (exempt from the map) | updated | step 23: token creation, the pause, §6 rotation, break-glass, gate reasons, the jobs card and cron |

Guard: doc-guard --staged --dry-run -> would pass (docs staged: APP_FLOW, BACKEND_STRUCTURE, FRONTEND_GUIDELINES, FRONTEND_STRUCTURE, PRD, TECH_STACK, development-commands)
Questions: 0 asked
Unmapped: none

DOC IMPACT: updated 9 docs
```

The index is staged and nothing is committed; `/ship` commits.

### PR1b, at `/ship` (2026-09-24)

Re-run after `/review-implementation` and `/final-review` changed code. Every owning section
already described their fixes; this run made no edits. The count differs from the report
above because the reviews also updated REVIEW_CHECKLIST.md.

```
DOC SYNC REPORT — default — prod-launch-release vs master — 2026-09-24

| Doc | Section | Action | Summary |
|---|---|---|---|
| BACKEND_STRUCTURE.md | Database Schema; ER diagram | updated | JobHeartbeat entity and `job_heartbeats` table (revision 1b6b462491fa) |
| BACKEND_STRUCTURE.md | API endpoints (/auth/login, /auth/refresh, /auth/logout, /healthz); host gate paragraph | updated | `auth_session_issue` advisory lock (login/refresh shared; logout and rotation exclusive); /healthz version, gate_break_glass, jobs, no-store; six logged gate reasons as one JSON message, ip = last X-Forwarded-For hop; GATE_BREAK_GLASS |
| BACKEND_STRUCTURE.md | Code Organization | updated | app/cli/rotate_password.py, gate_logging.py, job_health.py, the task_postrun heartbeat writer in tasks.py |
| APP_FLOW.md | Settings; Checking background jobs; §4 Error Handling | updated | the Background jobs card and top alert, six states and copy; bounce banner names its likely causes |
| FRONTEND_STRUCTURE.md | lib, hooks, settings, shared inventories; behavioral notes | updated | serverTime.js, useBackgroundJobs.js, BackgroundJobsSection/Alert, FreshnessDot |
| FRONTEND_GUIDELINES.md | Status colors; patterns | updated | fresh/overdue colors; freshness line; inline status alert |
| TECH_STACK.md | Environment Variables; CI/CD Pipeline; Operator tooling; §8 tree | updated | GATE_BREAK_GLASS, GIT_COMMIT, FLY_API_TOKEN; ops-check.yml (failure lines become error annotations); release-smoke PAUSE, [1] version-reported, jobs-fresh after-pause rule; paused.json (review_by ≤ 31 days out) |
| development-commands.md | Multi-target Dockerfile; CI paragraph | updated | prod stage takes GIT_COMMIT; ops-check.yml runs the operator command daily |
| PRD.md | 5.7 User Authentication | updated | pointer to the shipped CLI (app.cli.rotate_password, RUNBOOK §6) |
| REVIEW_CHECKLIST.md | FastAPI, PostgreSQL, Operator scripts | updated | checks added by the implementation/final reviews (log message shape, proxy-header ip, advisory-lock revoke paths) |
| LESSONS.md | Pydantic pitfalls; Verify current state; Corrections Log; Bug Log | updated | `\z` rule, blocker-vs-signal rule, 2026-09-23/24 rows |
| TODOS.md | P1 Resume worker and beat; P2/P3 items | updated | resume steps include emptying paused.json; review-added items |
| IMPLEMENTATION_PLAN.md | Phase 2 → M8 row | no change | stays `implementing` with PR1a's link; ship's second run adds PR1b's |
| AGENTS.md | Development Commands | no change | no new command, service, or host-side exception |

Guard: doc-guard --staged --dry-run -> would pass
Questions: 0 asked
Unmapped: none

DOC IMPACT: updated 10 docs
```

### PR2

```
DOC SYNC REPORT — default — prod-launch-release vs master — 2026-09-25

| Doc | Section | Action | Summary |
|---|---|---|---|
| (doc map) | every changed path | no change | all 15 paths are exempt (`.agents/docs/**`, `.agents/plans/**`, `.agents/state/**`, `infra/*.md`); no code, route, schema, dependency, env var, command or CI job changed |
| TECH_STACK.md | Environment Variables (operator-only) | updated | the Cloudflare drift script stays unscheduled per the v1.1 (ops) contract (was "a v1.1 item") |
| TECH_STACK.md | Infrastructure (Database row) | updated | continuous WAL backups enabled 2026-09-23; the `ops-check` token reads only snapshots (TODOS P3) |
| IMPLEMENTATION_PLAN.md | Phase 2 (Known Gaps, Locked architecture, Explicitly deferred to v1.1, Prioritization) | updated | applied in execute-plan steps 28–29: M8 in its last part; unmanaged Flex 17.2; deferred list points at the v1.1 (ops) contract. M8 row status left `implementing` for `/ship` |
| PRD.md | 11. Future Roadmap | updated | "Fly Postgres (unmanaged Flex)" (step 29); v1.0 boxes left for `/ship`'s roadmap pass |
| TODOS.md | — | updated | step 30: new P3 WAL cron token; P1, P2 rotation and P2 `Fly-Client-IP` pointers |
| LESSONS.md | Bug Log; `fly deploy` section; Runbook checks | updated | step 30: the 2026-09-23 worker incident; "Merged is not deployed"; `${RELEASE:?}` |
| AGENTS.md | — | no change | no command, structure, dependency or env var changed |
| config.json | doc_map | no change | no unmapped area |

Guard: doc-guard --staged --dry-run -> staged changes touch no documented areas
Questions: 0 asked
Unmapped: none

DOC IMPACT: updated 5 docs
```

### PR2, at `/ship` (2026-09-26)

Re-run after `/review-implementation` and `/final-review` changed `infra/release-smoke.py`
(check 9) and the docs, and after criterion 6 was recorded. Every owning section already
described those changes; this run made no edits. The count is the docs this commit carries.

```
DOC SYNC REPORT — default — prod-launch-release vs master — 2026-09-26

| Doc | Section | Action | Summary |
|---|---|---|---|
| TECH_STACK.md | Infrastructure (Operator tooling: `release-smoke.py`) | updated | check 9 passes when either restore mechanism is under 48 h; one unreadable and the other stale, empty or off is exit 1; exit 2 only when neither is read (the only mapped path on the branch: `infra/release-smoke.py`) |
| TECH_STACK.md | Infrastructure (Database row; Environment Variables) | updated | WAL backups enabled 2026-09-23 and the `ops-check` token reads only snapshots (TODOS P2); the drift script stays unscheduled per the v1.1 (ops) contract. The `ops-check.yml` row carries no stale exit-class claim |
| IMPLEMENTATION_PLAN.md | Phase 2 (Known Gaps, Locked architecture, deferred list, Prioritization) | updated | execute-plan steps 28–29; the M8 row stays `implementing` with PR1a/PR1b links until `ship-record` |
| PRD.md | 5.12 Hosting; 11. Future Roadmap | updated | "Fly Postgres (unmanaged Flex)" in both places |
| REVIEW_CHECKLIST.md | Operations (health checks … CI parity) | updated | three review-added checks: a stamped deploy asserts HEAD and a clean tree, a log proof greps its own marked request, a multi-mechanism check exits as production when something it read fails |
| LESSONS.md | Bug Log; `fly deploy`; Runbook checks | updated | the 2026-09-23 worker incident, "Merged is not deployed", `${RELEASE:?}` and its nested-subshell caveat, the access-token proof rule |
| TODOS.md | P1; P2 rotation; P2 continuous backups; P2 `Fly-Client-IP`; two visual-tests P2s | updated | the rotation P2 added at the PR1b release and marked done 2026-09-26 (criterion 6); the continuous-backups P2 retitled with the WAL cron-token note folded in; `visual-tests` timeout hang and `mealcard-undo.spec.js` width added (review decisions) |
| AGENTS.md | Development Commands | no change | no command, structure, dependency or env var changed |
| config.json | doc_map | no change | no unmapped area |

Guard: doc-guard --staged --dry-run -> would pass
Questions: 0 asked
Unmapped: none

DOC IMPACT: updated 6 docs
```

## Completion

- Completed: 2026-09-21T23:36:43Z. Scope: **PR1a** of M8 (steps 1–9). PR1b and PR2 are
  still to come under this plan.
- **What was built.**
  - The operator tooling that makes a release a written, mechanically checked procedure:
    - `infra/RUNBOOK.md` (release: gates, backend-first deploy, promote by SHA, smoke,
      Cloudflare and manual checks, tagging, two-doctrine rollback, execution log);
    - `infra/incident-diagnostics.md` (one entry per failure mode, including break-glass
      Mode A/B and the real-restore data-loss path);
    - `infra/backup-restore-drill.md` (both restore paths into dated scratch clusters,
      and a restore-point log);
    - `infra/release-smoke.py` (nine checks in four groups; exit 0 pass, 1 production,
      2 tooling; `--only`, `--skip`, `--release-commit`, `--self-test`; the
      `/healthz.jobs` contract reader ready for PR1b);
    - `infra/cloudflare-drift.py` (read-only, structural redaction).
  - `infra/fly-scale.json` pins `web=1 worker=1 beat=1`.
  - The frontend build stamps its commit into `<meta name="build-commit">` (`vercel.json`
    `buildCommand`).
  - CI gains `infra-tests` and a stamped-build step.
  - The expired break-glass line in `cloudflare-state.md` now points at the working
    design.
  - The doc map routes PR1b's modules ahead of time and exempts `infra/*.md`.
  - No application code and no migration, as Eng review 0 intended for PR1a.
- **Test results** (commands from development-commands.md):
  - backend `docker-compose exec api uv run pytest` → **915 passed, 3 skipped**;
  - frontend `npm run test:run` → **550 passed (57 files)**, `npm run lint` → exit 0
    (0 errors; 7 warnings, all in files this branch does not touch);
  - `python3 -m pytest infra/tests -q` → **99 passed**;
  - `python3 -m pytest .agents/tests -q` → **504 passed**;
  - visual regression (api-test, frontend-preview and frontend-visual rebuilt) →
    **7 passed**, with the preview's `index.html` carrying the literal
    `%VITE_GIT_COMMIT%`, as documented;
  - `doc-guard --staged --dry-run` → would pass, and `--worktree` → pass.
  - Mutation checks: 5 smoke and 3 drift regressions, plus 2 renamed-heading link
    controls. Each turned the suite red, and each file was restored `cmp`-identical.
- **Test-artifact gaps.** No fixture was captured from production (assumption 5). The first
  real smoke run (Between-the-PRs step 3) is the integration point for flyctl's JSON shapes
  and the `fly pg backup list` table; a mismatch is exit 2, never a pass. The `fly ssh`
  transport of check 4 is unproven. Its probe code was run end to end against the local
  Compose worker. Critical paths 5–13 are operator-executed, and belong in PR2 by design.
- **Deviations from the plan:**
  1. Check 6 is the credential-free half (a no-cookie 401 must keep `private, no-store`
     and must not be an edge `HIT`). The logged-in `private, no-cache` check is a manual
     RUNBOOK step (assumption 4, approved).
  2. `--release-commit` is required when the release group runs, rather than defaulting to
     HEAD (assumption 6).
  3. `vercel.json` uses `npm run build` rather than `vite build` (assumption 10).
  4. `doc_map.exempt_notes` holds the exemption's reasoning (assumption 9).
  5. Bot Fight Mode is recorded as "not yet recorded" (assumption 8).
  6. Found during step 6: check 4 now treats a traceback raised on the machine as exit 1,
     not exit 2 (LESSONS Decisions row).
  7. The password-rotation runbook section is left for PR1b, with the CLI it documents.
- **Carried, not reopened:** the GitHub 60-day scheduled-workflow disable (RUNBOOK header
  re-arm); OQ 1 (token scopes listed and confirmed at step 6), OQ 2 (cadence stated as a
  default), OQ 4 (recorded as observed); Mode B (accepted risk, written down); the
  web-restart re-arm of the never-run grace (diagnostics).
- **Status: DONE_WITH_CONCERNS.**
  1. **/ship will mark the whole plan shipped after PR1a.** Its "Record shipped" step sets
     `implementation_status=shipped` on the plan, the registry and the M8 milestone row
     unconditionally. `/execute-plan` then refuses PR1b ("This plan shipped"). This is a
     framework gap with no partial-ship mode; the user decides at `/ship`. A framework task
     has been suggested.
  2. `IMPLEMENTATION_PLAN.md` → Locked architecture and `PRD.md` still say "Fly managed
     Postgres". TECH_STACK now states the truth (unmanaged Flex 17.2), and the plan assigns
     the epic-text reconciliation to PR2.
  3. **Operator steps precede the PR1a deploy** (Between the PRs 0–1):
     - the two Vercel toggles (after `vercel login`);
     - confirm a restore point exists, and enable continuous backups if they are still
       off (item 12 was due "today" on 2026-09-12, and nothing here verified it);
     - `fly scale count web=1 -a mealy-app-prod`, without which smoke check 3 fails on the
       first run.

### PR1b

- Completed: 2026-09-23T19:14:44Z. Scope: **PR1b** of M8 (steps 10–23). PR2 (the operator
  release, the drills, the epic-text reconciliation) is still to come under this plan.
- **What was built.**
  - The host gate logs which of six checks rejected a request (`app.gate`, never the secret,
    421 body byte-identical, emitter failures swallowed), and `GATE_BREAK_GLASS=1` in
    `fly.toml [env]` skips only origin-verify, logging every admitted bypass.
  - `/healthz` reports the deployed commit (`GIT_COMMIT` build arg), the break-glass flag and
    a `jobs` reading, served from memory with `Cache-Control: no-store`. A lifespan task
    refreshes the reading every 30 s from the new `job_heartbeats` table (revision
    `1b6b462491fa`, additive, reversible), and a Celery `task_postrun` hook upserts a
    heartbeat for each successful `beat_schedule` task, or records the error.
  - `python -m app.cli.rotate_password <email>` rotates the household password and revokes
    every session in one commit (exit 0/1/2).
  - `infra/release-smoke.py` gains check 1 `version-reported` and a checked-in pause
    declaration (`infra/paused.json`, worker and beat since 2026-09-23, review by
    2026-10-23): a paused group must be stopped, check 4 and jobs-fresh print `PAUSE`
    (never pass), the summary counts paused groups, and a past review date fails.
  - `.github/workflows/ops-check.yml` runs the liveness, recoverability and edge groups daily
    with a read-only Fly token, retrying once.
  - Settings gains a Background jobs card and a one-line top alert (six states, one live
    region). The iCloud line shares the new `FreshnessDot` and `serverTime.js`. The sign-in
    bounce banner names its likely causes.
- **Test results** (commands from development-commands.md, 2026-09-23):
  - backend `docker-compose exec api uv run pytest` → **1044 passed, 3 skipped** (the first
    run collapsed to 91 failed / 264 errors on the visual seed left in `todo_app_test`, the
    documented one-time collapse; the re-run is the result);
  - frontend `npm run test:run` → **630 passed (61 files)**; `npm run lint` → 0 errors,
    7 warnings, all in files this branch does not touch; `npm run hygiene` → the 12
    pre-existing unused exports (a 13th, `HEALTHZ_QUERY_KEY`, was mine: the tests now import
    it instead of hardcoding `['healthz']`);
  - stamped build (`VITE_GIT_COMMIT`, production `VITE_API_BASE_URL`) → exit 0, and
    `dist/index.html` carries `37334a5…`;
  - migrations: `upgrade head` → `downgrade -1` (1b6b462491fa → b7e2c9a4f1d8) →
    `upgrade head`, current `1b6b462491fa (head)`;
  - visual regression (`todo_app_test` reset, api-test, frontend-preview and frontend-visual
    rebuilt, `--reporter=list`) → **7 passed**; visual containers removed with `rm -sf`;
  - `python3 -m pytest infra/tests -q` → **155 passed**; `python3 -m pytest .agents/tests -q`
    → **636 passed**; `release-smoke.py --self-test` → the expected
    `exit 1 production: [3] scale-reconciled`;
  - `doc-guard --staged --dry-run` → would pass.
  - Mutation checks on every key rule (gate reasons, the emitter wrapper, stale thresholds,
    the unusable reading, the SUCCESS/beat filter, the rotation's single commit, each pause
    rule, the state ladder and the status region): each turned its suite red and was restored.
- **Test-artifact gaps.**
  - Not exercised against production, by design: the PR1b smoke checks and the PAUSE outcome
    run at Between the PRs steps 7–10, after PR1b merges and deploys; `ops-check.yml` needs
    the `FLY_API_TOKEN` secret (RUNBOOK) and the merge before its first dispatch.
  - The rotation CLI was run against the local stack only; the `fly ssh console --select`
    TTY path is the operator's first run.
  - The 375 px page overflow on Settings comes from the pre-existing FamilyMemberManager "Add"
    button (33 px), outside PR1b; the 375 px check was scoped to the PR1b elements.
- **Deviations from the plan:**
  1. The server-aligned clock uses the fetch outcome time (`max(dataUpdatedAt,
     errorUpdatedAt)`), not `Date.now()` in render, which `react-hooks/purity` forbids; the
     fetch gets a 10 s `AbortSignal.timeout` so a hung request still settles.
  2. `version-reported` is a new check in the liveness group (`[1]`, skip key
     `healthz_version`) rather than a field inside an existing check.
  3. The CLI's exit 2 covers any database-layer failure (`DBAPIError`, `OSError`, a
     timeout), not only a connection error, so a schema fault is not a traceback.
  4. The pause declaration is the user's approved addition of 2026-09-23 (`infra/paused.json`).
  5. A past `review_by` fails **every** run, not once (approved assumption 2); the user was
     told.
  6. PRD 5.7 gains a pointer to the shipped CLI; its behavior text already matched.
- **Status: DONE_WITH_CONCERNS.**
  1. Between the PRs steps 2–6 have not run: PR1a is merged but not deployed, and production
     still runs v33 (before #49). If PR1b merges first, the first deploy carries both, and
     step 3's PR1a skip list no longer applies; step 8's full smoke does.
  2. Step 8 says "every group must pass". While `infra/paused.json` declares the worker and
     beat, check 4 and jobs-fresh print PAUSE, never pass, and the Settings card reads the
     jobs overdue (the truth). At that step the operator either records PAUSE as the outcome
     or resumes the worker first (TODOS P1).
  3. `FLY_API_TOKEN` must be created and set before `ops-check.yml`'s first run (RUNBOOK),
     or the daily run fails as tooling.
  4. A TODOS candidate, not added: the pre-existing 375 px overflow from the
     FamilyMemberManager "Add" button on Settings.
- State synced 2026-09-23T19:16:24Z: plan and registry `implementation_status=ready-for-review`, `reason_by=execute-plan` (the concerns above).

### Concerns addressed, and Between the PRs executed (2026-09-23, after PR1b's implementation)

- **Concern 1 (PR1a undeployed):** the operator chose to keep the reviewed order and deploy PR1a
  before PR1b merges.
  - Step 2: released as `v1-20260923-f0a8d81`. Fly v34; Vercel `dpl_Gzqsu1SKbRJnVCKGWQKMLUj3uZUD`,
    promoted by SHA; no migrations; ~4 s downtime.
  - Step 3: the smoke ran from this branch's script, for the pause. Exit 0: 8 passed, 4 skipped,
    1 paused.
  - Step 4: the rollback dry-run went to `1087f30` / v33's image as v35, then forward as v36,
    with smoke exit 0 on both sides.
  - Step 6: drift `exit 0: no drift`.
  - The Cloudflare dashboard checks (3/3) and the manual checks (4/4) passed. The R2 upload with
    boto3 1.43.90 closed that TODOS item.
  - Step 5 (restore drill): both paths passed; the operator granted four narrow permission
    rules for the production reads, and removed them after.
    - Path 1, the 22 h-old snapshot: restored in 68 s.
    - Path 2, point-in-time to 19:55Z: restored in 50 s. Replay was proven by a refresh token
      issued at 19:42Z. The first attempt, at 22:13Z, failed because the archived WAL ended
      near 20:37Z; that is a new TODOS P2 on the recovery-point lag.
    - Neither scratch cluster archives into production's bucket.
    - The operator destroyed all three scratch apps; `fly apps list` showed none at 22:53Z.
  - The CI gate used the operator-approved equivalence with `91edffa`: `visual-tests` hit its
    25-minute timeout on a pre-existing report-server hang, which a separate task is fixing.
  - Procedure fixes: RUNBOOK §2 step 4 (CLI promote), §5.1 and §5.2 (Promote, not Instant
    Rollback; a tag names the previous release), and the plan's Assignment note, which carries
    the observed correction. LESSONS gained the rule. Everything is logged in
    `infra/RUNBOOK.md` and `infra/backup-restore-drill.md`.
- **Concern 2 (step 8 vs PAUSE):** the plan's step 8 now states the pause exception. The run
  exits 0 with the paused groups counted, and a PAUSE is never written up as a pass.
- **Concern 3 (`FLY_API_TOKEN`):** the operator created it (19:44:07Z). RUNBOOK: created
  2026-09-23; rotate by 2027-09-23. The first dispatch waits for PR1b's merge.
- **Concern 4 (375 px overflow):** added to TODOS.md as a P3.

### Between the PRs 7–11 executed (2026-09-24, after PR1b merged as #62)

Recorded for PR2. The agent guided each step. Auto mode blocked its first production command (`fly ssh console`), so the
operator ran every production command, and the agent ran the local, GitHub, and public-URL reads.

- **Step 7, release `v1-20260924-f4a6814`** (squash `f4a6814`).
  - Fly v37 (`registry.fly.io/mealy-app-prod:deployment-01M38VT0SGJF6EHM9Q5J5CQYYT`). Vercel
    `dpl_AoaGZKAo9i18SMP3vrQBZpxGcTh3`, promoted by SHA.
  - Gates: CI `Tests` success (run 35953955035); doc-guard passed on #62; `ops-check` n/a (never
    run); restore point `exit 0` (snapshot 5 h, WAL 11 h).
  - Migration: production was at `b7e2c9a4f1d8`; this release applied `1b6b462491fa` (additive,
    downgrade written and tested by migration-upgrade CI).
  - Downtime ~6 s (04:47:45–04:47:50Z).
  - `fly status`: web started with 1/1 checks passing; worker and beat stopped (the declared pause).
  - The deploy's spinner pushed the `release_command` output out of the terminal scrollback. The
    migration was confirmed from `/healthz`: `jobs.read: ok` can only happen once `job_heartbeats`
    exists, and `version` read `f4a6814…`.
  - A rollback worktree at the PR1a tag, with the §5.2 command pasted, was ready and not needed.
- **Step 8.**
  - Smoke: `exit 0: 11 passed, 0 skipped, 2 paused (beat, worker declared in infra/paused.json)`;
    check 8 matched `f4a6814` on both tiers.
  - The Cloudflare dashboard checks and the manual checks passed, as the operator reported.
  - Tagged `v1-20260924-f4a6814`.
  - **Finding: the gate's `ip` logs the app's own address, not the caller's.**
    - Observed: the smoke probe logged `66.241.124.153`, and a `*.fly.dev` curl with a forged
      `X-Forwarded-For: 203.0.113.9` logged `2a09:8280:1::10e:a0e0:0`. Those are the A and AAAA
      records of `mealy-app-prod.fly.dev`. The forged value never appeared, and `reason` was right
      on both lines.
    - Cause: Fly's docs describe `X-Forwarded-For` as the client *followed by* the proxies, so its
      last entry is Fly's edge. They recommend `Fly-Client-IP`, "always set by the Fly Proxy".
    - Fixed by quickfix `gate-log-fly-client-ip` (#64, `56e0c39`): the gate logs `Fly-Client-IP`,
      and the BACKEND_STRUCTURE gate paragraph, LESSONS Bug Log and REVIEW_CHECKLIST → FastAPI are
      corrected. Not yet deployed.
    - The next release proves it: a direct request carrying a forged `Fly-Client-IP` must log the
      caller's real address. Fly's docs don't say whether they overwrite a client-sent value.
      Tracked as TODOS.md P2 "Prove at the next release that Fly overwrites a client-sent
      `Fly-Client-IP`" (added by #64).
- **Step 9: skipped by the operator.** Recorded as TODOS.md P2 "Run the password-rotation CLI end to
  end in production (M8 criterion 6, skipped at the PR1b release)", uncommitted on this branch. Until
  it runs, criterion 6 is open; PR2 records it as deferred, not met.
- **Step 10.**
  - The first dispatch, run 36009722470, exited 2: `` `fly` is not on PATH `` on `[9]` and `[5]`.
    `setup-flyctl` installs only `flyctl`. Fixed by quickfix #63 (`29f4b75`, the "Expose flyctl as
    fly" step and `infra/tests/test_ops_check_workflow.py`).
  - Branch proof, run 36017858233: green.
  - Master dispatch, run 36058117263: green, `exit 0: 7 passed, 0 skipped, 1 paused`.
  - Self-test, run 36058128975: failed as designed. Its annotations were
    `FAIL [jobs] jobs-fresh: … → infra/incident-diagnostics.md#background-jobs-dead-worker-or-beat`
    and `exit 1 production: [jobs] jobs-fresh (self-test: …)`. **The failure email showed both
    annotations** (operator-verified), so criterion 17 is met.
  - The first scheduled run, 36041300063, fired at 18:26:58Z, 4 h 10 min after its 14:17 slot. It
    failed on the PATH bug, before #63 merged. Scheduled runs can be hours late.
  - **Finding: the cron cannot see WAL backups.**
    - `[9]` passes on the volume snapshot, with `also: fly pg backup list exited 1: Error: failed to
      exec on VM 6835444b795398: unauthorized`. That read runs a command on the Postgres VM, which a
      `fly tokens create readonly` token cannot do.
    - Release-time smoke from a laptop still reads WAL backups.
    - PR2: correct the RUNBOOK. Its first-run criterion ("no `also:` part") cannot hold with this
      token. Its "drop the cron to its credential-free checks" sentence would remove `[9]` and `[5]`
      for a gap in one sub-read.
    - PR2: add a TODO to investigate `fly tokens create machine-exec` for that one read, linked to the
      WAL-lag P2.
- **Step 11: rehearsed locally** (criterion 15 met).
  - Setup: a throwaway `docker-compose run` of the `api` service on :8099 with `APP_ENV=production`,
    `PUBLIC_API_HOST=api.mealy.dev`, `CORS_ALLOW_ORIGINS=https://mealy.dev`, `STORAGE_BACKEND=local`,
    and dummy hex secrets for `ORIGIN_VERIFY_SECRET`, `JWT_SECRET_KEY` and `HOUSEHOLD_ACCESS_KEY`.
    Command `uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'`.
    The dev api on :8000 was untouched.
  - Flag `"0"`: `/healthz` false; a right Host with no origin header got 421 `origin_verify_absent`;
    the right header got 200; `Host: mealy-app-prod.fly.dev` got 421 `host_mismatch`.
  - Flag `"1"`: `/healthz` true; a right Host with no header got 200, logged `outcome="bypassed"`;
    the right header got 200, also logged `bypassed`; the wrong Host still got 421 `host_mismatch`.
  - Flag `"true"`: the same as `"0"`, because the parse is strict.
  - PR2: put the rehearsal command in `infra/incident-diagnostics.md` → Break-glass ("Rehearse it").
- **Procedure fixes for PR2's RUNBOOK.**
  1. Write `${RELEASE:?}` wherever a command reads `$RELEASE`. §2 step 4's URL lookup ran in a fresh
     shell without it and took the newest deployment. That happened to be the right one, and
     `mealy.dev` then served `f4a6814`. The smoke refused an empty flag with exit 2.
  2. Keep `fly deploy`'s output (for example `| tee`), or confirm the migration from `/healthz`
     (`jobs.read: ok`), because the spinner scrolls the `release_command` lines away.
  3. Scheduled `ops-check` runs can fire hours late; the "latest run under 48 h" gate still works.
  4. In auto mode an agent cannot run production commands. The operator runs them, or grants narrow
     rules and removes them afterwards.
- **CI problems seen on #63, outside M8's code; separate sessions started for both:**
  - the `BackgroundJobsSection` loading test races under `shouldAdvanceTime`;
  - `mealcard-undo.spec.js` width fails deterministically since about 07:00Z on 2026-09-24
    (5.497 px against a 5 px tolerance, locally and in CI). The Playwright HTML report server still
    hangs a failed visual job until its 25-minute timeout.

### PR2

- Completed: 2026-09-25T03:28:29Z. Scope: **PR2** of M8 (steps 24–30), the last declared part. No
  application code and no migration.
- **What was built.**
  - The runbooks now record the PR1b release (`v1-20260924-f4a6814`) and every correction it
    revealed:
    - RUNBOOK: the execution-log row, `${RELEASE:?}` on every command that reads it, a
      `tee`d deploy plus an `alembic current` check after a migration release, late scheduled
      runs, who runs production commands, Vercel's Save-then-reload, and a `FLY_API_TOKEN`
      first-run rule that expects the cron's refused WAL read;
    - diagnostics: break-glass is available, with a local rehearsal (re-run in this session,
      same results as step 11), and the cron's `also:` line is explained;
    - drill §0: the three steps it takes to enable backups.
  - Open question 4 is answered by a production read: the DB primary has not idle-stopped
    since the PR1b release. The M7 runbook's `fly status` box is struck, and its sweep item
    is re-recorded as open behind the worker pause.
  - The v1.1 (ops) scope contract is written in the epic: 4 In, 2 Gated, 4 Out. The parent
    plan's item 8 is closed, and IMPLEMENTATION_PLAN points at the contract.
  - The epic records what M8 shipped against each Done-when criterion.
  - "Fly managed Postgres" is corrected in three docs.
  - TODOS gains the WAL cron-token P3. LESSONS gains the 2026-09-23 worker incident and two
    rules: "Merged is not deployed" and `${VAR:?}`.
- **Test results** (commands from development-commands.md, 2026-09-25):
  - backend `docker-compose exec api uv run pytest` → **1059 passed, 3 skipped**;
  - frontend `npm run test:run` → **632 passed (61 files)**; `npm run lint` → 0 errors,
    7 warnings (none in files this branch touches: PR2 touches no frontend file);
  - `python3 -m pytest infra/tests -q` → **165 passed**;
  - `python3 -m pytest .agents/tests -q` → **636 passed**;
  - `release-smoke.py --self-test` → the expected `exit 1 production: [3] scale-reconciled`;
  - `doc-guard --staged --dry-run` → "staged changes touch no documented areas";
    `--worktree` → pass.
  - The visual suite was not run. PR2 changes no frontend or backend file (assumption 8).
- **Test-artifact gaps.** Critical path 5 (rotation over SSH) has not been run. The operator
  will run it before `/ship` (option A). The worker-side halves of critical paths 4 and 8 stay
  unproven in production while the worker is paused (assumption 3; TODOS P1): check 4's round
  trip, the first `job_heartbeats` rows, and the card's "All running on schedule".
- **Deviations from the plan.**
  1. The runbooks gained two items that no step 7–11 note named. RUNBOOK §2 step 7 has a
     one-time pointer to the `Fly-Client-IP` proof, so the next release does not miss it.
     The epic has a "What M8 shipped" block, which carries "PR2 updates the epic text"
     without rewriting the criteria.
  2. Open question 4 was answered from an agent-run production read. It was read-only and
     not blocked, unlike step 7's `fly ssh console`.
  3. The WAL cron-token TODO is P3, not P2 (step 28's reasoning).
- **Status: DONE_WITH_CONCERNS.**
  1. **M8 criterion 6 is still open.** Run RUNBOOK §6 in production before `/ship` (the
     operator chose option A). Then record: a RUNBOOK execution-log row (the CLI's output
     line, old password refused, new accepted, a signed-in tab bounced with the banner); the
     epic's rotation bullet turned from "pending" to met; TODOS P2 marked done. The last part
     must not ship with it pending.
  2. **One detail comes only from the agent's notes:** drill §0 step 3 (`fly secrets deploy`
     after enabling, "a restart did not apply them"). The operator should confirm it in
     review.
  3. **Known and accepted:** #64 (`Fly-Client-IP`) is merged but not deployed. The next
     release proves it (RUNBOOK §2 step 7, TODOS P2). The worker-side evidence waits for the
     resume (TODOS P1).
- State synced 2026-09-25T03:28:50Z: plan and registry `implementation_status=ready-for-review`, `reason_by=execute-plan` (the concerns above).
- **Superseded after this run** (recorded by `/final-review`, 2026-09-25): the WAL cron-token
  P3 named in steps 28 and 30, the PR2 doc-sync table, "What was built" and deviation 3 no
  longer exists. `/review-implementation` folded it into TODOS.md P2 "Continuous backups:
  the newest recovery point trails by hours, and no check asserts them on their own", and
  the RUNBOOK header and TECH_STACK's Database row cite that P2.
- **Concern 1 closed 2026-09-26:** the operator ran RUNBOOK §6 in production. It revoked 9
  refresh tokens and set the session version to 3; the old password was refused and the new
  one accepted. It is recorded in the RUNBOOK log, the epic and TODOS P2 (done). The
  access-token half was not exercised in production; the integration test covers it.
- **No longer documentation only** (`/final-review`, 2026-09-25, user decision):
  `infra/release-smoke.py` check 9 fails as exit 1 when a restore mechanism it could read is
  stale, empty or off and the other could not be read (exit 2 only when it reads neither),
  with five new tests in `infra/tests/test_release_smoke.py` (170 passed). `ops-check.yml`
  runs `master`'s script, so the change is live when PR2 merges; no deploy carries it.
