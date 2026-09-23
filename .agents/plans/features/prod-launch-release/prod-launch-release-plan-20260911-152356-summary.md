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
