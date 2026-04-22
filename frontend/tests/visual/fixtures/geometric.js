import { expect } from '@playwright/test'

// Exported tolerance constants so specs can reuse them or reason about the
// defaults (Eng 5A). Specs override via the { tolerance } option on each
// helper when a specific assertion needs a different bar.
export const PX_TOLERANCE = 0.5 // Half-pixel tolerance for stable-across-state assertions.
export const DELTA_TOLERANCE = 1 // 1px tolerance for expected deltas (sub-pixel layout rounding).

export async function bboxOf(locator) {
  const box = await locator.boundingBox()
  if (!box) throw new Error(`boundingBox returned null for ${locator}`)
  return box
}

// With reducedMotion: 'reduce' in the Playwright config (Eng 4A),
// SwimlaneGrid.jsx:49 honors the media query and hover transitions don't
// animate — target-state geometry applies instantly. Only fonts still need a
// settle tick so text-sized bboxes stabilize.
async function settleTransitions(page) {
  await page.evaluate(() => document.fonts.ready)
}

// Adversarial review A3 — explicit readiness helper. Prefers UI signals over
// `networkidle`, which is a transport heuristic that can hang or go green on
// the wrong state. When `targetCardName` is supplied we wait for that
// specific seeded card to be visible before proceeding.
export async function waitForMealboardReady(page, { targetCardName } = {}) {
  await page.goto('/mealboard/planner')
  await expect(page.locator('[data-testid="swimlane-grid"]')).toBeVisible()
  if (targetCardName) {
    await expect(
      page.locator('[data-testid="meal-card"]').filter({ hasText: targetCardName }).first(),
    ).toBeVisible()
  } else {
    await expect(page.locator('[data-testid="meal-card"]').first()).toBeVisible()
  }
  await page.evaluate(() => document.fonts.ready)
}

/**
 * Assert that `staticLocator`'s bbox is stable across hover/rest/exit of
 * `hoverTargetLocator`. Used for invariants like "SwimlaneGrid width does
 * not change when a MealCard is hovered."
 */
export async function expectStableAcrossHover(
  page,
  staticLocator,
  hoverTargetLocator,
  dims = ['x', 'y', 'width', 'height'],
  neutralLocator = null,
  { tolerance = PX_TOLERANCE } = {},
) {
  const rest = await bboxOf(staticLocator)
  await hoverTargetLocator.hover()
  await settleTransitions(page)
  const hovered = await bboxOf(staticLocator)
  if (neutralLocator) {
    await neutralLocator.hover()
  } else {
    await page.mouse.move(0, 0)
  }
  await settleTransitions(page)
  const exited = await bboxOf(staticLocator)
  for (const d of dims) {
    expect(
      Math.abs(hovered[d] - rest[d]),
      `${d} stable on hover (delta should be <${tolerance}px)`,
    ).toBeLessThanOrEqual(tolerance)
    expect(
      Math.abs(exited[d] - rest[d]),
      `${d} stable on exit (delta should be <${tolerance}px)`,
    ).toBeLessThanOrEqual(tolerance)
  }
}

/**
 * Assert that hovering `targetLocator` changes `dim` by exactly
 * `expectedDelta` (± tolerance). Used for the +48px hover-expand invariant.
 */
export async function expectDeltaOnHover(
  page,
  targetLocator,
  dim,
  expectedDelta,
  neutralLocator = null,
  { tolerance = DELTA_TOLERANCE } = {},
) {
  const rest = await bboxOf(targetLocator)
  await targetLocator.hover()
  await settleTransitions(page)
  const hovered = await bboxOf(targetLocator)
  expect(
    Math.abs(hovered[dim] - rest[dim] - expectedDelta),
    `${dim} hover-delta ~= ${expectedDelta}px (± ${tolerance})`,
  ).toBeLessThanOrEqual(tolerance)
  // Restore to rest so state doesn't leak into the next assertion.
  if (neutralLocator) {
    await neutralLocator.hover()
  } else {
    await page.mouse.move(0, 0)
  }
  await settleTransitions(page)
}
