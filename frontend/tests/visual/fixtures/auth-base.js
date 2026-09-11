// M5 PR1 — Playwright base test fixture that intercepts /auth/refresh
// to return the access_token cached by globalSetup. This sidesteps the
// __Host-refresh cookie's Secure flag (which is rejected on http://api-test
// by the test browser). The frontend's M4 rootAuthLoader runs unmodified.
//
// Each spec changes its import from `@playwright/test` to this file,
// e.g.:
//   import { test, expect } from '../fixtures/auth-base.js'
//
// Behavior:
// - The refresh route ALWAYS returns 200 with the cached token, regardless
//   of whether the test browser's call would have succeeded against the
//   real backend (which it can't, because the Secure cookie was dropped).
// - The token itself is the one minted by globalSetup via real
//   /auth/login or /auth/register flow against api-test. So the backend
//   sees real auth headers from a real user; only the refresh round-trip
//   is short-circuited.
// - Side-effect of this design: the M4 boot-refresh ROUND-TRIP itself
//   isn't exercised by visual tests. That round-trip is covered by
//   frontend unit tests (vitest with MSW). Visual tests cover what the
//   user sees post-refresh (the mealboard).
//
// Defense in depth: the cached token is a 15-min JWT for a synthetic
// test user. Even so, .vrt-token is in .gitignore — never check in.
import { test as base } from '@playwright/test'
import fs from 'node:fs'

// Absolute path: matches the write side in globalSetup.js. Both files
// live under frontend/tests/visual/, so the token sits at .../visual/.vrt-token.
const TOKEN_PATH = new URL('../.vrt-token', import.meta.url).pathname
// Defensive load-time check: if globalSetup threw before writing the token
// (or never ran), surface a clear error here instead of letting spec
// imports die with ENOENT. The minimum-length check guards against a
// stale empty/whitespace file from a prior run failure.
let TOKEN
try {
  TOKEN = fs.readFileSync(TOKEN_PATH, 'utf8').trim()
} catch (err) {
  throw new Error(
    `auth-base.js: failed to read ${TOKEN_PATH} — globalSetup likely failed before writing the visual-test JWT. Original error: ${err.message}`,
  )
}
if (!TOKEN || TOKEN.length < 20) {
  throw new Error(
    `auth-base.js: ${TOKEN_PATH} contains an empty or invalid token (length=${TOKEN?.length ?? 0}). Re-run globalSetup or delete the stale file.`,
  )
}

// M7 PR2 — a 1x1 transparent PNG, inlined so this fixture stays self-contained.
const FIXTURE_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk' +
    'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
  'base64',
)

export const test = base.extend({
  context: async ({ context }, use) => {
    // M7 PR2 — serve fixture bytes for every private media read.
    //
    // `GET /uploads/*` is no longer a public static mount; it is a cookie-
    // authenticated route. The visual stack cannot satisfy that guard: the
    // browser talks to docker hostnames (`frontend-preview` / `api-test`),
    // which are not same-site, so a `SameSite=Strict` `__Host-refresh` cookie
    // would not transmit on an `<img>` subresource load — every image would
    // 401 and the geometry under test would shift. Same reason the
    // `/auth/refresh` intercept below exists.
    //
    // The real byte path is covered where it can be: backend pytest hits the
    // actual route with a real cookie (tests/integration/auth/test_media_read.py,
    // 41 tests). This suite only needs pixels. (Eng review A2.)
    //
    // NOTE: nothing in the current specs actually requests `/uploads/*` — the
    // seeded items use `icon_emoji`, not `icon_url`. This is deliberately
    // installed ahead of need, so the first spec that seeds an uploaded icon
    // or a stock icon stays deterministic instead of silently 401ing.
    await context.route('**/uploads/**', async (route) => {
      // GET only. `context.route` is method-agnostic, and `POST
      // /uploads/item-icon` is a real protected API endpoint — fulfilling it
      // with PNG bytes would make a future upload spec fail inexplicably, or
      // pass while proving nothing.
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'image/png',
        headers: { 'Cache-Control': 'private, no-cache' },
        body: FIXTURE_PNG,
      })
    })
    await context.route('**/auth/refresh', async (route) => {
      const origin = route.request().headers().origin
      const headers = origin
        ? {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Credentials': 'true',
          }
        : undefined
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers,
        // AccessTokenOut schema (app/auth/schemas.py L45-49) requires
        // both fields. Default token_type is "bearer".
        body: JSON.stringify({
          access_token: TOKEN,
          token_type: 'bearer',
        }),
      })
    })
    await use(context)
  },
  // M5 PR1 — direct API calls from spec code (Playwright's `request`
  // fixture, used by mealcard-undo.spec.js for setup/teardown) also need
  // a Bearer token now that the api-test stack enforces auth. Default
  // headers via extraHTTPHeaders cover every method on the request
  // fixture without requiring spec changes per call site.
  request: async ({ playwright }, use) => {
    const ctx = await playwright.request.newContext({
      extraHTTPHeaders: {
        Authorization: `Bearer ${TOKEN}`,
      },
    })
    await use(ctx)
    await ctx.dispose()
  },
})

export { expect } from '@playwright/test'
