const CATEGORY_COLORS = {
  BREAKFAST: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  LUNCH: 'bg-sage-100 text-sage-700 dark:bg-green-900/30 dark:text-green-400',
  DINNER: 'bg-peach-100 text-terracotta-700 dark:bg-orange-900/30 dark:text-orange-400'
}

export default function MealCard({ meal, recipe, onToggleCooked, onDelete }) {
  const mealName = recipe?.name || meal.custom_meal_name || 'Unnamed meal'
  const cookTime = recipe?.cook_time_minutes
  const isFavorite = recipe?.is_favorite
  const categoryColor = CATEGORY_COLORS[meal.category] || CATEGORY_COLORS.DINNER

  return (
    <div className={`meal-card meal-card-row-view relative p-3 rounded-xl border transition-all ${
      meal.was_cooked
        ? 'meal-card-cooked bg-sage-50 dark:bg-green-900/20 border-sage-200 dark:border-green-800'
        : 'bg-card-bg dark:bg-gray-800 border-card-border dark:border-gray-700 hover:shadow-md'
    }`}>
      {/* Category Badge */}
      <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full mb-2 ${categoryColor}`}>
        {meal.category}
      </span>

      {/* Meal Name */}
      <h4 className={`font-medium text-sm leading-tight mb-2 ${
        meal.was_cooked
          ? 'text-text-secondary dark:text-gray-400'
          : 'text-text-primary dark:text-gray-100'
      }`}>
        {mealName}
      </h4>

      {/* Meta Info */}
      <div className="flex items-center gap-2 text-xs text-text-muted dark:text-gray-500">
        {cookTime && (
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {cookTime} min
          </span>
        )}
        {isFavorite && (
          <span className="px-1.5 py-0.5 bg-terracotta-100 dark:bg-blue-900/30 text-terracotta-600 dark:text-blue-400 rounded text-xs">
            Favorite
          </span>
        )}
      </div>

      {/* Notes */}
      {meal.notes && (
        <p className="mt-2 text-xs text-text-muted dark:text-gray-500 italic">
          {meal.notes}
        </p>
      )}

      {/* Actions - Bottom of card, visible on hover */}
      <div className="meal-card-actions absolute bottom-2 left-3 right-3 flex items-center justify-end gap-1">
        {/* Cooked Toggle */}
        <button
          onClick={onToggleCooked}
          className={`p-1.5 rounded-full transition-colors ${
            meal.was_cooked
              ? 'bg-sage-500 text-white'
              : 'bg-warm-sand dark:bg-gray-700 text-text-muted dark:text-gray-500 hover:bg-sage-100 dark:hover:bg-green-900/30 hover:text-sage-600 dark:hover:text-green-400'
          }`}
          title={meal.was_cooked ? 'Mark as not cooked' : 'Mark as cooked'}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </button>

        {/* Delete */}
        <button
          onClick={onDelete}
          className="p-1.5 rounded-full bg-warm-sand dark:bg-gray-700 text-text-muted dark:text-gray-500 hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-500 transition-colors"
          title="Remove meal"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  )
}
