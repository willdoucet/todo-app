import { test, expect } from '@playwright/test'
import {
  bboxOf,
  expectStableAcrossHover,
  waitForMealboardReady,
} from '../fixtures/geometric.js'

test.describe('Food-item MealCard', () => {
  test('hovering a food-item card does not shift the SwimlaneGrid width', async ({ page }) => {
    await waitForMealboardReady(page, { targetCardName: 'VRT Food Item Alpha' })

    const card = page
      .locator('[data-testid="meal-card"][data-variant="food_item"]')
      .filter({ hasText: 'VRT Food Item Alpha' })
      .first()
    const grid = page.locator('[data-testid="swimlane-grid"]')
    const weekHeader = page.locator('[data-testid="week-header"]')

    await expectStableAcrossHover(page, grid, card, ['width'], weekHeader)
  })

  test('food-item card rest geometry is smaller than recipe baseline but non-zero', async ({ page }) => {
    await waitForMealboardReady(page, { targetCardName: 'VRT Food Item Alpha' })

    const foodCard = page
      .locator('[data-testid="meal-card"][data-variant="food_item"]')
      .filter({ hasText: 'VRT Food Item Alpha' })
      .first()
    const recipeCard = page
      .locator('[data-testid="meal-card"][data-variant="recipe"]')
      .filter({ hasText: 'VRT Recipe Alpha' })
      .first()

    const foodBox = await bboxOf(foodCard)
    const recipeBox = await bboxOf(recipeCard)

    expect(foodBox.height).toBeGreaterThan(0)
    expect(recipeBox.height).toBeGreaterThan(0)
    // Locks in the "food-item body is shorter than the recipe body" invariant
    // from the Chunk 2 plan (min-h-[52px] vs min-h-[100px]).
    expect(foodBox.height).toBeLessThan(recipeBox.height)
  })
})
