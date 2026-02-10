import SwipeableItem from './SwipeableItem'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function ResponsibilityCard({ responsibility, isCompleted, onToggle, onEdit, onDelete, enableSwipe = true, categoryContext = null }) {
  const iconSrc = responsibility.icon_url 
    ? (responsibility.icon_url.startsWith('http') ? responsibility.icon_url : `${API_BASE}${responsibility.icon_url}`)
    : null

  const handleToggle = () => {
    if (categoryContext) {
      onToggle(categoryContext)
    } else {
      onToggle()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleToggle()
    }
  }

  // Determine swipe action based on context
  // In daily view (has toggle), swipe completes/uncompletes
  // In edit view (has edit/delete but no meaningful toggle), swipe not needed
  const showSwipe = enableSwipe && onToggle && typeof onToggle === 'function'

  const cardContent = (
    <div
      role="button"
      tabIndex={0}
      onClick={handleToggle}
      onKeyDown={handleKeyDown}
      aria-pressed={isCompleted}
      aria-label={`${responsibility.title}${isCompleted ? ' (completed)' : ''}`}
      className={`
        group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all duration-200
        focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500
        ${isCompleted
          ? 'bg-sage-100 dark:bg-green-800 border border-sage-200 dark:border-green-800'
          : 'bg-card-bg dark:bg-gray-700/50 border border-card-border dark:border-gray-600 hover:bg-warm-beige dark:hover:bg-gray-700'
        }
      `}
    >
      {/* Icon */}
      {iconSrc && (
        <img
          src={iconSrc}
          alt=""
          className={`w-10 h-10 rounded object-cover flex-shrink-0 ${isCompleted ? 'opacity-60' : ''}`}
        />
      )}

      {/* Title and Description */}
      <div className="flex-1 min-w-0">
        <span
          className={`
            block text-sm font-medium transition-colors
            ${isCompleted
              ? 'text-sage-700 dark:text-green-400 line-through'
              : 'text-text-primary dark:text-gray-100'
            }
          `}
        >
          {responsibility.title}
        </span>
        {responsibility.description && (
          <p
            className={`
              mt-0.5 text-xs line-clamp-2
              ${isCompleted
                ? 'text-sage-600/70 dark:text-green-500/70'
                : 'text-text-muted dark:text-gray-400'
              }
            `}
          >
            {responsibility.description}
          </p>
        )}
      </div>

      {/* Action buttons */}
      {(onEdit || onDelete) && (
        <div className="flex items-center gap-1 flex-shrink-0">
          {onEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onEdit(responsibility)
              }}
              className="
                sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 opacity-100
                p-1.5 text-terracotta-600 dark:text-blue-400
                hover:text-terracotta-700 dark:hover:text-blue-300
                hover:bg-terracotta-50 dark:hover:bg-blue-900/30
                rounded transition-all duration-200
                focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500
              "
              aria-label={`Edit responsibility: ${responsibility.title}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete(responsibility.id)
              }}
              className="
                sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 opacity-100
                p-1.5 text-red-600 dark:text-red-400
                hover:text-red-700 dark:hover:text-red-300
                hover:bg-red-50 dark:hover:bg-red-900/30
                rounded transition-all duration-200
                focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500
              "
              aria-label={`Delete responsibility: ${responsibility.title}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      )}
    </div>
  )

  // Wrap with SwipeableItem for swipe-to-complete on mobile
  if (showSwipe) {
    return (
      <SwipeableItem
        onSwipeAction={handleToggle}
        actionType="complete"
        actionLabel={isCompleted ? 'Undo' : 'Done'}
      >
        {cardContent}
      </SwipeableItem>
    )
  }

  return cardContent
}