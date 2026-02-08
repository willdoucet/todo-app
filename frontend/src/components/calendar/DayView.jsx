import { useMemo } from 'react'
import { formatDateKey, groupByDate } from './calendarUtils'
import AllDaySection from './AllDaySection'
import TimeGrid from './TimeGrid'

/**
 * Single-column day view with all-day task bars + time grid.
 * Works on both desktop and mobile (single column scales naturally).
 */
export default function DayView({ date, tasks, events, familyMembers, onQuickAddTask, onQuickAddEvent, onEditTask, onEditEvent, onToggleComplete }) {
  const dateKey = formatDateKey(date)
  const tasksByDate = useMemo(() => groupByDate(tasks || [], 'due_date'), [tasks])
  const eventsByDate = useMemo(() => groupByDate(events || [], 'date'), [events])

  const dayTasks = tasksByDate[dateKey] || []
  const dayEvents = eventsByDate[dateKey] || []

  return (
    <div>
      {/* All-day tasks */}
      <AllDaySection tasks={dayTasks} familyMembers={familyMembers} onEditTask={onEditTask} onToggleComplete={onToggleComplete} />

      {/* Time grid */}
      <div className="overflow-y-auto" style={{ maxHeight: 600 }}>
        <TimeGrid
          events={dayEvents}
          familyMembers={familyMembers}
          onQuickAddTask={onQuickAddTask ? (time) => onQuickAddTask(date, time) : undefined}
          onQuickAddEvent={onQuickAddEvent ? (time) => onQuickAddEvent(date, time) : undefined}
          onEditEvent={onEditEvent}
        />
      </div>

      {/* Empty state */}
      {dayTasks.length === 0 && dayEvents.length === 0 && (
        <p className="text-center text-sm text-text-muted dark:text-gray-500 py-8">
          No events or tasks for this day
        </p>
      )}
    </div>
  )
}
