// Category color map
const CATEGORY_COLORS = {
  fruit: 'bg-amber-100 dark:bg-amber-900/30',
  vegetable: 'bg-sage-100 dark:bg-green-900/30',
  protein: 'bg-peach-100 dark:bg-red-900/30',
  dairy: 'bg-blue-100 dark:bg-blue-900/30',
  grain: 'bg-warm-sand dark:bg-gray-700',
}

/**
 * Compact grid card for a food item. Shows emoji + name + category dot.
 * Hover reveals edit/delete actions and favorite heart.
 */
export default function FoodItemCard({ item, onEdit, onDelete, onToggleFavorite }) {
  return (
    <div
      className="
        group relative aspect-square flex flex-col items-center justify-center
        p-3 rounded-xl border border-card-border dark:border-gray-700
        bg-card-bg dark:bg-gray-800
        hover:shadow-md hover:border-terracotta-200 dark:hover:border-blue-700
        transition-all cursor-default
      "
    >
      {/* Favorite toggle (top-right) */}
      <button
        type="button"
        onClick={onToggleFavorite}
        className={`
          absolute top-1.5 right-1.5 p-1 rounded-full transition-all
          ${
            item.is_favorite
              ? 'text-terracotta-500 dark:text-blue-400 opacity-100'
              : 'text-text-muted dark:text-gray-500 opacity-0 group-hover:opacity-100 hover:text-terracotta-500 dark:hover:text-blue-400'
          }
        `}
        title={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
        aria-label={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
      >
        <svg className="w-4 h-4" fill={item.is_favorite ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
        </svg>
      </button>

      {/* Edit/delete actions (bottom, hover reveal) */}
      <div className="absolute bottom-1.5 right-1.5 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          onClick={onEdit}
          className="p-1 rounded-full bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-terracotta-100 dark:hover:bg-blue-900/40 hover:text-terracotta-600 dark:hover:text-blue-400 transition-colors"
          title="Edit"
          aria-label="Edit food item"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="p-1 rounded-full bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-red-100 dark:hover:bg-red-900/40 hover:text-red-600 dark:hover:text-red-400 transition-colors"
          title="Delete"
          aria-label="Delete food item"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>

      {/* Emoji */}
      <div className="text-3xl sm:text-4xl leading-none mb-1.5">
        {item.emoji || '🍽'}
      </div>

      {/* Name */}
      <div className="text-xs font-medium text-text-primary dark:text-gray-100 text-center line-clamp-2">
        {item.name}
      </div>

      {/* Category dot */}
      {item.category && (
        <div
          className={`w-2 h-2 rounded-full mt-1.5 ${CATEGORY_COLORS[item.category] || 'bg-warm-sand'}`}
          title={item.category}
        />
      )}
    </div>
  )
}
