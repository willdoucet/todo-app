import { getMemberColor } from './calendarUtils'

/**
 * Horizontal bars for all-day tasks (or all-day events).
 * Used at the top of WeekViewDesktop columns and DayView.
 */
export default function AllDaySection({ tasks, familyMembers, onEditTask, onToggleComplete }) {
  if (!tasks || tasks.length === 0) return null

  const membersById = Object.fromEntries((familyMembers || []).map((m) => [m.id, m]))

  return (
    <div className="border-b border-card-border dark:border-gray-700 pb-1 mb-1 space-y-0.5">
      {tasks.map((task) => {
        const member = membersById[task.assigned_to] || task.family_member
        const color = getMemberColor(member)
        const isCompleted = task.completed

        return (
          <div
            key={task.id}
            className={`flex items-center gap-1 px-1.5 py-1 rounded text-xs ${
              isCompleted ? 'line-through opacity-50' : ''
            } ${onEditTask ? 'cursor-pointer hover:brightness-90' : ''}`}
            style={{
              backgroundColor: color + '33',
              borderLeft: `3px solid ${color}`,
            }}
            onClick={onEditTask ? () => onEditTask(task) : undefined}
          >
            {onToggleComplete && (
              <button
                type="button"
                className="shrink-0 p-0 bg-transparent border-none cursor-pointer"
                onClick={(e) => { e.stopPropagation(); onToggleComplete(task) }}
                aria-label={isCompleted ? 'Mark incomplete' : 'Mark complete'}
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke={color} strokeWidth={2}>
                  {isCompleted ? (
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  ) : (
                    <circle cx="12" cy="12" r="9" />
                  )}
                </svg>
              </button>
            )}
            <span className="text-text-primary dark:text-gray-200 truncate">{task.title}</span>
          </div>
        )
      })}
    </div>
  )
}
