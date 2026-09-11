# R2 storage cutover runbook (M7 PR2)

Operator procedure for the one-way-ish moment when production stops storing user
uploads on ephemeral container disk and starts storing them in Cloudflare R2,
and `/uploads/*` stops being a public static mount.

Same purpose as [`cloudflare-state.md`](./cloudflare-state.md): keep operational
state and procedure in the repo rather than in someone's memory.

- **Plan:** `.agents/plans/features/prod-r2-storage/prod-r2-storage-plan-20260715-201232.md`
- **Milestone:** M7 of the `v1-productionization` epic
- **Status:** EXECUTED 2026-09-11 — cutover at 10:49 PDT (17:49 UTC); Cloudflare
  Access Application 1 removed the same day. See the execution log at the bottom.

---

## What changes at cutover

| | Before PR2 | After PR2 |
|---|---|---|
| New upload bytes land in | ephemeral container disk `/app/uploads` | Cloudflare R2 bucket |
| `GET /uploads/*` served by | public `StaticFiles` mount | authenticated `GET /uploads/{key}` route |
| Who gates image reads | Cloudflare Access (edge) only | first-party `__Host-refresh` cookie |
| Stock icons read from | `/app/uploads/stock_icons` (never populated in prod — see note) | `/app/stock_icons_src` in the image |

> **Note — stock icons are currently BROKEN in production.** The
> `docker-compose` api entrypoint copies `stock_icons_src` into the uploads
> volume, but the Fly `[processes] web` command and the prod Dockerfile `CMD`
> do not. So `/uploads/stock_icons/*.png` 404s in prod today. PR2's compat
> branch reads them straight from the image, which **fixes** this. Expect stock
> icons to start working, not to regress.

---

## Pre-cutover gates

- [x] **OQ1 — live same-site check (BLOCKING, cannot be automated).**
      In a real browser against the Cloudflare-proxied production origin, log in
      at `https://mealy.dev`, open DevTools → Network, and confirm the
      `__Host-refresh` cookie is sent on an `<img>` request to
      `https://api.mealy.dev/uploads/<key>` (the request's Cookies tab). This
      proves the `SameSite=Strict` cookie transmits on a same-site subresource
      load. Same-site is confirmed on paper (`mealy.dev` and `api.mealy.dev`
      share eTLD+1), but the entire read path rests on it. If it fails, PR2
      must not ship as designed.
      Before PR2 is deployed, the old StaticFiles mount serves the image whether
      or not the cookie is sent, so "the image loads" proves nothing. The cookie
      on the request is the signal.
- [x] **`fly volumes list -a mealy-app-prod` is empty** (OQ3 residual). `fly.toml`
      has no `[mounts]` block, so `/app/uploads` should be ephemeral and there is
      nothing to migrate. A volume attached imperatively would not show in
      config — this is the definitive 30-second check.
- [x] **The four `R2_*` secrets are present** (provisioned in M2, first real use
      here). Names only — never print values. Prefer Fly's own names-only view:
      `fly secrets list -a mealy-app-prod`
      If you need to confirm they reached the running machine, filter ON THE
      REMOTE SIDE so no value ever crosses the SSH pipe:
      `fly ssh console -a mealy-app-prod -C "sh -c 'env | grep \"^R2_\" | cut -d= -f1'"`
      ⚠️ Never run unfiltered `env` / `printenv`, and never pipe a remote `env`
      into a local `grep` — the non-matching lines have already crossed into
      your terminal and the transcript by then. See LESSONS.md, "Never run
      unfiltered `env` / `printenv`".
- [x] **`fly secrets list -a mealy-app-prod` does NOT list `STORAGE_BACKEND`.**
      A Fly secret overrides `fly.toml [env]`. If one exists, the "rollback
      reverts the flip" argument below is void — remove it (`fly secrets unset
      STORAGE_BACKEND -a mealy-app-prod`) before deploying.
- [x] **Cloudflare's Browser Cache TTL is "Respect Existing Headers".**
      *Caching → Configuration → Browser Cache TTL* rewrites `Cache-Control`
      unless set to "Respect Existing Headers"; a rewritten TTL would let a
      logged-out user on a shared device keep seeing cached photos. Set it in
      the dashboard and record it in [`cloudflare-state.md`](./cloudflare-state.md).
      The header itself can only be checked after the deploy (Smoke
      verification): the pre-PR2 mount sends no `Cache-Control`, so there is
      nothing to inspect yet.
- [x] **Keep Cloudflare Access Application 1 UP** through cutover and smoke
      verification. It is the fallback while first-party auth is unproven.

> Every `fly` command needs `-a mealy-app-prod` or must run from `backend/`.
> The repo root has no `fly.toml`, and flyctl fails there with "the config for
> your app is missing an app name". Don't work around it by changing the `app`
> name in `fly.toml`: `mealy-app-prod` is the real app.

> **Expected, not a regression: images do NOT load on Vercel preview
> deployments.** `vercel.app` is on the Public Suffix List, so every
> `*.vercel.app` preview origin is a *different site* from `api.mealy.dev` —
> the `SameSite=Strict` `__Host-refresh` cookie will not be sent on an `<img>`
> subresource load, and every image 401s. Production is unaffected
> (`mealy.dev` and `api.mealy.dev` share eTLD+1 `mealy.dev`). Verify OQ1 above
> against the **production** origin, never a preview URL. A preview served
> from a `mealy.dev` subdomain would exercise the real path — see TODOS.md.

## Cutover

- [x] Record the cutover timestamp here: `2026-09-11 10:49 PDT (17:49 UTC)`
- [x] Deploy PR2 (code + the `STORAGE_BACKEND=r2` flip land in the SAME deploy —
      writes-to-R2 and reads-through-the-proxy must flip together, or an
      R2-written object would 404 against a disk-backed read). Deploy the
      merged `master`, from `backend/` so `fly.toml` and the Dockerfile are
      picked up: `git checkout master && git pull`, then
      `cd backend && fly deploy -a mealy-app-prod`.
- [x] `GET /healthz` returns 200. While Access Application 1 is up,
      `api.mealy.dev/healthz` returns Access's 302. Use the Fly hostname
      instead; the production host gate lets `/healthz` (and only `/healthz`)
      through on it: `curl -sS https://mealy-app-prod.fly.dev/healthz`.
- [ ] `fly scale show -a mealy-app-prod` lists exactly one `beat` machine (the
      `fly.toml` singleton invariant). Not recorded in the 2026-09-11 run.
- [x] **Smoke freeze:** do NOT create real household uploads until the checks
      below pass. Use one throwaway image you are willing to delete.

## Smoke verification

- [x] Upload one throwaway image (any of the four types). It succeeds.
- [x] That image renders in the app after a full page reload.
- [x] The object exists in the R2 bucket (not on container disk).
- [x] `curl -i https://api.mealy.dev/uploads/<that-key>` with **no cookie** →
      **401**. This is the security-critical check: no public static surface.
      While Access Application 1 is up, this returns Access's **302** instead:
      the edge answers before the app, so a 302 is neither a pass nor a fail.
      Before the teardown, the app-level proof is the log-out check below; this
      curl is repeated after the teardown (Post-cutover), where it must be 401.
- [x] A stock icon renders (responsibility or item icon picker).
- [x] Log out, then reload a page with images → images fail to load (401).
- [x] **The browser receives `cache-control: private, no-cache` unmodified.**
      DevTools → Network → a private image → Response Headers. Anything with
      `max-age` in it means Cloudflare's Browser Cache TTL rewrote the header
      (see the pre-cutover gate).
- [x] **CF edge does not cache private media.** Load a private image twice and
      confirm no `cf-cache-status: HIT` on `/uploads/*`. `BYPASS` is the
      expected value (Cloudflare saw `private, no-cache`); a revalidation
      returning `304` is also correct.
- [x] **Durability:** `fly apps restart mealy-app-prod`, then confirm the
      throwaway image still renders. This is what proves R2 rather than
      ephemeral disk — the property M7 exists to deliver.
- [x] Delete the throwaway image's entity so no test data lingers.

## If smoke verification fails

Prefer **forward-fix** over rollback. Rollback is not one-command reversible
(the remaining `[medium]` from the adversarial review).

Three windows:

1. **Before the PR2 deploy** — normal rollback is safe. Prod still writes to
   disk and CF Access is up.
2. **During the smoke window, before real household uploads** — either
   forward-fix, or redeploy PR1 and delete the throwaway DB reference and its
   R2 object. Cheap, because the only R2 object is the throwaway.
3. **After real R2 uploads exist** — forward-fix. If rollback is truly
   unavoidable: export the `assets` rows and R2 objects created since the
   cutover timestamp, restore compatible local files OR accept documented
   broken image references, and only then redeploy PR1.

> A code rollback only undoes the R2 flip if `STORAGE_BACKEND` is versioned
> with the code. If it were set as a Fly secret instead, redeploying PR1 would
> leave the flag set — and PR1 writes to R2 while reading from disk, which is
> broken. Keep the flip and the code in the same revision.

**The exact rollback command matters.** Only a deploy that reads PR1's
`fly.toml` reverts the flag:

```bash
# Correct — the whole tree, so fly.toml has no [env] block:
git checkout <pre-PR2 master commit>      # `git log --oneline master` — the commit before the PR2 squash
cd backend && fly deploy -a mealy-app-prod
```

Two commands that look like a rollback and are not:

- `fly deploy --image <PR1 image>` **from the PR2 checkout** re-applies PR2's
  `fly.toml [env]` → PR1 code with `STORAGE_BACKEND=r2`, the broken combination.
- `fly machine update --image <PR1 image>` keeps each machine's **existing** env
  → same result.

If you must roll back by image, add the flag explicitly:
`fly deploy -a mealy-app-prod --image <PR1 image> -e STORAGE_BACKEND=local`.

## Post-cutover (Ops, after PR2 is verified in prod)

- [x] Tear down **Cloudflare Access Application 1**. This is M7's exit item:
      `/uploads/*` was the last thing that needed edge gating.
- [x] Re-verify `api.mealy.dev` is protected by first-party auth alone:
      unauthenticated `/uploads/*` → 401, unauthenticated protected API → 401,
      `/healthz` → 200.
- [x] Update [`cloudflare-state.md`](./cloudflare-state.md): move Application 1
      to a historical-record section with the removal rationale and date, the
      same way Application 2 was recorded on 2026-05-14.
- [ ] Confirm the abandoned-upload sweep runs against R2 (Celery beat, hourly;
      the first run lands about an hour after a deploy or restart). Look for
      the worker's task-success line:
      `fly logs -a mealy-app-prod --no-tail | grep -i sweep_abandoned_uploads`
      → `Task app.tasks.sweep_abandoned_uploads[…] succeeded`. The
      `Abandoned-upload sweep: deleted N unreferenced assets` line only appears
      when there is something to reclaim (`sweep_abandoned_uploads` in
      `app/services/asset_lifecycle.py` returns early otherwise), so its
      absence proves nothing.

---

## Execution log

| Date | Operator | Outcome | Notes |
|---|---|---|---|
| 2026-09-11 | willdoucet | Pass | Cutover 10:49 PDT (17:49 UTC), PR #44 merged 10:48 PDT. Every pre-cutover gate and smoke check passed; private media arrived as `cache-control: private, no-cache` with `cf-cache-status: BYPASS`. Browser Cache TTL changed from 4 hours to "Respect Existing Headers" before the deploy. Access Application 1 removed the same day; post-teardown checks passed. Still open: the sweep success line and the `fly scale show` beat count. |
