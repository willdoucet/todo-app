// components/TaskItem.jsx
import SwipeableItem from '../shared/SwipeableItem'

// Rounded-square checkbox matching Option B mockup
function CustomCheckbox({ checked, onChange }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={onChange}
      className={`
        w-4 h-4 rounded flex items-center justify-center
        transition-all duration-100 flex-shrink-0
        ${checked
          ? 'bg-text-muted border-text-muted dark:bg-gray-500 dark:border-gray-500'
          : 'border-[1.5px] border-[#c4bfb7] dark:border-gray-600 hover:border-text-muted dark:hover:border-gray-500'
        }
        focus:outline-none focus-visible:ring-2 focus-visible:ring-text-muted/50 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900
      `}
    >
      {checked && (
        <svg
          className="w-2.5 h-2.5 text-white"
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

// Priority flag icon — matches flag shape used in Apple Reminders
function PriorityFlag({ priority }) {
  if (!priority || priority === 0) return null

  const colorClass =
    priority === 1 ? 'text-red-600 dark:text-red-400' :
    priority === 5 ? 'text-amber-500 dark:text-amber-400' :
    'text-text-secondary dark:text-gray-400'

  const label =
    priority === 1 ? 'High priority' :
    priority === 5 ? 'Medium priority' :
    'Low priority'

  return (
    <svg
      className={`w-[13px] h-[13px] ${colorClass} flex-shrink-0`}
      fill="currentColor"
      viewBox="0 0 24 24"
      aria-label={label}
    >
      <path d="M5 21V4h1c1 0 2.5.5 4 1.5S12.5 7 14 7c1.2 0 2.3-.3 3.3-.9.5-.3 1-.6 1.4-1 .2-.1.3-.2.3-.1v9c-.4.4-.9.7-1.4 1C16.3 15.7 15.2 16 14 16c-1.5 0-3-.5-4.5-1.5S7 13 6 13v8H5z" />
    </svg>
  )
}

export default function TaskItem({ task, onToggle, onEdit, onDelete, depth = 0, onToggleExpand, isExpanded }) {
  const isOverdue = task.due_date && !task.completed && new Date(task.due_date) < new Date()
  const memberColor = task.family_member?.color
  const isSystemMember = task.family_member?.is_system || task.family_member?.name === 'Everyone'
  const stripeColor = isSystemMember ? 'transparent' : (memberColor || 'transparent')
  const hasChildren = task.children && task.children.length > 0

  return (
    <SwipeableItem
      onSwipeAction={() => onDelete(task.id)}
      actionType="delete"
      actionLabel="Delete"
    >
      <div
        className={`
          group flex items-center gap-3 px-3 h-12
          border-b border-[#f0ece5] dark:border-gray-800
          border-r-[3px]
          transition-colors duration-75
          hover:bg-[#f7f4ee] dark:hover:bg-gray-800
          ${task.completed ? 'opacity-50' : ''}
        `}
        style={{
          borderRightColor: stripeColor,
          paddingLeft: `${12 + Math.min(depth, 2) * 24}px`,
        }}
        title={task.family_member && !isSystemMember ? `Assigned to ${task.family_member.name}` : undefined}
      >
        {/* Subtask expand/collapse chevron */}
        {hasChildren ? (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onToggleExpand?.(task.id) }}
            className="w-3 h-3 flex-shrink-0 text-text-muted hover:text-text-secondary transition-transform duration-150"
            style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}
            aria-label={isExpanded ? 'Collapse subtasks' : 'Expand subtasks'}
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z" />
            </svg>
          </button>
        ) : depth > 0 ? (
          <span className="w-3 flex-shrink-0" />
        ) : null}

        <CustomCheckbox
          checked={task.completed}
          onChange={() => onToggle(task.id)}
        />

        {/* Task title + priority flag */}
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span className={`
            text-[13px] font-medium truncate
            ${task.completed
              ? 'line-through text-text-muted dark:text-gray-500'
              : 'text-text-primary dark:text-gray-100'}
          `}>
            {task.title}
          </span>
          <PriorityFlag priority={task.priority} />
        </div>

        {/* Metadata: iCloud badge + due date chip */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {task.external_id && (
            task.sync_status === 'PENDING_PUSH' ? (
              <span className="text-[10px] text-text-muted dark:text-gray-500 italic">Syncing...</span>
            ) : (
              <svg className="w-3 h-3 text-text-muted dark:text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-label="Synced with iCloud">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
              </svg>
            )
          )}
          {task.due_date && (
            <span className={`
              inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium
              ${isOverdue
                ? 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/20'
                : 'text-text-secondary bg-warm-beige dark:text-gray-400 dark:bg-gray-800'}
            `}>
              {isOverdue ? (
                <svg className="w-[11px] h-[11px]" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-[11px] h-[11px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              )}
              {isOverdue && <span className="sr-only">Overdue: </span>}
              {formatDueDate(task.due_date)}
            </span>
          )}
        </div>

        {/* Action buttons — hover-reveal on desktop, always visible on mobile */}
        <div className="flex gap-px flex-shrink-0 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 transition-opacity duration-75">
          <button
            onClick={onEdit}
            className="
              w-[26px] h-[26px] flex items-center justify-center
              text-text-muted hover:text-text-secondary dark:hover:text-gray-300
              hover:bg-[#f0ece5] dark:hover:bg-gray-700
              rounded transition-colors duration-75
              focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500
            "
            aria-label={`Edit task: ${task.title}`}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            onClick={() => onDelete(task.id)}
            className="
              w-[26px] h-[26px] flex items-center justify-center
              text-text-muted hover:text-red-600 dark:hover:text-red-400
              hover:bg-[#f0ece5] dark:hover:bg-gray-700
              rounded transition-colors duration-75
              focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500
            "
            aria-label={`Delete task: ${task.title}`}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </SwipeableItem>
  )
}
