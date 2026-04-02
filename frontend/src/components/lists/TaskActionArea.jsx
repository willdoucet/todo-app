// Bordered action area container — "Crisp Defined" variant
// Contains: indicator chips (priority, date, iCloud) | separator | action buttons (delete, save/cancel, expand)

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

function DueDateChip({ dueDate, isOverdue }) {
  if (!dueDate) return null
  return (
    <span className={`
      inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[11px] font-medium border
      text-text-secondary bg-white border-card-border dark:text-gray-400 dark:bg-gray-700 dark:border-gray-600
    `}>
      {isOverdue ? (
        <svg className="w-[11px] h-[11px] text-red-500 dark:text-red-400" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
        </svg>
      ) : (
        <svg className="w-[11px] h-[11px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      )}
      {isOverdue && <span className="sr-only">Overdue: </span>}
      {formatDueDate(dueDate)}
    </span>
  )
}

function ICloudBadge({ task }) {
  if (!task.external_id) return null
  if (task.sync_status === 'PENDING_PUSH') {
    return <span className="text-[10px] text-text-muted dark:text-gray-500 italic">Syncing...</span>
  }
  return (
    <svg className="w-3 h-3 text-text-muted dark:text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-label="Synced with iCloud">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
    </svg>
  )
}

export default function TaskActionArea({
  task,
  isEditing,
  isEmptyTitle,
  isDetailsExpanded,
  onDelete,
  onSave,
  onCancel,
  onToggleDetails,
}) {
  const isOverdue = task.due_date && !task.completed && new Date(task.due_date) < new Date()

  return (
    <div className="flex items-center gap-0.5 flex-shrink-0 py-1 px-1.5 bg-[#f8f6f1] dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-lg">
      {/* Indicators */}
      <PriorityFlag priority={task.priority} />
      <DueDateChip dueDate={task.due_date} isOverdue={isOverdue} />

      {/* Divider between task indicators and iCloud badge */}
      {task.external_id && (task.priority > 0 || task.due_date) && (
        <div className="w-px h-4 bg-card-border dark:bg-gray-600 mx-0.5 flex-shrink-0" />
      )}
      <ICloudBadge task={task} />

      {/* Separator before action buttons — only when indicators are present */}
      {(task.priority > 0 || task.due_date || task.external_id) && (
        <div className="w-px h-5 bg-card-border dark:bg-gray-600 mx-1 flex-shrink-0" />
      )}

      {/* Delete button — always visible */}
      <button
        type="button"
        onClick={() => onDelete(task.id)}
        className="
          w-[26px] h-[26px] flex items-center justify-center
          text-text-muted hover:text-red-600 dark:hover:text-red-400
          hover:bg-red-50 dark:hover:bg-red-900/20
          rounded transition-colors duration-75
          focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500
          sm:min-h-0 sm:min-w-0 min-h-[44px] min-w-[44px]
        "
        aria-label={`Delete task: ${task.title}`}
      >
        <svg className="w-[13px] h-[13px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>

      {/* Save/Cancel — visible when editing */}
      {isEditing && (
        <div className="flex gap-0.5">
          <button
            type="button"
            onClick={isEmptyTitle ? () => onDelete(task.id) : onSave}
            className={`
              px-2.5 py-1 text-[11px] font-semibold rounded
              transition-colors duration-75
              focus:outline-none focus-visible:ring-2
              sm:min-h-0 min-h-[44px]
              ${isEmptyTitle
                ? 'bg-red-500 dark:bg-red-600 text-white hover:bg-red-600 dark:hover:bg-red-700 focus-visible:ring-red-500'
                : 'bg-terracotta-500 dark:bg-blue-600 text-white hover:bg-terracotta-600 dark:hover:bg-blue-700 focus-visible:ring-terracotta-500'}
            `}
            aria-label={isEmptyTitle ? 'Delete task' : 'Save task'}
          >
            {isEmptyTitle ? 'Delete' : 'Save'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="
              px-2 py-1 text-[11px] font-medium rounded
              bg-white dark:bg-gray-700 text-text-muted dark:text-gray-400
              border border-card-border dark:border-gray-600
              hover:bg-warm-beige dark:hover:bg-gray-600 hover:text-text-secondary dark:hover:text-gray-300
              transition-colors duration-75
              focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500
              sm:min-h-0 min-h-[44px]
            "
          >
            Cancel
          </button>
        </div>
      )}

      {/* Expand/contract chevron */}
      <button
        type="button"
        onClick={onToggleDetails}
        className={`
          w-[26px] h-[26px] flex items-center justify-center
          rounded transition-all duration-200
          focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500
          sm:min-h-0 sm:min-w-0 min-h-[44px] min-w-[44px]
          ${isDetailsExpanded
            ? 'bg-terracotta-500 dark:bg-blue-600 text-white hover:bg-terracotta-600 dark:hover:bg-blue-700'
            : 'text-text-muted dark:text-gray-500 hover:bg-card-border dark:hover:bg-gray-700 hover:text-text-secondary dark:hover:text-gray-300'}
        `}
        aria-expanded={isDetailsExpanded}
        aria-label={isDetailsExpanded ? 'Hide details' : 'Show details'}
      >
        <svg
          className="w-[13px] h-[13px] transition-transform duration-250"
          style={{ transform: isDetailsExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>
  )
}
