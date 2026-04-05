// Category badge colors
const CATEGORY_STYLES = {
  fruit: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  vegetable: 'bg-sage-100 text-sage-700 dark:bg-green-900/30 dark:text-green-400',
  protein: 'bg-peach-100 text-terracotta-700 dark:bg-red-900/30 dark:text-red-400',
  dairy: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  grain: 'bg-warm-sand text-text-secondary dark:bg-gray-700 dark:text-gray-300',
}

/**
 * List row for a food item. Shows emoji, name, category badge, favorite, actions.
 */
export default function FoodItemRow({ item, isLast, onEdit, onDelete, onToggleFavorite }) {
  return (
    <div
      className={`
        group flex items-center gap-3 px-4 py-3
        ${!isLast ? 'border-b border-card-border dark:border-gray-700' : ''}
        hover:bg-warm-beige/50 dark:hover:bg-gray-700/30 transition-colors
      `}
    >
      {/* Emoji */}
      <div className="text-xl leading-none w-8 text-center">
        {item.emoji || '🍽'}
      </div>

      {/* Name */}
      <div className="flex-1 text-sm font-medium text-text-primary dark:text-gray-100">
        {item.name}
      </div>

      {/* Category badge */}
      {item.category && (
        <div
          className={`px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wide ${CATEGORY_STYLES[item.category] || 'bg-warm-sand'}`}
        >
          {item.category}
        </div>
      )}

      {/* Favorite */}
      <button
        type="button"
        onClick={onToggleFavorite}
        className={`
          p-1.5 rounded-md transition-all
          ${
            item.is_favorite
              ? 'text-terracotta-500 dark:text-blue-400 opacity-100'
              : 'text-text-muted dark:text-gray-500 hover:text-terracotta-500 dark:hover:text-blue-400'
          }
        `}
        title={item.is_favorite ? 'Unfavorite' : 'Favorite'}
        aria-label={item.is_favorite ? 'Unfavorite' : 'Favorite'}
      >
        <svg className="w-4 h-4" fill={item.is_favorite ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
        </svg>
      </button>

      {/* Edit/delete actions (hover reveal) */}
      <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          onClick={onEdit}
          className="p-1.5 rounded-md text-text-muted dark:text-gray-400 hover:text-terracotta-600 dark:hover:text-blue-400 hover:bg-warm-beige dark:hover:bg-gray-700 transition-colors"
          title="Edit"
          aria-label="Edit"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="p-1.5 rounded-md text-text-muted dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          title="Delete"
          aria-label="Delete"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  )
}
