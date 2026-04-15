import { getRecipeDotColor } from '../../constants/recipeGradients'

const HEART_PATH = 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z'

// Category color map for food_item rows (legacy FoodItemRow used badge pills)
const CATEGORY_BADGE = {
  fruit: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  vegetable: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  protein: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  dairy: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  grain: 'bg-warm-sand text-text-secondary dark:bg-gray-700 dark:text-gray-300',
  Other: 'bg-warm-sand text-text-secondary dark:bg-gray-700 dark:text-gray-300',
}

/**
 * Unified list row for the Item model. Branches on `item.item_type`:
 *   - recipe: gradient dot + name + time/servings metadata + heart + hover edit/delete
 *   - food_item: emoji + name + category badge + heart + hover edit/delete
 *
 * Replaces RecipeRow + FoodItemRow. Click row → opens drawer (recipes) or form (food items).
 */
export default function ItemRow({ item, index = 0, isLast, onClick, onEdit, onDelete, onToggleFavorite }) {
  const isRecipe = item.item_type === 'recipe'
  const rd = item.recipe_detail || {}
  const fid = item.food_item_detail || {}
  const isDark = document.documentElement.classList.contains('dark')

  const animStyle = {
    animation: `recipe-row-enter 0.25s ease both`,
    animationDelay: `${Math.min(index * 25, 500)}ms`,
  }

  const totalTime = (rd.prep_time_minutes || 0) + (rd.cook_time_minutes || 0)
  const categoryKey = fid.category || 'Other'
  const badgeClass = CATEGORY_BADGE[categoryKey] || CATEGORY_BADGE.Other

  return (
    <div
      className={`
        group flex items-center gap-3 px-4 py-3 cursor-pointer
        ${!isLast ? 'border-b border-card-border dark:border-gray-700' : ''}
        hover:bg-warm-beige/50 dark:hover:bg-gray-700/30 transition-colors duration-150
      `}
      style={animStyle}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      tabIndex={0}
      role="button"
    >
      {/* Leading visual — gradient dot for recipes, emoji for food items */}
      {isRecipe ? (
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: getRecipeDotColor(item.name, isDark) }}
          aria-hidden="true"
        />
      ) : (
        <span className="text-xl leading-none flex-shrink-0 w-7 text-center" aria-hidden="true">
          {item.icon_emoji || '🍽'}
        </span>
      )}

      {/* Name */}
      <div className="flex-1 text-sm font-medium text-text-primary dark:text-gray-100 truncate">
        {item.name}
      </div>

      {/* Metadata */}
      {isRecipe ? (
        <div className="flex items-center gap-1.5 text-xs text-text-muted dark:text-gray-400 flex-shrink-0">
          {totalTime > 0 && <span>⏲ {totalTime}m</span>}
          {totalTime > 0 && rd.servings && <span className="text-card-border dark:text-gray-600">·</span>}
          {rd.servings && <span>{rd.servings} serving{rd.servings > 1 ? 's' : ''}</span>}
        </div>
      ) : (
        <span
          className={`text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full flex-shrink-0 ${badgeClass}`}
        >
          {categoryKey}
        </span>
      )}

      {/* Favorite heart */}
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onToggleFavorite?.() }}
        className={`
          p-1.5 rounded-md transition-all flex-shrink-0
          ${item.is_favorite
            ? 'text-[#E06B6B] opacity-100'
            : 'text-text-muted dark:text-gray-500 hover:text-[#E06B6B]'
          }
        `}
        aria-label={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24"
          fill={item.is_favorite ? 'currentColor' : 'none'}
          stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d={HEART_PATH} />
        </svg>
      </button>

      {/* Hover edit/delete */}
      <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-[180ms] flex-shrink-0">
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onEdit?.() }}
          className="p-1.5 rounded-md text-text-muted dark:text-gray-400 hover:text-terracotta-600 dark:hover:text-blue-400 hover:bg-warm-beige dark:hover:bg-gray-700 transition-all duration-150 hover:scale-110"
          aria-label={`Edit ${item.name}`}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onDelete?.() }}
          className="p-1.5 rounded-md text-text-muted dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-150 hover:scale-110"
          aria-label={`Delete ${item.name}`}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  )
}
