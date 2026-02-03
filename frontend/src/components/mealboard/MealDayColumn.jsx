import MealCard from './MealCard'

const MEAL_CATEGORIES = ['BREAKFAST', 'LUNCH', 'DINNER']

export default function MealDayColumn({
  date,
  isToday,
  meals,
  getRecipeById,
  onAddMeal,
  onToggleCooked,
  onDeleteMeal
}) {
  const dayName = date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase()
  const dayNumber = date.getDate()

  const getMealForCategory = (category) => {
    return meals.find(m => m.category === category)
  }

  return (
    <div className={`h-full flex flex-col border-r border-card-border dark:border-gray-700 last:border-r-0 ${
      isToday ? 'bg-peach-100/30 dark:bg-blue-900/10' : ''
    }`}>
      {/* Day Header */}
      <div className={`px-3 py-3 text-center border-b border-card-border dark:border-gray-700 ${
        isToday ? 'bg-peach-100 dark:bg-blue-900/30' : ''
      }`}>
        <p className={`text-xs font-medium ${
          isToday ? 'text-terracotta-600 dark:text-blue-400' : 'text-text-muted dark:text-gray-500'
        }`}>
          {dayName}
        </p>
        <p className={`text-xl font-bold ${
          isToday ? 'text-terracotta-600 dark:text-blue-400' : 'text-text-primary dark:text-gray-100'
        }`}>
          {dayNumber}
        </p>
      </div>

      {/* Meal Slots */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto">
        {MEAL_CATEGORIES.map(category => {
          const meal = getMealForCategory(category)
          const recipe = meal?.recipe_id ? getRecipeById(meal.recipe_id) : null

          if (meal) {
            return (
              <MealCard
                key={category}
                meal={meal}
                recipe={recipe}
                onToggleCooked={() => onToggleCooked(meal)}
                onDelete={() => onDeleteMeal(meal.id)}
              />
            )
          }

          return (
            <button
              key={category}
              onClick={() => onAddMeal(date, category)}
              className="w-full p-3 border-2 border-dashed border-card-border dark:border-gray-600 rounded-xl text-text-muted dark:text-gray-500 hover:border-terracotta-300 dark:hover:border-blue-500 hover:text-terracotta-600 dark:hover:text-blue-400 transition-colors group"
            >
              <div className="flex flex-col items-center gap-1">
                <svg className="w-5 h-5 opacity-50 group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span className="text-xs">Add meal</span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
