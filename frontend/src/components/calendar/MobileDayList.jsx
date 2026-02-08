import CalendarItem from './CalendarItem'
import { formatDateKey } from './calendarUtils'

/**
 * Full list of tasks and events for a single day — used in mobile split views.
 */
export default function MobileDayList({ tasks, events, date, familyMembers, onQuickAddTask, onQuickAddEvent, onEditTask, onEditEvent, onToggleComplete }) {
  const dateKey = formatDateKey(date)
  const membersById = Object.fromEntries((familyMembers || []).map((m) => [m.id, m]))

  const dayTasks = (tasks || []).filter((t) => {
    if (!t.due_date) return false
    return String(t.due_date).slice(0, 10) === dateKey
  })

  const dayEvents = (events || []).filter((e) => {
    return String(e.date).slice(0, 10) === dateKey
  })

  const isEmpty = dayTasks.length === 0 && dayEvents.length === 0

  return (
    <div className="py-3">
      <div className="flex items-center justify-between mb-2 px-1">
        <h3 className="text-sm font-semibold text-text-primary dark:text-gray-200">
          {date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
        </h3>
        {(onQuickAddTask || onQuickAddEvent) && (
          <div className="flex gap-1">
            {onQuickAddTask && (
              <button
                onClick={() => onQuickAddTask(date)}
                className="p-1.5 rounded-lg text-terracotta-500 dark:text-blue-400 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
                title="New Task"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            )}
            {onQuickAddEvent && (
              <button
                onClick={() => onQuickAddEvent(date)}
                className="p-1.5 rounded-lg text-terracotta-500 dark:text-blue-400 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
                title="New Event"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>

      {isEmpty ? (
        <p className="text-sm text-text-muted dark:text-gray-500 px-1">No events or tasks</p>
      ) : (
        <div className="space-y-0.5">
          {dayEvents.map((event) => (
            <CalendarItem
              key={`event-${event.id}`}
              item={event}
              type="event"
              member={membersById[event.assigned_to] || event.family_member}
              onClick={onEditEvent ? () => onEditEvent(event) : undefined}
            />
          ))}
          {dayTasks.map((task) => (
            <CalendarItem
              key={`task-${task.id}`}
              item={task}
              type="task"
              member={membersById[task.assigned_to] || task.family_member}
              onClick={onEditTask ? () => onEditTask(task) : undefined}
              onToggleComplete={onToggleComplete}
            />
          ))}
        </div>
      )}
    </div>
  )
}
