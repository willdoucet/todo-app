import { PlusIcon } from '@heroicons/react/24/outline'

/**
 * Reusable empty state component with illustration, heading, subtext, and optional CTA.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.icon - Icon component to display (defaults to clipboard)
 * @param {string} props.title - Main heading text
 * @param {string} props.description - Subtext explaining what users can do
 * @param {string} [props.actionLabel] - Text for the CTA button (if provided, button will show)
 * @param {Function} [props.onAction] - Click handler for the CTA button
 * @param {string} [props.className] - Additional CSS classes
 */
export default function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) {
  return (
    <div className={`text-center py-12 px-4 ${className}`}>
      {/* Icon */}
      <div className="flex justify-center mb-4">
        {icon || (
          <div className="w-16 h-16 rounded-full bg-warm-sand/50 dark:bg-gray-700 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-text-muted dark:text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Title */}
      <h3 className="text-lg font-medium text-text-primary dark:text-gray-100 mb-2">
        {title}
      </h3>

      {/* Description */}
      <p className="text-sm text-text-muted dark:text-gray-400 max-w-xs mx-auto mb-6">
        {description}
      </p>

      {/* CTA Button */}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="
            inline-flex items-center gap-2 px-4 py-2.5
            bg-terracotta-500 dark:bg-blue-600 text-white
            rounded-lg font-medium text-sm
            hover:bg-terracotta-600 dark:hover:bg-blue-700
            active:scale-[0.98] transition-all duration-200
            focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500 focus-visible:ring-offset-2
          "
        >
          <PlusIcon className="w-4 h-4" />
          {actionLabel}
        </button>
      )}
    </div>
  )
}

// Pre-configured empty states for common use cases
export function EmptyListsState({ onAction }) {
  return (
    <EmptyState
      icon={
        <div className="w-16 h-16 rounded-full bg-terracotta-100 dark:bg-blue-900/30 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-terracotta-500 dark:text-blue-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z"
            />
          </svg>
        </div>
      }
      title="No lists yet"
      description="Create your first list to start organizing your tasks."
      actionLabel="Create List"
      onAction={onAction}
    />
  )
}

export function EmptyTasksState({ onAction }) {
  return (
    <EmptyState
      icon={
        <div className="w-16 h-16 rounded-full bg-sage-100 dark:bg-green-900/30 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-sage-500 dark:text-green-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
      }
      title="No tasks yet"
      description="Add your first task to this list to get started."
      actionLabel="Add Task"
      onAction={onAction}
    />
  )
}

export function EmptyResponsibilitiesState({ onAction }) {
  return (
    <EmptyState
      icon={
        <div className="w-16 h-16 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-amber-500 dark:text-amber-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"
            />
          </svg>
        </div>
      }
      title="No responsibilities yet"
      description="Create recurring tasks for family members to complete daily."
      actionLabel="Add Responsibility"
      onAction={onAction}
    />
  )
}

export function EmptyDailyViewState() {
  return (
    <EmptyState
      icon={
        <div className="w-16 h-16 rounded-full bg-warm-sand/50 dark:bg-gray-700 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-text-muted dark:text-gray-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
            />
          </svg>
        </div>
      }
      title="Nothing scheduled"
      description="No responsibilities are scheduled for this day."
    />
  )
}
