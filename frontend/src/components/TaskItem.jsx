// components/TaskItem.jsx
import SwipeableItem from './SwipeableItem'

// Custom circle checkbox with animation
function CustomCheckbox({ checked, onChange }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={onChange}
      className={`
        w-5 h-5 rounded-full border-2 flex items-center justify-center
        transition-all duration-200 flex-shrink-0
        ${checked
          ? 'bg-gray-400 border-gray-400 scale-100'
          : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
        }
        focus:outline-none focus:ring-2 focus:ring-gray-400/50 focus:ring-offset-2 dark:focus:ring-offset-gray-900
      `}
    >
      {checked && (
        <svg
          className="w-3 h-3 text-white animate-[scale-in_150ms_ease-out]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={3}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      )}
    </button>
  )
}

// Icon component for assigned_to - smaller, cleaner styling
function AssignedIcon({ familyMember }) {
  // Handle "Everyone" (system member) with group icon
  if (familyMember?.is_system || familyMember?.name === 'Everyone') {
    return (
      <div
        className="flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 dark:bg-gray-800"
        title="Assigned to Everyone"
      >
        <svg className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      </div>
    )
  }

  // For individual family members, show first letter avatar
  const name = familyMember?.name || '?'
  const initial = name.charAt(0).toUpperCase()

  // Lighter, more subtle color palette
  const colors = [
    { bg: 'bg-blue-50 dark:bg-blue-900/30', text: 'text-blue-500 dark:text-blue-400' },
    { bg: 'bg-pink-50 dark:bg-pink-900/30', text: 'text-pink-500 dark:text-pink-400' },
    { bg: 'bg-green-50 dark:bg-green-900/30', text: 'text-green-500 dark:text-green-400' },
    { bg: 'bg-purple-50 dark:bg-purple-900/30', text: 'text-purple-500 dark:text-purple-400' },
    { bg: 'bg-orange-50 dark:bg-orange-900/30', text: 'text-orange-500 dark:text-orange-400' },
  ]

  // Simple hash to pick a consistent color
  const colorIndex = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % colors.length
  const color = colors[colorIndex]

  return (
    <div
      className={`flex items-center justify-center w-6 h-6 rounded-full ${color.bg}`}
      title={`Assigned to ${name}`}
    >
      <span className={`text-xs font-medium ${color.text}`}>
        {initial}
      </span>
    </div>
  )
}

// Format due date - shorter format
function formatDueDate(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const currentYear = now.getFullYear()
  const dateYear = date.getFullYear()

  const options = {
    month: 'short',
    day: 'numeric',
    ...(dateYear !== currentYear && { year: 'numeric' })
  }

  return date.toLocaleDateString('en-US', options)
}

export default function TaskItem({ task, onToggle, onEdit, onDelete }) {
  const isOverdue = task.due_date && !task.completed && new Date(task.due_date) < new Date()

  return (
    <SwipeableItem
      onSwipeAction={() => onDelete(task.id)}
      actionType="delete"
      actionLabel="Delete"
    >
      <div className={`
        group flex items-start gap-3 p-4 rounded-xl border
        bg-white dark:bg-gray-900
        border-gray-200 dark:border-gray-800
        hover:border-gray-300 dark:hover:border-gray-700
        hover:shadow-sm
        transition-all duration-200
        ${task.completed ? 'opacity-60' : ''}
      `}>
      <CustomCheckbox
        checked={task.completed}
        onChange={() => onToggle(task.id)}
      />

      <div className="flex-1 min-w-0">
        <p className={`
          text-sm font-medium leading-snug
          ${task.completed
            ? 'line-through text-gray-400 dark:text-gray-500'
            : 'text-gray-900 dark:text-gray-100'}
        `}>
          {task.title}
        </p>
        {task.description && (
          <p className={`mt-1 text-xs ${
            task.completed
              ? 'text-gray-400 dark:text-gray-500'
              : 'text-gray-500 dark:text-gray-400'
          }`}>
            {task.description}
          </p>
        )}
        {task.due_date && (
          <div className="mt-1.5 flex items-center gap-1">
            {/* Warning icon for overdue tasks (WCAG 1.4.1 - not color alone) */}
            {isOverdue && (
              <svg className="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
            )}
            <svg className={`w-3 h-3 ${
              isOverdue ? 'text-red-500' : 'text-gray-400 dark:text-gray-500'
            }`} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className={`text-xs ${
              isOverdue
                ? 'text-red-500 font-medium'
                : task.completed
                  ? 'text-gray-400 dark:text-gray-500'
                  : 'text-gray-500 dark:text-gray-400'
            }`}>
              {isOverdue && <span className="sr-only">Overdue: </span>}
              {formatDueDate(task.due_date)}
            </p>
          </div>
        )}
      </div>

      {/* Right side: Status icons + Action buttons (unified container) */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {/* Important star - in 32px wrapper for alignment */}
        {task.important && (
          <div
            className="w-8 h-8 flex items-center justify-center"
            title="Important"
          >
            <svg
              className="w-4 h-4 text-amber-500"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </div>
        )}

        {/* Assigned to icon - in 32px wrapper for alignment */}
        {task.family_member && (
          <div className="w-8 h-8 flex items-center justify-center">
            <AssignedIcon familyMember={task.family_member} />
          </div>
        )}

        {/* Edit button */}
        <button
          onClick={onEdit}
          className="
            sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 opacity-100
            w-8 h-8 flex items-center justify-center
            text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
            hover:bg-gray-100 dark:hover:bg-gray-800
            rounded-lg transition-all duration-200
            focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500
          "
          aria-label={`Edit task: ${task.title}`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>

        {/* Delete button */}
        <button
          onClick={() => onDelete(task.id)}
          className="
            sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 opacity-100
            w-8 h-8 flex items-center justify-center
            text-gray-400 hover:text-red-500 dark:hover:text-red-400
            hover:bg-gray-100 dark:hover:bg-gray-800
            rounded-lg transition-all duration-200
            focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500
          "
          aria-label={`Delete task: ${task.title}`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
      </div>
    </SwipeableItem>
  )
}
