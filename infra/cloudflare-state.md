# Cloudflare State (mealy.dev / api.mealy.dev)

Canonical intent file for all Cloudflare dashboard state during M2-M5. The
dashboard config itself is not in git (real drift detection via API or
Terraform is M8 runbook scope, tracked in `.claude/IMPLEMENTATION_PLAN.md`).
This file is the diff-able intent — update in the same commit that changes
the dashboard. Slice 7 manually reconciles file vs. live dashboard.

The bypass-application section is removed in M5 PR #2 when the
`/plumbing-test*` endpoints come down. Rest of file persists past M2 and
feeds into the M8 runbook drift-detection work.

Last verified: 2026-05-01 by willdoucet
Cloudflare account ID: <TODO — Cloudflare dashboard right sidebar (32-char hex)>
Zone: mealy.dev (zone ID: <TODO — Cloudflare zone overview right sidebar (32-char hex)>)
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

Name: <TODO — name as configured (runbook suggested "Mealy M2-M5 Edge Gate")>
Application domains:
  - mealy.dev (no path — matches all paths)
  - api.mealy.dev (no path — matches all paths)
Identity provider: One-Time PIN
Session duration: 24h
Policy: "Operator allowlist"
  - Action: Allow
  - Include → Emails: willdoucet@gmail.com

## Access — Application 2: Plumbing-test bypass (M2-M5 only; removed in M5 PR #2)

Cloudflare Access doesn't support path-based bypass policies inside a
single Application — Policy "Include" selectors are identity-based only
(country, IP, common name, etc.). The mechanism for bypassing specific
paths is a SECOND self-hosted Application with the path-specific domains
and a Bypass policy. Cloudflare evaluates the more-specific path-bound
Application before the broader Edge gate Application.

Name: <TODO — name as configured (runbook suggested "Mealy plumbing-test bypass")>
Application domains:
  - api.mealy.dev / Path: plumbing-test
  - api.mealy.dev / Path: plumbing-test/read
Identity provider: irrelevant (Bypass action skips auth)
Policy: "Bypass plumbing-test"
  - Action: Bypass
  - Include → Selector: Everyone (fallback: IP ranges = 0.0.0.0/0 + ::/0)

Reason for bypass: cross-origin XHR from `mealy.dev` to
`api.mealy.dev/plumbing-test` cannot complete an OAuth-style Access
redirect. Slice 5's split-origin cookie verification depends on these two
paths reaching Fly directly. Removed alongside the `/plumbing-test*`
endpoints in M5 PR #2.

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
clears (~30/min worst case). M3's FastAPI middleware adds finer-grained
app-layer rate-limiting that can match the original 10/min/IP semantics
exactly. Verified working 2026-05-01 via `slice6-rate-limit-burst-test.sh`
(first 5 of 10 returned 404 from Fly origin, last 5 returned 429 from
Cloudflare).

Revisit if upgrading to Cloudflare Pro/Business — at that point, swap
expression to the original `(http.request.uri.path matches "^/auth/") and
(http.host eq "api.mealy.dev")` with 10-req/1-min/1-min-duration semantics.
