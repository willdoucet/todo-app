import { test } from '@playwright/test'
import { expectStableAcrossHover, waitForMealboardReady } from '../fixtures/geometric.js'

// The exact invariants that the shipped hover-jitter fix is meant to
// preserve. SC4 demands this spec specifically fail — with a message
// containing `width stable on hover` — when the `mealboard-scroll-stable`
// class is reverted on MealPlannerView.jsx.
test('SwimlaneGrid width + all day-header x-positions stable across MealCard hover', async ({ page }) => {
  await waitForMealboardReady(page, { targetCardName: 'VRT Food Item Alpha' })

  const firstCard = page
    .locator('[data-testid="meal-card"]')
    .filter({ hasText: 'VRT Food Item Alpha' })
    .first()
  const grid = page.locator('[data-testid="swimlane-grid"]')
  const weekHeader = page.locator('[data-testid="week-header"]')
  const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

  // 1. Grid width must not move when a card is hovered.
  await expectStableAcrossHover(page, grid, firstCard, ['width'], weekHeader)

  // 2. Every day-header column's x-position must stay put.
  for (const d of days) {
    const header = page.locator(`[data-testid="day-header-${d}"]`)
    await expectStableAcrossHover(page, header, firstCard, ['x'], weekHeader)
  }
})
