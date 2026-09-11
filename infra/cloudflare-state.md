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

Status: **active (2026-09-11)** — deployed in the `mealy.dev` zone and verified
end to end that day: through Cloudflare, `/uploads/<key>` → 401 and
`/auth/status` → 200 with the `mealy.dev` CORS header; straight to the Fly IP
(`curl --resolve`) → 421; a `Host: api.mealy.dev/healthz?` spoof aimed at a real
route → 421 at the origin (400 at the edge); `/healthz` → 200 by both paths.

Dashboard path (post-2025 redesign; there is no longer a "Transform Rules →
Modify Request Header" submenu): select the **`mealy.dev` zone** (this is a
zone-level feature, not account-level) → **Rules → Overview** (older accounts:
**Rules → Transform Rules**) → **Create rule → Request Header Transform Rule**.

Rule name: Mealy origin lock
When incoming requests match: **Custom filter expression**
  `(http.host eq "api.mealy.dev")`
  (Expression Builder equivalent: Field `Hostname`, Operator `equals`, Value
  `api.mealy.dev`.)
Then → Modify request header: **Set static**
  - Header name: `X-Origin-Verify`
  - Value: the `ORIGIN_VERIFY_SECRET` Fly secret. **Never written in this file,
    in git, or in a chat transcript.**
Deploy.

Free plan: allowed (10 transform rules total; this uses 1). The only Free
limitation is no regex in expressions — not needed here, `eq` is exact match.
API fallback if the rule type is not visible in the dashboard:
`PUT /zones/{zone_id}/rulesets/phases/http_request_late_transform/entrypoint`
with a single `rewrite` rule whose `action_parameters.headers` sets
`X-Origin-Verify` to `{"operation":"set","value":"<secret>"}`.

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
2. In the `mealy.dev` zone: Rules → Overview → Create rule → Request Header
   Transform Rule. Create the rule above (see the dashboard path at the top of
   this section), paste the value, Deploy.
3. Store the same value as a Fly secret (this restarts the machines on the
   current image). Keep the value out of the `fly` process's arguments (visible
   in `ps`) — `printf` is a shell builtin — and collapse stray whitespace, so a
   trailing blank line cannot emit a SECOND, empty `ORIGIN_VERIFY_SECRET=`
   assignment. That one wins, blanks the secret, and the app then refuses to
   boot at all:
   ```bash
   printf 'ORIGIN_VERIFY_SECRET=%s\n' "$(pbpaste | tr -d '[:space:]')" | fly secrets import -a mealy-app-prod
   ```
   Then clear the clipboard:
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
5. Verify from outside, never by hammering `/auth/login`. First confirm the
   machines finished restarting — `fly secrets import` triggers a restart, and
   checking during that window still hits the OLD secret and reports a false
   failure:
   ```bash
   fly status -a mealy-app-prod
   ```
   Wait for every `web` machine to show a fresh `LAST UPDATED` and passing
   checks, then:
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

If real traffic gets 421 after step 4, either the Fly secret and the rule's
value differ, or Cloudflare is not applying the rule at all. From outside the
two are indistinguishable — both checks return the same 421 body by design — so
work through them in this order:

1. Force Fly to match what Cloudflare actually has. The rule's **Value** field
   is readable in the dashboard: copy it, then re-run rollout step 3. This is
   what fixed the 2026-09-11 rollout, where the two sides had drifted apart.
   Wait for the restart, then re-verify.
2. If it still 421s, the value is provably identical on both sides and the rule
   is not being applied: check that it is **Deployed** rather than saved as a
   draft, is a **Request** (not Response) header rule, sits in the `mealy.dev`
   zone, and that its expression matches.
3. Break-glass: redeploying the previous image restores service and reopens the
   bypass. Safe for this change because it does not touch `fly.toml`.

### Rotation

Repeat rollout steps 1–3 with a new value, running the `fly secrets import`
immediately after saving the dashboard rule. Between the two, requests carry the
new value while the app still expects the old one, so expect a short burst of
421s. `fly secrets import` restarts the web machines anyway, so accepting two
values during a rotation would not remove the gap.

### Gotchas when setting or rotating the secret

Three traps, all hit during the 2026-09-11 rollout:

- **The clipboard collision.** A command using `pbpaste` reads the clipboard when
  it RUNS, not when you paste it — so copying the command itself overwrites the
  value you meant to use, and the header is set to the command text. Paste the
  command into the terminal first, then copy the value, then press Enter.
- **Verify only after the restart finishes.** `fly secrets import` restarts the
  machines; a check run during that window still hits the old secret and looks
  like a failure. Confirm `LAST UPDATED` moved in `fly status` first.
- **A 421 never says which check failed.** The host check and the origin-header
  check return an identical body on purpose, so "rule not applied" and "values
  differ" look the same from outside. Use the ordered recovery above instead of
  guessing.
