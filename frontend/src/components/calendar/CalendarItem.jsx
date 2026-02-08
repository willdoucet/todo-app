import { getMemberColor } from './calendarUtils'

/**
 * Single task or event line item for calendar views.
 * @param {object} props
 * @param {object} props.item - Task or CalendarEvent object
 * @param {'task'|'event'} props.type
 * @param {object} [props.member] - FamilyMember object for color resolution
 */
export default function CalendarItem({ item, type, member, onClick, onToggleComplete }) {
  const color = getMemberColor(member)
  const isCompleted = type === 'task' && item.completed
  const timeDisplay =
    type === 'event' && item.start_time
      ? item.all_day
        ? 'All day'
        : `${item.start_time}${item.end_time ? '–' + item.end_time : ''}`
      : null

  return (
    <div
      className={`flex items-center gap-2 py-1.5 px-2 rounded-md text-sm ${
        isCompleted ? 'line-through opacity-50' : ''
      } ${onClick ? 'cursor-pointer hover:bg-warm-sand/50 dark:hover:bg-gray-700/50' : ''}`}
      onClick={onClick ? () => onClick(item, type) : undefined}
    >
      {/* Icon / Checkbox */}
      {type === 'task' ? (
        <button
          type="button"
          className="shrink-0 p-0 bg-transparent border-none cursor-pointer text-text-secondary dark:text-gray-400 hover:text-terracotta-500 dark:hover:text-blue-400"
          onClick={onToggleComplete ? (e) => { e.stopPropagation(); onToggleComplete(item) } : undefined}
          aria-label={isCompleted ? 'Mark incomplete' : 'Mark complete'}
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            {isCompleted ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
              />
            )}
          </svg>
        </button>
      ) : (
        <svg
          className="w-4 h-4 shrink-0 text-text-secondary dark:text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      )}

      {/* Member color dot */}
      <span
        className="w-2.5 h-2.5 rounded-full shrink-0"
        style={{ backgroundColor: color }}
      />

      {/* Title */}
      <span className="truncate text-text-primary dark:text-gray-200">
        {item.title}
      </span>

      {/* Time */}
      {timeDisplay && (
        <span className="ml-auto text-xs text-text-muted dark:text-gray-500 whitespace-nowrap">
          {timeDisplay}
        </span>
      )}
    </div>
  )
}
