# R2 storage cutover runbook (M7 PR2)

Operator procedure for the one-way-ish moment when production stops storing user
uploads on ephemeral container disk and starts storing them in Cloudflare R2,
and `/uploads/*` stops being a public static mount.

Same purpose as [`cloudflare-state.md`](./cloudflare-state.md): keep operational
state and procedure in the repo rather than in someone's memory.

- **Plan:** `.agents/plans/features/prod-r2-storage/prod-r2-storage-plan-20260715-201232.md`
- **Milestone:** M7 of the `v1-productionization` epic
- **Status:** NOT YET EXECUTED — fill in the log at the bottom when you run it

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

- [ ] **OQ1 — live same-site check (BLOCKING, cannot be automated).**
      In a real browser against the Cloudflare-proxied production origin, log in
      at `https://mealy.dev` and confirm an `<img>` pointing at
      `https://api.mealy.dev/uploads/<key>` loads. This proves the
      `SameSite=Strict` `__Host-refresh` cookie transmits on a same-site
      subresource load. Same-site is confirmed on paper (`mealy.dev` and
      `api.mealy.dev` share eTLD+1), but the entire read path rests on it.
      If it fails, PR2 must not ship as designed.
- [ ] **CF edge does not cache private media.** With DevTools open, load a
      private image twice and confirm no `cf-cache-status: HIT` on
      `/uploads/*`. `Cache-Control: private, no-cache` should prevent it; a
      revalidation returning `304` is expected and correct.
- [ ] **`fly volumes list -a mealy-app-prod` is empty** (OQ3 residual). `fly.toml`
      has no `[mounts]` block, so `/app/uploads` should be ephemeral and there is
      nothing to migrate. A volume attached imperatively would not show in
      config — this is the definitive 30-second check.
- [ ] **The four `R2_*` secrets are present** (provisioned in M2, first real use
      here). Names only — never print values. Prefer Fly's own names-only view:
      `fly secrets list -a mealy-app-prod`
      If you need to confirm they reached the running machine, filter ON THE
      REMOTE SIDE so no value ever crosses the SSH pipe:
      `fly ssh console -a mealy-app-prod -C "sh -c 'env | grep \"^R2_\" | cut -d= -f1'"`
      ⚠️ Never run unfiltered `env` / `printenv`, and never pipe a remote `env`
      into a local `grep` — the non-matching lines have already crossed into
      your terminal and the transcript by then. See LESSONS.md, "Never run
      unfiltered `env` / `printenv`".
- [ ] **`fly secrets list -a mealy-app-prod` does NOT list `STORAGE_BACKEND`.**
      A Fly secret overrides `fly.toml [env]`. If one exists, the "rollback
      reverts the flip" argument below is void — remove it (`fly secrets unset
      STORAGE_BACKEND -a mealy-app-prod`) before deploying.
- [ ] **The browser receives `cache-control: private, no-cache` unmodified.**
      Cloudflare's *Caching → Configuration → Browser Cache TTL* rewrites the
      header unless set to "Respect Existing Headers"; a rewritten TTL would let
      a logged-out user on a shared device keep seeing cached photos. Check the
      response header in DevTools on a private image and record the dashboard
      setting in [`cloudflare-state.md`](./cloudflare-state.md).
- [ ] **Keep Cloudflare Access Application 1 UP** through cutover and smoke
      verification. It is the fallback while first-party auth is unproven.

> **Expected, not a regression: images do NOT load on Vercel preview
> deployments.** `vercel.app` is on the Public Suffix List, so every
> `*.vercel.app` preview origin is a *different site* from `api.mealy.dev` —
> the `SameSite=Strict` `__Host-refresh` cookie will not be sent on an `<img>`
> subresource load, and every image 401s. Production is unaffected
> (`mealy.dev` and `api.mealy.dev` share eTLD+1 `mealy.dev`). Verify OQ1 above
> against the **production** origin, never a preview URL. A preview served
> from a `mealy.dev` subdomain would exercise the real path — see TODOS.md.

## Cutover

- [ ] Record the cutover timestamp here: `________________`
- [ ] Deploy PR2 (code + the `STORAGE_BACKEND=r2` flip land in the SAME deploy —
      writes-to-R2 and reads-through-the-proxy must flip together, or an
      R2-written object would 404 against a disk-backed read).
- [ ] `GET /healthz` returns 200.
- [ ] **Smoke freeze:** do NOT create real household uploads until the checks
      below pass. Use one throwaway image you are willing to delete.

## Smoke verification

- [ ] Upload one throwaway image (any of the four types). It succeeds.
- [ ] That image renders in the app after a full page reload.
- [ ] The object exists in the R2 bucket (not on container disk).
- [ ] `curl -i https://api.mealy.dev/uploads/<that-key>` with **no cookie** →
      **401**. This is the security-critical check: no public static surface.
- [ ] A stock icon renders (responsibility or item icon picker).
- [ ] Log out, then reload a page with images → images fail to load (401).
- [ ] **Durability:** `fly apps restart mealy-app-prod`, then confirm the
      throwaway image still renders. This is what proves R2 rather than
      ephemeral disk — the property M7 exists to deliver.
- [ ] Delete the throwaway image's entity so no test data lingers.

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

- [ ] Tear down **Cloudflare Access Application 1**. This is M7's exit item:
      `/uploads/*` was the last thing that needed edge gating.
- [ ] Re-verify `api.mealy.dev` is protected by first-party auth alone:
      unauthenticated `/uploads/*` → 401, unauthenticated protected API → 401,
      `/healthz` → 200.
- [ ] Update [`cloudflare-state.md`](./cloudflare-state.md): move Application 1
      to a historical-record section with the removal rationale and date, the
      same way Application 2 was recorded on 2026-05-14.
- [ ] Confirm the abandoned-upload sweep runs against R2 (Celery beat, hourly;
      look for the `Abandoned-upload sweep` log line).

---

## Execution log

| Date | Operator | Outcome | Notes |
|---|---|---|---|
| | | | |
