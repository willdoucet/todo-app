# Release runbook

The repeatable release procedure for `mealy.dev` / `api.mealy.dev`: gates, deploy, smoke,
rollback. It covers only this one type of task. When something is broken, use
[`incident-diagnostics.md`](./incident-diagnostics.md). For the backup-restore drill, use
[`backup-restore-drill.md`](./backup-restore-drill.md).

| | |
|---|---|
| Owner | willdoucet (the operator; one operator by design) |
| Last executed | 2026-09-23, `v1-20260923-f0a8d81` (M8 PR1a, with the rollback dry-run; see the execution log) |
| Estimated duration | 30–45 min: deploy ~5, promote ~2, smoke ~2, manual checks ~10, log ~5 |
| Risk | Medium. At `web=1` every deploy replaces the only web machine in place, so the API is down for a few seconds |
| Minimum flyctl | v0.4.102 (`fly version`). The smoke script parses `--json` output that older releases shaped differently |
| Plan | `.agents/plans/features/prod-launch-release/prod-launch-release-plan-20260911-152356.md` (M8) |

**This repository is public.** GitHub disables a public repository's scheduled workflows after
60 days with no repository activity. Commits and pull requests count as activity; workflow
*runs* do not. A green daily `ops-check` does not keep itself alive. A monthly release resets
the clock. If 50 days have passed since the last commit on `master`, commit anything,
otherwise the between-release watchdog stops and nothing will say so:

```bash
git log -1 --format=%cI origin/master
```

**Credentials, by name only.** Never print a value, and never run a bare `env` or `printenv`
anywhere (LESSONS.md):

- `FLY_API_TOKEN`: GitHub Actions secret for `ops-check.yml`. It is a `fly tokens create
  readonly` token (org-scoped, read-only) with a one-year expiry. Created 2026-09-23, before
  PR1b merged; its first dispatch below still waits for the merge.
  **Rotate by:** 2027-09-23, the day it expires. To create or rotate it, pipe
  it straight into the secret so it never prints:
  ```bash
  fly tokens create readonly -o personal -n ops-check -x 8760h | gh secret set FLY_API_TOKEN
  ```
  `-o` names the organization so flyctl does not prompt mid-pipe. If the first run below
  reports the token rejected (exit 2), stdout carried more than the token: run `gh secret
  set FLY_API_TOKEN` on its own and paste the token at its prompt.
  Then prove it can read what the cron needs, and run the watchdog at once rather than
  waiting for the schedule (scheduled workflows only fire from the default branch):
  ```bash
  gh workflow run ops-check.yml
  gh run list --workflow=ops-check.yml --limit 1
  gh workflow run ops-check.yml -f self_test=true
  ```
  The first run must be green, and its `[9] restore-point` line must report a WAL backup
  (`newest WAL backup …` or `WAL backups disabled`) with no `also:` part. Check 9 passes on a
  recent volume snapshot alone and reports a refused `fly pg backup list` only as `also: …`,
  so a green run by itself does not prove that read. With that, `[9]` and `[5] origin-lock`
  prove the token can run `fly volumes snapshots list`, `fly pg backup list` and
  `fly ips list`; the
  self-test run must fail, and its run page's error annotations must name `[jobs] jobs-fresh`
  and read `exit 1 production:` (`gh run view <run id>` lists them). GitHub's failure email
  carries the run's status, never the log, and its docs do not say whether it includes
  annotations: record in the execution log whether the email showed those two annotations or
  only "Process completed with exit code 1", since that is what a real alert will look like. If a read is refused, the token lacks a scope: do not replace it with
  a deploy-capable token; drop the cron to its credential-free checks instead.
- `CLOUDFLARE_API_TOKEN`: local shell only, read-only, used by `infra/cloudflare-drift.py`.
  Zone `mealy.dev` scopes: Zone WAF Read, Transform Rules Read, Zone Settings Read, Bot
  Management Read. Account scope: Access: Apps and Policies Read.

```
  PRE:  CI green ── doc-guard ── migration listed w/ reversibility ── ops-check recent
         │
  1.  fly deploy ──▶ release_command: alembic upgrade head
         │              └── fails ──▶ previous image keeps serving ──▶ STOP, forward-fix
  2.  fly status: every process group started, rollout complete
  3.  Vercel: promote the staged build whose SHA is the release commit (never before step 2)
  4.  infra/release-smoke.py  (all groups)
         │
         ├── exit 0 ──▶ Cloudflare + manual checks ──▶ tag release ──▶ log execution row ──▶ DONE
         ├── exit 2 ──▶ tooling broken, not production ──▶ fix the laptop, re-run
         └── exit 1 ──▶ ROLLBACK
                          │
                          1. Vercel: promote previous  ◄── frontend FIRST
                          2. still broken? fly deploy --image <prev> --skip-release-command
                             (code only, NOT schema; from the previous commit's checkout)
                          3. migration already applied? forward-fix is the default;
                             alembic downgrade only if the listing below says reversible;
                             restore from backup only if both are unsafe
```

Every `fly` command needs `-a <app>` or must run from `backend/`. The repo root has no
`fly.toml`.

---

## 0. Before you start

- [ ] **Vercel is not auto-promoting, and builds see their commit. Set both before the release
      pull request merges:** the merge is what makes Vercel build. Settings → Environments →
      Production → Branch Tracking: "Auto-assign Custom Production Domains" is **off**, and
      Settings → Environment Variables: "Automatically expose System Environment Variables"
      is **on**. Merged with the first still on, the new frontend goes live ahead of the
      backend. Merged with the second off, the build is stamped with an empty commit and
      smoke check 8 fails. Both settings persist, so after the first release this is a
      confirmation. If the first setting is unavailable, use §4 instead of step 2.4 below.
- [ ] Tools: `fly version` ≥ v0.4.102, `gh auth status` ok, `python3 --version` ≥ 3.11,
      `curl`. The Vercel CLI is optional. Its local token has expired before, so run
      `vercel login` first if you use it.
- [ ] Check out the release commit and name it. Every command below reads `$RELEASE`:
      ```bash
      git checkout master && git pull
      RELEASE=$(git rev-parse HEAD); echo "$RELEASE"
      test -z "$(git status --porcelain)" && echo clean || echo "NOT CLEAN: stop"
      ```
      It must print `clean`. `fly deploy` uploads the working tree as it stands, uncommitted
      and untracked files included, while `/healthz` reports whatever `$RELEASE` says, so a
      dirty checkout ships unreviewed code that check 8 then passes as the release. Deploy from
      a clean checkout (a fresh `git worktree add` of `master` if this one holds other work).
- [ ] **Tell the household before it feels the release.** Pick a quiet hour. At `web=1` the
      single web machine is replaced in place, and a save made during that window fails with
      an error toast (the change is reverted, not lost silently). If someone is using the
      app, say so first.
- [ ] Machine counts are set outside the deploy, with `fly scale count`, and pinned in
      [`fly-scale.json`](./fly-scale.json) (`web=1`, `worker=1`, `beat=1`). A deploy does not
      change them. Do not re-scale unless smoke check 3 fails. **First execution only (M8
      PR1a):** production still runs the platform default `web=2`. Scale it now, before §2,
      so check 3 passes and the downtime you log is `web=1`'s, not a rolling deploy's:
      ```bash
      fly scale count web=1 -a mealy-app-prod
      ```

## 1. Pre-release gates

Stop at the first gate that fails.

- [ ] **CI is green on the release commit.** A squash merge creates a new commit on
      `master`, and `test.yml` runs again on that push:
      ```bash
      gh run list --commit "$RELEASE" --json databaseId,workflowName,status,conclusion
      ```
      Expected: `Tests` `completed` / `success`. `cancelled` means a later push to `master`
      superseded the run (the workflow cancels in-progress runs per ref): rerun it with
      `gh run rerun <databaseId>` and wait for `success`.
- [ ] **doc-guard passed on the pull request.** It runs on pull requests only:
      ```bash
      gh pr checks <pr-number>
      ```
      Expected: `doc-guard` pass.
- [ ] **The most recent `ops-check` run is green and under 48 h old**, if the workflow has
      ever run:
      ```bash
      gh run list --workflow=ops-check.yml --branch master --limit 1 --json conclusion,createdAt
      ```
      If `gh` reports that no workflow is named `ops-check.yml`, record
      `n/a — workflow not yet on default branch` in the log and continue. That is the state
      until PR1b merges. Once it has run, a red or older run blocks the release: open it,
      read which check failed, and fix that first. The release is what watches the watcher.
- [ ] **List the migrations this release applies, each with its reversibility.** The exact
      list is production's current revision up to the release's head. Production first; this
      prints a revision id and no connection string:
      ```bash
      fly ssh console -a mealy-app-prod -g web -C "sh -c 'cd /app && /app/.venv/bin/alembic current'"
      ```
      Then locally, through Docker Compose (a subshell, so your shell stays at the repo root):
      ```bash
      (cd backend && docker-compose exec api alembic history -r <prod-revision>:head)
      ```
      The oldest line printed is production's current revision, which is already applied:
      leave it out. Write one line per remaining revision into the execution log: its id, whether `downgrade()` is
      written **and tested** (the `migration-upgrade` CI job tests the newest revision's
      down/up), and otherwise "forward-fix only". No revisions means the log says `none`.
- [ ] **Does any revision require quiescing writers?** Read each revision's docstring. A
      header that says to stop the Celery worker and beat (as `a1b2c3d4e5f1_item_model_expand`
      does: ACCESS EXCLUSIVE locks) is binding, not advice. If one does, run §3 instead of
      §2's plain deploy.
- [ ] **A restore point exists** before any release that carries a migration:
      ```bash
      python3 infra/release-smoke.py --only=recoverability
      ```
      Expected: `exit 0`. If it fails, see
      [incident-diagnostics.md → No recent restore point](./incident-diagnostics.md#no-recent-restore-point).
- [ ] **The merge build is Staged, not live.** Deployments: the `master` row whose commit is
      `${RELEASE:0:7}` reads Staged (or is still building). If it is already Current, §0's
      Vercel settings were not set before the merge; the frontend is ahead of the backend,
      so deploy the backend now and continue.

## 2. Deploy: backend first, then frontend

1. **Measure the downtime.** In a second terminal, start this and leave it running until
   step 3 finishes. The log records the observed number, because "brief" is not a number:
   ```bash
   while :; do printf '%s %s\n' "$(date -u +%T)" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 https://api.mealy.dev/healthz)"; sleep 1; done
   ```
   Afterwards, count the seconds that were not `200`.
2. **Deploy the backend** from `backend/`, so `fly.toml` and the Dockerfile are picked up.
   The build argument puts the commit into `/healthz` (from PR1b on; before that the image
   ignores it harmlessly):
   ```bash
   (cd backend && fly deploy -a mealy-app-prod --build-arg GIT_COMMIT="$RELEASE")
   ```
   The subshell keeps your shell at the repo root, where step 5 runs the smoke script.
   `release_command` runs `alembic upgrade head` against the new image before web takes
   traffic. **If it fails**, the previous image keeps serving: stop here and follow
   [incident-diagnostics.md → Migration failure mid-release](./incident-diagnostics.md#migration-failure-mid-release).
   Do not roll back. Nothing was released.
3. **Every process group is started.** A deploy updates an already-stopped machine without
   starting it, which is how the worker stayed dead for 103 days:
   ```bash
   fly status -a mealy-app-prod
   ```
   Expected: every `web`, `worker` and `beat` machine `started`, and every one on the new
   version. Smoke check 2 asserts this again from JSON.
4. **Promote the frontend.** Vercel built the merge and left it **Staged**. Promote the
   staged deployment **whose commit SHA equals `$RELEASE`** (`echo ${RELEASE:0:7}`), and
   only once it is **Ready**. Never "the latest staged": that can be an older leftover, or
   a build still running. Dashboard: Deployments → the `master` row with that commit and
   status Ready → ⋯ → **Promote**. Domains move instantly, with no rebuild. Or from the
   CLI (after `vercel login`), taking the deployment's URL from the record Vercel writes to
   GitHub for that commit:
   ```bash
   URL=$(gh api "repos/willdoucet/todo-app/deployments/$(gh api "repos/willdoucet/todo-app/deployments?sha=$RELEASE" -q '.[0].id')/statuses" -q '.[0].environment_url'); echo "$URL"
   vercel inspect "$URL" --scope willdoucets-projects     # status must read Ready
   vercel promote "$URL" --scope willdoucets-projects --yes
   ```
   A promotion you forget leaves production on the previous bundle. Smoke check 8 catches
   that whenever the release changed `frontend/`: it compares the deployed build's
   `frontend/` with the release's. If Vercel made no deployment for `$RELEASE` (a build
   skipped because `frontend/` did not change), there is nothing to promote: skip this
   step, and check 8 passes on the previous build.
5. **Run the smoke script** from the repo root, on the host:
   ```bash
   python3 infra/release-smoke.py --release-commit="$RELEASE"
   ```
   First execution only (PR1a, before PR1b's `/healthz` fields exist), use the skip list.
   Skipped assertions print `skipped`, never `pass`, and check 1 still runs:
   ```bash
   python3 infra/release-smoke.py --only=release,liveness,recoverability,edge \
     --skip=healthz_jobs,healthz_version,healthz_gate_break_glass --release-commit="$RELEASE"
   ```
   - `exit 0`: continue.
   - `exit 2 tooling:`: the laptop is the problem (flyctl missing, token expired, no
     network, a Cloudflare challenge page). Production is untouched. Fix it and re-run.
   - `exit 1 production:`: each failed line links its diagnostics entry. Check whether it is
     a rollback trigger (§5).

   Two checks can fail transiently. Check 4 (`worker round-trip unverified`) can fail when
   a busy queue or a Postgres primary that is waking up delays `health_check` past 30 s.
   Check 5 (`rate-limited, unverified`) can fail on a 429. For either, wait, look at the
   worker log or the WAF window, and retry once before treating it as a broken release.

   **A declared pause.** When `infra/paused.json` declares the worker or beat paused (it does
   from 2026-09-23 until the Upstash cap is addressed, TODOS.md P1), check 2 expects those
   groups **stopped**, and check 4 and `[jobs] jobs-fresh` print `PAUSE`, never `PASS`. The
   run exits 0 and its summary counts them (`… 2 paused (beat, worker declared in
   infra/paused.json)`). A paused group that is running, a job that succeeded on a later day
   than the worker's `since` (a resume nobody declared), or a pause past its `review_by`
   date, fails. See [incident-diagnostics.md → A deliberate pause](./incident-diagnostics.md#a-deliberate-pause-worker-or-beat).

   To prove the exit plumbing without touching production (no command reaches it):
   ```bash
   python3 infra/release-smoke.py --self-test
   ```
   Expected: `exit 1 production: [3] scale-reconciled (self-test: …)`.
6. **Cloudflare dashboard.** Do this every release, whether or not you ran the drift script.
   The script narrows where to look; it does not replace looking. Zone `mealy.dev`:
   - [ ] Security → WAF → Rate limiting rules: **Mealy api-auth burst limit** is active,
         5 requests / 10 seconds / IP, Block 10 s.
   - [ ] Rules → Overview: **Mealy origin lock** (Request Header Transform Rule) is
         **Deployed**. Presence only. Do not open the rule's value or copy it anywhere.
   - [ ] Caching → Configuration → Browser Cache TTL: **Respect Existing Headers**.

   Optional, with a read-only token exported in this shell:
   ```bash
   python3 infra/cloudflare-drift.py
   ```
   Expected: `exit 0: no drift`. Any drift: fix the dashboard, or update
   `cloudflare-state.md` in the same commit that records a deliberate change.
7. **Manual checks no script can do.** Each lists the signal it looks for:
   - [ ] **Same-site cookie on an image.** Log in at `https://mealy.dev`, open DevTools →
         Network, and click an image request to `api.mealy.dev/uploads/…`. The Cookies tab
         shows `__Host-refresh`. The response has `cache-control: private, no-cache`,
         unmodified (any `max-age` means Cloudflare rewrote it), and `cf-cache-status` is
         not `HIT`. This is the logged-in half of smoke check 6, which can only test the
         no-cookie 401.
   - [ ] **An upload reaches R2 and reads back.** Upload a throwaway image (for example a
         family member photo), reload, and confirm it displays; then put the old one back.
         A rotated R2 credential passes boot and fails only on a write, so no read check
         catches it. On the first M8 release, also write the boto3 version pinned in
         `backend/uv.lock` into the log row: that closes TODOS.md → "Confirm boto3 default
         checksums against R2 at the first M8 release", whose entry says what to change if
         the upload fails.
   - [ ] **Stale tab.** Open a tab on `https://mealy.dev/mealboard` *before* step 2 and leave
         it open through the deploy. After the promotion, use it. Navigating works, or a
         failed action shows an error and a full reload recovers.
   - [ ] **Chunk load.** In that same old tab, open a page you had not visited (for example
         Recipes). The old build asks for a JS chunk that no longer exists, and it does not
         get a 404: `vercel.json`'s catch-all rewrite answers with the app's HTML, marked
         cacheable for a year, so the chunk fails to load. One full reload must recover
         cleanly, on this real route and not only on `/index.html`. That HTML now sits in
         Cloudflare's cache under the old chunk's name, which is why §5.1 purges the cache
         (TODOS.md → "A missing `/assets/*` chunk is answered with a year-cached HTML page").
8. **Tag the release.** The scheme is `v1-<UTC date>-<short sha>`, so releases are
   greppable in `git tag`:
   ```bash
   TAG="v1-$(date -u +%Y%m%d)-$(git rev-parse --short=7 "$RELEASE")"
   git tag -a "$TAG" -m "Release $TAG" "$RELEASE" && git push origin "$TAG"
   ```
9. **Stop the downtime loop, and log the release** in the table at the bottom: date, you,
   the tag, the migration lines from §1, the outcome, the observed downtime in seconds, and
   anything the procedure got wrong. Fix the procedure in the same pull request as the
   row.

## 3. Deploying a migration that requires quiescing writers

Use this only when §1 found a revision whose docstring says to stop the worker and beat.

1. Find the `worker` and `beat` machine ids:
   ```bash
   fly machines list -a mealy-app-prod
   ```
2. Stop them, then confirm both read `stopped` before going on. They carry
   `[[restart]] policy = "always"`, so do not assume the stop held:
   ```bash
   fly machine stop <worker-id> <beat-id> -a mealy-app-prod
   fly machines list -a mealy-app-prod
   ```
3. Deploy (§2 step 2). They stay stopped, because a deploy leaves a stopped machine
   stopped. Here that is useful.
4. Once `release_command` has succeeded and web is healthy, start them again:
   ```bash
   fly machine start <worker-id> <beat-id> -a mealy-app-prod
   ```
5. Continue at §2 step 3. The "every process group started" check is what proves you did
   not leave them down.

## 4. When Vercel auto-promotion cannot be turned off

The backend must never trail the frontend by more than one `fly deploy`.

- **Release with no migration:** deploy Fly *before* merging, from the pull request's
  checkout (`(cd backend && fly deploy -a mealy-app-prod --build-arg GIT_COMMIT=$(git rev-parse HEAD))`;
  the repo root has no `fly.toml` or Dockerfile), then merge. Migrations must be backward-compatible anyway, and there are none here.
- **Release with a migration:** **never deploy before merging.** `release_command` would
  apply an unmerged branch's revision to production. If that pull request is then revised or
  abandoned, production's `alembic_version` points at a revision that does not exist on
  `master`, and the next deploy cannot resolve its path. Merge first, then deploy Fly
  **immediately**, before touching anything else. The frontend lags by the length of one
  `fly deploy`.
- Smoke check 8 compares each tier's code (`frontend/`, `backend/`) between the deployed
  commit and the release, not commit ancestry. A squash merge never makes the pull
  request's head an ancestor of `master`, but its `backend/` is the one that merged, so the
  deploy-before-merge path passes.

## 5. Rollback

**Triggers.** Roll back when the release caused one of these:

- a user-visible regression;
- smoke `exit 1` on something this release changed, and it does not clear on a retry (a
  transient 429 or a round-trip timeout is not a trigger by itself);
- the host gate rejecting real traffic (check 5 returning 421 through Cloudflare).

`release_command` failing is **not** a rollback: the previous image never stopped serving.

**"Rollback" never means the database goes backward.** There are two doctrines.

### 5.1 Frontend first: promote the previous build, then purge the edge cache

In Vercel, promote the previous production deployment: the one whose commit is the
previous release tag's SHA (`git rev-list -n 1 <previous-tag>`). Deployments → that row →
⋯ → **Promote**, or `vercel promote <its URL>` as in §2 step 4. **Promote**, not Instant
Rollback: Promote works on a build that was Current before (observed 2026-09-23), while on
the Hobby plan Instant Rollback reaches only the production deployment just before the
current one and refuses anything older with `402 … upgrade to pro`. One stray promotion (a
merge that went Current, as #60's did) puts the previous release out of its reach.

Then, before re-testing: Cloudflare, zone `mealy.dev` → Caching → Configuration →
**Purge Everything**, and do an empty-cache reload in every browser that opened the old
build after the release (§2 step 7's chunk-load check does). While the release was live, a
request for one of the previous build's chunks got the app's HTML, cached for a year under
that chunk's name. The previous build asks for exactly those names, so without the purge
the rolled-back app fails to load them. Re-test. Many releases need nothing more.

### 5.2 Backend: roll back the code, never the schema

`fly releases rollback` does not exist (flyctl v0.4.102 has only the `fly releases`
listing). The rollback is a deploy of the previous image:

1. Read the previous successful release's image reference:
   ```bash
   fly releases --image -a mealy-app-prod
   ```
2. Check out **the commit being rolled back to**. `fly deploy --image` re-applies the
   *current checkout's* `fly.toml [env]`. From the new checkout it would pair old code with
   new `[env]` values, which is the `STORAGE_BACKEND` trap in `r2-cutover-runbook.md`:
   ```bash
   git checkout <previous-release-tag>
   ```
   The tag is what makes this exact. Its checkout's `fly.toml [env]` is the one the tagged
   image ran with, so read `git log --oneline -3 -- backend/fly.toml` only when a
   `backend/fly.toml` change merged between that tag and a deploy.
3. Deploy that image **without the release command**:
   ```bash
   (cd backend && fly deploy -a mealy-app-prod --image <image-ref> --skip-release-command)
   ```
   `--skip-release-command` is **required** across a migration boundary and harmless
   otherwise. The previous image's Alembic tree cannot find the newer revision now stored in
   `alembic_version`, so its `alembic upgrade head` fails with "Can't locate revision"
   and the deploy aborts on exactly the case it exists for.
4. Smoke the rolled-back state from the release checkout, not the previous one: the
   previous commit may not carry the script (M8 PR1a's parent does not), and an older copy
   checks less. The previous image may lack `/healthz` fields, so skip only what it lacks:
   ```bash
   git checkout master
   python3 infra/release-smoke.py --only=liveness,edge --skip=healthz_jobs,healthz_gate_break_glass
   ```
   A pre-PR1b image (PR1a's) lacks all three `/healthz` fields, so rolling back to one skips
   `healthz_version` too: `--skip=healthz_jobs,healthz_version,healthz_gate_break_glass`.
   While the rolled-back image lacks `jobs`, the daily `ops-check` fails naming the missing
   key. That is a correct signal. Roll forward soon, or disable the workflow for the
   duration. Never teach the script to pass on a missing key.
5. **Roll forward** when the fix is merged: back to `master`, and §2 again. To roll the
   frontend forward to a deployment that was already promoted (a false alarm, or a dry-run),
   **Promote** it again (§5.1), then Purge Everything once more: while the previous bundle
   was live, a request for one of the release's chunk names was answered with HTML and
   cached under that name.

### 5.3 A migration has already landed

- **Forward-fix is the default.** Write a new revision that repairs it.
- `alembic downgrade` only for a revision that §1's listing recorded as downgrade written
  **and tested**.
- Restore from backup only when both are unsafe. That is not a rollback, it is
  [incident-diagnostics.md → A real restore into production](./incident-diagnostics.md#a-real-restore-into-production):
  stop the worker first, or the abandoned-upload sweep can delete live media.

## 6. Rotate the household password

The operator CLI (M8 item 6). It sets a new password and signs **every** household session
out in one transaction: every open tab lands on the sign-in page on its next request, and an
unsaved form is lost.

1. **Tell the household first,** and give them the new password. The one exception is a
   rotation because the password leaked: then rotate first, and tell them after.
2. Open a shell on a **web** machine. Use `--select`, not `-C "..."`: the password prompt
   needs a TTY, which `-C` does not reliably allocate. Choose a `web` machine; the worker and
   beat run no API code, and may be paused:
   ```bash
   fly ssh console -a mealy-app-prod --select
   ```
3. In that shell, run the CLI with the interpreter spelled out. The prod image's `PATH` entry
   is relative (`.venv/bin`), so a bare `python` outside `/app` is the system one:
   ```bash
   cd /app && /app/.venv/bin/python -m app.cli.rotate_password <household email>
   ```
   It prompts twice. Expected: `rotated: user 1; N refresh token(s) revoked; session version
   is now M`, then `all sessions revoked; the household must sign in with the new password`.
   Exit `1` means refused and nothing written (no such user, a mismatch, empty, or over 128
   characters, the most login accepts). Exit `2` means a database error or one nobody
   anticipated (named by its type only): the rotation may not have completed (the connection
   can drop around the commit), so try signing in with the new password before retrying.
4. Sign in at `https://mealy.dev` with the new password. A tab that was signed in shows the
   sign-in page with "Your session ended. Someone may have signed out on another device, or
   the household password changed."

---

## Execution log

| Date (UTC) | Operator | Release | Migrations (id · reversibility) | Outcome | Deploy downtime (s) | Notes |
|---|---|---|---|---|---|---|
| 2026-09-23 | willdoucet (run by Claude Code) | `v1-20260923-f0a8d81`: Fly v34, rolled back to v33's image as v35, forward as v36; Vercel `dpl_Gzqsu1SKbRJnVCKGWQKMLUj3uZUD` | none (production at `b7e2c9a4f1d8`, the head) | Pass. Smoke exit 0: 8 passed, 4 skipped (the PR1a list), 1 paused (worker and beat, declared). Cloudflare dashboard 3/3; drift `exit 0: no drift`; manual checks 4/4. Rollback dry-run: rolled-back smoke (liveness, edge) exit 0, 4 passed, 3 skipped; after the roll forward the same result as the release | ~4 each: release 19:50:08–19:50:12, rollback 20:13:45–20:13:49, roll forward 21:50:19–21:50:23 | **CI gate:** `visual-tests` on `f0a8d81` hit its 25-min timeout twice (a Playwright report-server hang after a flaky failure, fixed separately); the operator accepted equivalence: `frontend/`, `backend/`, `infra/`, `.github/` are identical to `91edffa`, green on all five jobs. **Vercel:** #60's merge build went Current at merge (the auto-assign toggle had not been saved), so PR1a's frontend led the backend ~3 h, harmlessly (a meta tag and the build command). **Smoke** ran from the PR1b branch's script, which reads `infra/paused.json`; master's copy fails checks 2 and 4 on the declared pause. `ops-check`: n/a, not yet on the default branch. **R2 upload** read back with boto3 1.43.90 (default checksums). **Procedure fixes (this row's pull request):** the previous release was `91edffa^` = `1087f30`, not `$RELEASE^`, because the release spanned two merges (#60, #61), so the tag, not `^`, names it from now on; Instant Rollback refused `1087f30`'s build (402, Hobby) while `vercel promote` worked both ways, so §5.1 and §5.2 now say Promote; the roll forward needs a second purge; §2 step 4 gained the CLI commands. The backup-restore drill is logged in its own file. |
