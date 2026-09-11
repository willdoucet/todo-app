# Cloudflare State (mealy.dev / api.mealy.dev)

Canonical intent file for all Cloudflare dashboard state during M2-M7. The
dashboard config itself is not in git (real drift detection via API or
Terraform is M8 runbook scope, tracked in `.agents/docs/IMPLEMENTATION_PLAN.md`).
This file is the diff-able intent — update in the same commit that changes
the dashboard. Slice 7 manually reconciles file vs. live dashboard.

After M5 PR2 (2026-05-08), the `/plumbing-test*` backend endpoints are
gone. The Application 2 Bypass policy was **removed 2026-05-14** in
response to the cursor-implementation-review informational finding on
commit `a872136` (path-normalization variants — `/plumbing-test/`,
encoded dot segments, doubled slashes, backslashes — could theoretically
match the bypass selector at the edge while normalizing to a different
path at the FastAPI origin, sidestepping CF Access on a non-plumbing-test
request). Removing the vestigial bypass eliminates the concern entirely
since the underlying routes no longer exist. The CF Access edge gate
(Application 1) stays load-bearing for `/uploads/*` until M7 replaces
the StaticFiles mount with R2 + auth-proxied uploads (Cursor
implementation review constraint, 2026-05-07).

Last verified: 2026-05-01 by willdoucet
Cloudflare account ID: f7f2bff79b487f5d1552a1c5eebd3992
Zone: mealy.dev (zone ID: f188a6cea2ead74660b191d435cb370b)
Cloudflare Access team subdomain: mealyapp.cloudflareaccess.com

## DNS records (Cloudflare → mealy.dev zone)

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | @ (apex) | 4829274817842fa5.vercel-dns-017.com | Proxied (orange) — via CNAME flattening |
| CNAME | api | emldxj1.mealy-app-prod.fly.dev | Proxied (orange) |
| TXT | _fly-ownership.api | app-emldxj1 | n/a (TXT) |
| CNAME | _acme-challenge.api | api.mealy.dev.emldxj1.flydns.net | DNS only (gray) — Let's Encrypt validation |

Vercel auto-attached a `www.mealy.dev` redirect alias to the project; no
separate Cloudflare DNS record was added for it. If you ever want
`www.mealy.dev` to resolve, add a CNAME `www → cname.vercel-dns.com` (orange
cloud) — Vercel will 308 it back to the apex per the project's primary-domain
setting.

## Access — Application 1: Edge gate (full app)

Name: Mealy Edge Gate
Application domains:
  - mealy.dev (no path — matches all paths)
  - api.mealy.dev (no path — matches all paths)
Identity provider: One-Time PIN
Session duration: 24h
Policy: "Operator allowlist"
  - Action: Allow
  - Include → Emails: willdoucet@gmail.com

## Access — Application 2: Plumbing-test bypass (M2 → REMOVED 2026-05-14)

**Removed 2026-05-14** (operator action in CF dashboard). Historical
intent retained below for the M8 runbook drift-detection work.

### Historical record

Cloudflare Access doesn't support path-based bypass policies inside a
single Application — Policy "Include" selectors are identity-based only
(country, IP, common name, etc.). The mechanism for bypassing specific
paths is a SECOND self-hosted Application with the path-specific domains
and a Bypass policy. Cloudflare evaluates the more-specific path-bound
Application before the broader Edge gate Application.

Name: Bypass plumbing-test
Application domains:
  - api.mealy.dev / Path: plumbing-test
  - api.mealy.dev / Path: plumbing-test/read
Identity provider: irrelevant (Bypass action skips auth)
Policy: "Bypass plumbing-test"
  - Action: Bypass
  - Include → Selector: Everyone (fallback: IP ranges = 0.0.0.0/0 + ::/0)

Reason for bypass: cross-origin XHR from `mealy.dev` to
`api.mealy.dev/plumbing-test` cannot complete an OAuth-style Access
redirect. Slice 5's split-origin cookie verification depended on these two
paths reaching Fly directly.

### Removal rationale (2026-05-14)

The backend `/plumbing-test*` routes were deleted in M5 PR2 (commit
`e7032d3`, branch `prod-auth-enforcement-pr2`). The Bypass Application
was initially planned to stay live through M7 alongside the broader CF
Access teardown. The cursor-implementation-review on commit `a872136`
flagged an informational concern: path-normalization variants
(`/plumbing-test/`, encoded dot segments, doubled slashes, backslashes)
could theoretically match the bypass selector at the edge while
normalizing to a non-plumbing-test path at the FastAPI origin —
sidestepping CF Access on `/uploads/*`. Removing the vestigial bypass
now (rather than waiting for M7) eliminates the concern entirely with
zero cost since nothing depends on it.

## Caching — Browser Cache TTL

Setting (Caching → Configuration → Browser Cache TTL): **not yet recorded**.
Must be **"Respect Existing Headers"** — the M7 private-media route sends
`Cache-Control: private, no-cache` so the browser revalidates every image load
against the session cookie; any dashboard TTL would override that and let a
logged-out user on a shared device keep seeing cached photos. Verify in
DevTools and fill in during the M7 cutover (`r2-cutover-runbook.md`
pre-cutover gate).

## WAF — Rate limiting rules

Rule name: Mealy api-auth burst limit
Match: `(starts_with(http.request.uri.path, "/auth/"))`
Threshold: **5 requests / 10 seconds / IP**
Action: Block
Duration: 10 seconds
Status: active

**Deviation from plan body's "10 req / 1 min / IP" target:** Cloudflare free
tier caps rate-limit Period and Duration at 10 seconds and disallows the
`matches` regex operator + the `http.host` field for free-tier rate-limit
expressions. The hostname constraint is omitted because no other subdomain
on `mealy.dev` serves `/auth/*` paths (Vercel returns 404 for any such
request on `mealy.dev` itself), so the path-only filter is functionally
equivalent for our threat model. The 5-per-10-seconds threshold is
strictly stricter than the plan's 10-per-minute target on the leading
burst (5 in 10s vs 10 in 60s) and only modestly more permissive over a
full minute window if a brute-forcer rebursts after each 10-second block
clears (~30/min worst case). The app has **no app-layer rate limiting** — M3
shipped without the middleware once planned here, so this edge rule is the
only control (the argon2 dummy-hash note in `app/auth/passwords.py` records
the resulting DoS-amplification exposure). It only governs traffic that passes
through this zone — see *Transform Rules — origin lock* below for what stops
callers going around it. Verified working 2026-05-01 via
`slice6-rate-limit-burst-test.sh`
(first 5 of 10 returned 404 from Fly origin, last 5 returned 429 from
Cloudflare).

Revisit if upgrading to Cloudflare Pro/Business — at that point, swap
expression to the original `(http.request.uri.path matches "^/auth/") and
(http.host eq "api.mealy.dev")` with 10-req/1-min/1-min-duration semantics.

## Transform Rules — origin lock (Modify Request Header)

Status: **PENDING — not yet created.** The operator creates it in step 2 of the
rollout below; change this line to `active (YYYY-MM-DD)` when it is live.

Rule name: Mealy origin lock
Match: custom filter expression `(http.host eq "api.mealy.dev")`
Then: Modify request header → **Set static**
  - Header name: `X-Origin-Verify`
  - Value: the `ORIGIN_VERIFY_SECRET` Fly secret. **Never written in this file,
    in git, or in a chat transcript.**

Why: the Fly origin accepted connections that skip Cloudflare. Fly holds its
own certificate for `api.mealy.dev` (the `_acme-challenge.api` record above), so
`curl --resolve api.mealy.dev:443:<fly-ip> https://api.mealy.dev/...` reached the
app with the right `Host` header and never touched this zone: no WAF rate limit
on `/auth/*`, and no Transform Rule. `production_host_gate`
(`backend/app/main.py`) now also requires this header to match
`ORIGIN_VERIFY_SECRET` (constant-time compare) and returns 421 otherwise;
`/healthz` stays exempt for Fly's checks. Found 2026-09-11 during the M7 cutover
smoke checks.

Why a secret header and not an allowlist of Cloudflare's IP ranges: every
Cloudflare customer's traffic leaves from those ranges, so another tenant can
reach our origin from a Cloudflare IP through their own zone with their WAF
off. They cannot know this value. Authenticated Origin Pulls (mTLS) is not an
option because Fly's proxy terminates TLS before the app sees the connection.

"Set static" overwrites any `X-Origin-Verify` a client sends, so the header
cannot be injected through the zone. Cloudflare reserves header names starting
`cf-` and `x-cf-`; do not rename it to one.

### Rollout

Order matters: deploying the code before the rule exists locks the household
out. Steps 1–3 are harmless on the current release (it ignores the header), so
they can be done before the pull request merges.

1. Generate the secret straight to the clipboard; it is never printed:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32), end='')" | pbcopy
   ```
2. Dashboard → Rules → Transform Rules → Modify Request Header: create the rule
   above, paste the value, deploy it.
3. Store the same value as a Fly secret (this restarts the machines on the
   current image). Pipe it through stdin so the value never lands in the `fly`
   process's arguments (visible in `ps`); then clear the clipboard:
   ```bash
   pbpaste | sed 's/^/ORIGIN_VERIFY_SECRET=/' | fly secrets import -a mealy-app-prod
   ```
   ```bash
   pbcopy < /dev/null
   ```
   Clipboard-history tools and Universal Clipboard can retain the value; exclude
   it there too.
4. Confirm the secret reached Fly BEFORE deploying — names only, never values:
   ```bash
   fly secrets list -a mealy-app-prod | grep ORIGIN_VERIFY_SECRET
   ```
   Then deploy the code. In production the app refuses to boot without an
   `ORIGIN_VERIFY_SECRET` of at least 32 characters: if step 3 was skipped the
   new machine's lifespan raises and the deploy fails its health check rather
   than serving on a bad secret. On the single web machine that means a
   crash-loop until the secret is set, so do not skip the presence check above.
5. Verify from outside, never by hammering `/auth/login`:
   - Straight to the origin is rejected (expect `HTTP/2 421`):
     ```bash
     curl -si --resolve api.mealy.dev:443:66.241.124.153 https://api.mealy.dev/uploads/x | head -1
     ```
   - Through Cloudflare still reaches the app (expect `401` and
     `{"detail":"unauthorized"}`):
     ```bash
     curl -si https://api.mealy.dev/uploads/x
     ```
   - `https://api.mealy.dev/healthz` returns 200, and you can log in at
     `https://mealy.dev`.
   - The `/healthz` exemption cannot be spoofed via the Host header (expect
     `421`), aimed at a real route:
     ```bash
     curl -si --resolve api.mealy.dev:443:66.241.124.153 -H 'Host: api.mealy.dev/healthz?' https://api.mealy.dev/ | head -1
     ```

   Then set this section's Status line to active.

If real traffic gets 421 after step 4, the dashboard value and the Fly secret
differ. Neither can be read back, so repeat steps 1–3 with a fresh value. The
alternative is redeploying the previous image, which is safe for this change
because it does not touch `fly.toml`.

### Rotation

Repeat rollout steps 1–3 with a new value, running the `fly secrets set`
immediately after saving the dashboard rule. Between the two, requests carry the
new value while the app still expects the old one, so expect a short burst of
421s. There is one web machine and `fly secrets set` restarts it anyway, so
accepting two values during a rotation would not remove the gap.
