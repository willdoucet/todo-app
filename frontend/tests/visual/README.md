# Visual Regression Tests

Geometric invariants for the mealboard UI, run via Playwright against the
production `vite preview` bundle in Docker.

## Why geometric, not pixel?

The bugs we actually hit — hover-jitter, title wrap flip, card-body collapse —
are geometric: bbox position/size deltas across state transitions. Asserting
`grid.boundingBox().width` is stable is deterministic without font-rendering
Docker wrestling, which is the conventional VRT flake source. Pixel diffs
(`toHaveScreenshot()`) can be added later for aesthetic regressions (shadow
intensity, color palette); the fixture leaves a clean seam for that.

## Run locally

**Rebuild any time the frontend working tree changes** (app code, Vite config,
Playwright config, specs, or fixtures) — there is no bind mount, so `npx
playwright test` against a stale image silently tests an old bundle
(Adversarial review A5):

```bash
cd backend
docker-compose --profile visual-test build frontend-preview frontend-visual
docker-compose --profile visual-test up -d --wait db redis api-test frontend-preview
docker-compose --profile visual-test run --rm frontend-visual
```

Fast rerun when **neither frontend code nor specs changed** since the last
build:

```bash
docker-compose --profile visual-test run --rm frontend-visual
```

Teardown:

```bash
docker-compose --profile visual-test down -v
```

## Debugging a failing spec

Traces land in `frontend/test-results/`. Open the HTML report:

```bash
open frontend/test-results/report/index.html
```

Click any failing test → **Trace** to step through the full session
(screenshots, DOM snapshots, network). The trace viewer is the primary
debugging tool because `http://localhost:4173/` is **not** reachable from the
host browser in this setup — the preview bundle is built with
`VITE_API_BASE_URL=http://api-test:8000`, which only resolves inside the
docker network. If you want to poke at the preview from the host, add a local
`preview:local` build target (not currently planned).

CI uploads `frontend/test-results/` as the `playwright-report` artifact on
failure — download it from the failed Actions run and open
`report/index.html` locally.

## Adding a new invariant test

1. Copy `specs/mealcard-recipe.spec.js` as a starting template.
2. Use `waitForMealboardReady(page, { targetCardName })` to load the page.
3. Use `expectStableAcrossHover(page, staticLocator, hoverTarget, dims, neutral)`
   for "X doesn't move when Y is hovered" invariants.
4. Use `expectDeltaOnHover(page, target, dim, expectedPx, neutral)` for
   "X moves by exactly N px on hover" invariants.
5. Tolerance defaults are exported as `PX_TOLERANCE` (0.5) and
   `DELTA_TOLERANCE` (1); per-call overrides via `{ tolerance: n }`.

## Flake-response protocol (SC6)

If a run flakes during the 10-run soak:

1. Capture the failing diff, the delta, and the run ID.
2. If the delta is within 1–2px and the element is a known-dynamic region
   (text, emoji), widen the tolerance for **that specific assertion only**,
   not globally.
3. If the delta is larger, treat as a real bug — even if intermittent. Do
   not "tune the tolerance" as a first response.
4. If the flake recurs after tolerance widening, revert the soak-gate and
   land with a caveat: CI gate is advisory until the next hardening PR.

## Baseline management

When a design change legitimately shifts a geometric invariant (e.g., card
hover-expand moves from +48px to +52px), update the literal number in the
spec file **in the same PR** that makes the design change. Baselines are
source code, not separate files.

## Version bump rules (Eng 1B)

`@playwright/test` is pinned in two places:

- `frontend/package.json` devDependencies
- `PLAYWRIGHT_VERSION` ARG at the top of `frontend/Dockerfile`

Bump both in the same PR. The `visual-test` Dockerfile target asserts the
`package-lock.json` version matches the ARG and fails the build on drift.
Accidentally updating one without the other = clear failure, not a silent
browser-vs-client mismatch.

## Seed idempotency (Eng 2A)

`tests/visual/fixtures/seed.js` deletes any existing `VRT ...` meal entries
and items in the target week before inserting the canonical set. Local
reruns stay clean without `docker-compose down -v`. The nuclear reset is
still available when the test DB gets wedged.

## CI_FERNET_KEY secret (one-time setup)

The `api-test` container refuses to start without `FERNET_KEY`. GitHub
Actions provisions it from a repo secret. Generate once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste into **Settings → Secrets and variables → Actions → New repository
secret** with name `CI_FERNET_KEY`. This is a test-only key; it has no
production access.

## Rollout / branch-protection plan

1. Ship the `visual-tests` CI job as non-required.
2. Run 10 consecutive CI cycles on a trivial no-op commit (SC6). `gh run rerun <id>` in a loop, or push 10 empty `chore:` commits.
3. If all 10 pass with zero retries, flip the job to **Required** in
   **Settings → Branches → master → Require status checks**.
4. If flake appears, apply the flake-response protocol and rerun the soak.

## Rollback

If the `visual-tests` job flakes after being made required: delete the
`visual-tests:` block from `.github/workflows/test.yml` in a one-line PR.
The `api-test` / `frontend-preview` / `frontend-visual` services are
profile-gated so they have zero impact on normal `docker-compose up`. No
DB migrations, no feature flags, no user-visible rollback sequence.
