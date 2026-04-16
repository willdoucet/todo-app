/**
 * Item delete confirm-dialog copy helpers.
 *
 * Encodes the item-type-aware usage copy table from plan §1689-1695
 * (Design Review IA pass issue 3A). Both RecipesView + FoodItemsView +
 * MealPlannerView use this so the delete confirm always shows the same
 * structured description.
 *
 * Exports:
 *   - buildDeleteTitle(item)       → string   "Delete \"{name}\"?"
 *   - buildDeleteDescription(item) → ReactNode <primary line><secondary line>
 */

export function buildDeleteTitle(item) {
  if (!item) return 'Delete item?'
  return `Delete "${item.name}"?`
}

/**
 * Build the structured description (primary + secondary line) for the delete
 * confirm. Reads `item.meal_entry_count` which the backend attaches on every
 * GET /items response (see crud_items._attach_usage_counts).
 */
export function buildDeleteDescription(item) {
  if (!item) return null
  const isRecipe = item.item_type === 'recipe'
  const typeLabel = isRecipe ? 'Recipe' : 'Food item'
  const count = item.meal_entry_count ?? 0

  let primary
  if (count === 0) {
    primary = `${typeLabel} · not currently used`
  } else if (count === 1) {
    primary = `${typeLabel} · used in 1 meal — it will also be removed`
  } else {
    primary = `${typeLabel} · used in ${count} meals — they will also be removed`
  }

  return (
    <>
      <p className="text-sm text-text-secondary dark:text-gray-400">{primary}</p>
      <p className="mt-1 text-xs text-text-muted dark:text-gray-500">
        You can undo this for the next 15 seconds.
      </p>
    </>
  )
}
