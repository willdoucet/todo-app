import { test, expect } from '@playwright/test'
import { waitForMealboardReady } from '../fixtures/geometric.js'

// Eng 8A + Adversarial review A3/A4 — this file's name is prefixed `aaa-` so
// Playwright's alphabetical ordering runs it first. When the mealboard page
// is broken at the root, this smoke short-circuits the suite via
// maxFailures: 1 (in CI), saving time on four cryptic geometric failures
// that all share the same root cause.
test('mealboard page loads with canonical VRT seed rows and no console errors', async ({ page }) => {
  const consoleErrors = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text())
  })
  page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`))

  await waitForMealboardReady(page, { targetCardName: 'VRT Recipe Alpha' })

  // Pre-landing review fix #7 — count VRT-prefixed cards specifically.
  // Total `[data-testid="meal-card"]` would also match any pre-existing
  // non-VRT entries on the current week in a local dev DB and mask a true
  // smoke failure (seed inserted 0 cards but local DB had 3 stale ones).
  const vrtCardCount = await page
    .locator('[data-testid="meal-card"]')
    .filter({ hasText: /^VRT / })
    .count()
  expect(
    vrtCardCount,
    'mealboard smoke: expected >= 3 VRT-prefixed seeded meal cards after globalSetup',
  ).toBeGreaterThanOrEqual(3)

  expect(
    await page
      .locator('[data-testid="meal-card"]')
      .filter({ hasText: 'VRT Food Item Alpha' })
      .count(),
    'mealboard smoke: expected canonical VRT food-item seed row',
  ).toBeGreaterThanOrEqual(1)

  expect(consoleErrors, 'mealboard smoke: no JS errors in console').toEqual([])
})
