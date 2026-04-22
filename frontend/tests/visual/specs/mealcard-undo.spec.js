import { test, expect } from '@playwright/test'
import { bboxOf, waitForMealboardReady } from '../fixtures/geometric.js'

// Adversarial review A2 + CEO 4A — this spec creates its own throwaway meal
// entry and cleans it up in afterEach so the shared geometric fixtures stay
// immutable. Do NOT seed an already-soft-deleted row; orchestrating the
// delete through the UI is the point.

const API_URL = process.env.API_URL || 'http://localhost:8000'
// Pre-landing review fix #14 — throwaway rows always get sort_order=99 so a
// leftover from a crashed prior run can be swept before beforeEach re-seeds.
const THROWAWAY_SORT_ORDER = 99

function mondayOfThisWeekKey() {
  const today = new Date()
  const dayOfWeek = today.getDay()
  const offset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  const monday = new Date(today)
  monday.setDate(today.getDate() + offset)
  const y = monday.getFullYear()
  const m = String(monday.getMonth() + 1).padStart(2, '0')
  const d = String(monday.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

test.describe('Undo MealCard', () => {
  let throwawayEntryId = null

  test.beforeEach(async ({ request }) => {
    const monday = mondayOfThisWeekKey()

    // Pre-landing review fix #14 — if a prior run crashed between create and
    // cleanup, sweep any leftover throwaway rows on Monday before creating a
    // fresh one. Otherwise two throwaways would collide on `.last()` selectors
    // and the retry loop could accumulate rows across CI reruns.
    const existing = await request
      .get(`${API_URL}/meal-entries/?start_date=${monday}&end_date=${monday}`)
      .then((r) => r.json())
    for (const e of existing) {
      if (e.sort_order === THROWAWAY_SORT_ORDER) {
        await request.delete(`${API_URL}/meal-entries/${e.id}`).catch(() => {})
      }
    }

    // Grab an existing VRT item to attach the throwaway to. Reuses canonical
    // seed data so the test doesn't need to manufacture its own item.
    const items = await request.get(`${API_URL}/items/?search=VRT`).then((r) => r.json())
    const item = items.find((it) => it.name === 'VRT Recipe Beta')
    if (!item) {
      throw new Error('undo spec prereq: VRT Recipe Beta not found (globalSetup failed?)')
    }

    const slotTypes = await request
      .get(`${API_URL}/meal-slot-types/`)
      .then((r) => r.json())
    const slotId = slotTypes[0].id

    const created = await request
      .post(`${API_URL}/meal-entries/`, {
        data: {
          date: monday,
          meal_slot_type_id: slotId,
          item_id: item.id,
          sort_order: THROWAWAY_SORT_ORDER,
        },
      })
      .then((r) => r.json())
    throwawayEntryId = created.id
  })

  test.afterEach(async ({ request }) => {
    if (throwawayEntryId == null) return
    await request
      .delete(`${API_URL}/meal-entries/${throwawayEntryId}`)
      .catch(() => {})
    throwawayEntryId = null
  })

  test('undo card matches the replaced card bbox and does not shift the grid', async ({ page }) => {
    await waitForMealboardReady(page, { targetCardName: 'VRT Recipe Beta' })

    // Pre-landing review fix #1 — target by the exact entry id returned from
    // beforeEach, not by `.last()`. That selector was sort-order-dependent and
    // would silently pick the canonical Beta if a prior afterEach leaked.
    const liveCard = page.locator(
      `[data-testid="meal-card"][data-entry-id="${throwawayEntryId}"]`,
    )
    await expect(liveCard).toBeVisible()
    const liveBox = await bboxOf(liveCard)
    const grid = page.locator('[data-testid="swimlane-grid"]')
    const gridBefore = await bboxOf(grid)

    // Hover to reveal the action zone (recipe variant hides delete at rest).
    await liveCard.hover()
    const deleteButton = liveCard.locator('button[aria-label="Delete meal"]')
    // Pre-landing review fix #2 — explicit visibility wait before clicking so
    // Playwright's auto-wait doesn't race the max-h-0 → max-h-[48px] reveal.
    await expect(deleteButton).toBeVisible()
    await deleteButton.click()

    // UndoMealCard renders in the same grid cell with data-variant="undo".
    const undoCard = page.locator('[data-testid="meal-card"][data-variant="undo"]').first()
    await expect(undoCard).toBeVisible()
    const undoBox = await bboxOf(undoCard)

    // Match within 2px — slightly looser than PX_TOLERANCE because the button
    // element has different default browser styling than the recipe div.
    expect(Math.abs(undoBox.width - liveBox.width)).toBeLessThanOrEqual(2)
    expect(Math.abs(undoBox.height - liveBox.height)).toBeLessThanOrEqual(2)

    // Swimlane grid width must not change as a result of the swap.
    const gridAfter = await bboxOf(grid)
    expect(Math.abs(gridAfter.width - gridBefore.width)).toBeLessThanOrEqual(0.5)
  })
})
