import { useMemo } from 'react'
import { formatDateKey, groupByDate } from './calendarUtils'
import AllDaySection from './AllDaySection'
import TimeGrid from './TimeGrid'

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/**
 * 7-column time grid for desktop week view.
 * Each column has an AllDaySection (tasks) and a TimeGrid (events).
 */
export default function WeekViewDesktop({
  weekDates,
  tasks,
  events,
  familyMembers,
  onQuickAddTask,
  onQuickAddEvent,
  onEditTask,
  onEditEvent,
  onToggleComplete,
}) {
  const tasksByDate = useMemo(() => groupByDate(tasks || [], 'due_date'), [tasks])
  const eventsByDate = useMemo(() => groupByDate(events || [], 'date'), [events])
  const todayKey = formatDateKey(new Date())

  return (
    <div>
      {/* Day headers */}
      <div className="grid grid-cols-7 gap-0 pl-12">
        {weekDates.map((date, i) => {
          const dateKey = formatDateKey(date)
          const isToday = dateKey === todayKey

          return (
            <div key={i} className="text-center py-2 border-b border-card-border dark:border-gray-700">
              <div className="text-xs text-text-muted dark:text-gray-500">{DAY_NAMES[i]}</div>
              <div
                className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-medium ${
                  isToday
                    ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                    : 'text-text-primary dark:text-gray-200'
                }`}
              >
                {date.getDate()}
              </div>
            </div>
          )
        })}
      </div>

      {/* All-day section row */}
      <div className="grid grid-cols-7 gap-0 pl-12">
        {weekDates.map((date, i) => {
          const dateKey = formatDateKey(date)
          const dayTasks = tasksByDate[dateKey] || []

          return (
            <div key={i} className="border-r border-card-border/50 dark:border-gray-700/50 px-0.5">
              <AllDaySection tasks={dayTasks} familyMembers={familyMembers} onEditTask={onEditTask} onToggleComplete={onToggleComplete} />
            </div>
          )
        })}
      </div>

      {/* Time grid columns */}
      <div className="grid grid-cols-7 gap-0 overflow-y-auto" style={{ maxHeight: 600 }}>
        {weekDates.map((date, i) => {
          const dateKey = formatDateKey(date)
          const dayEvents = eventsByDate[dateKey] || []
          const isToday = dateKey === todayKey

          return (
            <div
              key={i}
              className={`border-r border-card-border/50 dark:border-gray-700/50 ${
                isToday ? 'bg-peach-100/10 dark:bg-blue-900/10' : ''
              }`}
            >
              <TimeGrid
                events={dayEvents}
                familyMembers={familyMembers}
                onQuickAddTask={onQuickAddTask ? (time) => onQuickAddTask(date, time) : undefined}
                onQuickAddEvent={onQuickAddEvent ? (time) => onQuickAddEvent(date, time) : undefined}
                onEditEvent={onEditEvent}
                showHourLabels={i === 0}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
