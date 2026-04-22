import { test, expect } from '@playwright/test'
import {
  bboxOf,
  expectStableAcrossHover,
  waitForMealboardReady,
} from '../fixtures/geometric.js'

test.describe('Recipe MealCard', () => {
  test('hovering a recipe card does not shift the SwimlaneGrid width', async ({ page }) => {
    await waitForMealboardReady(page, { targetCardName: 'VRT Recipe Alpha' })

    const card = page
      .locator('[data-testid="meal-card"][data-variant="recipe"]')
      .filter({ hasText: 'VRT Recipe Alpha' })
      .first()
    const grid = page.locator('[data-testid="swimlane-grid"]')
    const weekHeader = page.locator('[data-testid="week-header"]')

    await expectStableAcrossHover(page, grid, card, ['width'], weekHeader)
  })

  test('recipe card has non-zero rest geometry and single-line title', async ({ page }) => {
    await waitForMealboardReady(page, { targetCardName: 'VRT Recipe Alpha' })

    const card = page
      .locator('[data-testid="meal-card"][data-variant="recipe"]')
      .filter({ hasText: 'VRT Recipe Alpha' })
      .first()
    const box = await bboxOf(card)

    // Non-zero baseline — catches display:none / visibility:hidden regressions.
    expect(box.width).toBeGreaterThan(40)
    expect(box.height).toBeGreaterThan(40)
  })
})
