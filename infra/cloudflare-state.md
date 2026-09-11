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
(Application 1) stayed load-bearing for `/uploads/*` until M7 replaced
the StaticFiles mount with R2 + auth-proxied uploads (Cursor
implementation review constraint, 2026-05-07). It was **removed
2026-09-11** after the M7 cutover smoke checks. No Access applications
remain: `api.mealy.dev` is protected by first-party auth alone.

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

## Access — Application 1: Edge gate (M2 → REMOVED 2026-09-11)

**Removed 2026-09-11** (operator action in the Zero Trust dashboard), after the
M7 R2 cutover smoke checks passed — M7's exit item. Historical intent retained
below for the M8 runbook drift-detection work.

### Historical record

Name: Mealy Edge Gate
Application domains:
  - mealy.dev (no path — matches all paths)
  - api.mealy.dev (no path — matches all paths)
Identity provider: One-Time PIN
Session duration: 24h
Policy: "Operator allowlist"
  - Action: Allow
  - Include → Emails: willdoucet@gmail.com

### Removal rationale (2026-09-11)

From M5 on, the only surface first-party auth could not gate was the
`/uploads/*` StaticFiles mount (a `Mount` is not an `APIRoute`, so the
`protected` router's dependency never ran). M7 PR2 (#44) replaced it with the
cookie-authenticated `GET /uploads/{key}` route, leaving the gate nothing to
protect. Keeping it also had a cost. Access issues a separate session cookie
per hostname and a cross-origin XHR cannot complete its login redirect, so
whenever the 24h `api.mealy.dev` session lapsed, the SPA's `/auth/status` call
followed a 302 to `mealyapp.cloudflareaccess.com` and failed as a CORS error —
the operator could not log in (2026-09-11). The allowlist also admitted only
the operator's email, so no other household member could use the app.

Verified after removal, with no cookie, through Cloudflare: `/uploads/<key>` →
401, `/tasks/` → 401, `/healthz` → 200, and `/auth/status` with
`Origin: https://mealy.dev` → 200 with `access-control-allow-origin:
https://mealy.dev`. Execution log: [`r2-cutover-runbook.md`](./r2-cutover-runbook.md).

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

Setting (Caching → Configuration → Browser Cache TTL): **Respect Existing
Headers** — changed from the 4-hour default on 2026-09-11 by willdoucet, before
the M7 cutover.
Must stay **"Respect Existing Headers"** — the M7 private-media route sends
`Cache-Control: private, no-cache` so the browser revalidates every image load
against the session cookie; any dashboard TTL would override that and let a
logged-out user on a shared device keep seeing cached photos. Verified in
DevTools after the cutover (2026-09-11): a private image arrives with
`cache-control: private, no-cache` unmodified and `cf-cache-status: BYPASS`.

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
the resulting DoS-amplification exposure). Verified working 2026-05-01 via
`slice6-rate-limit-burst-test.sh`
(first 5 of 10 returned 404 from Fly origin, last 5 returned 429 from
Cloudflare).

Revisit if upgrading to Cloudflare Pro/Business — at that point, swap
expression to the original `(http.request.uri.path matches "^/auth/") and
(http.host eq "api.mealy.dev")` with 10-req/1-min/1-min-duration semantics.
