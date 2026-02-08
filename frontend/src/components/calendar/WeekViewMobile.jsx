import { formatDateKey, groupByDate, getMemberColor } from './calendarUtils'
import MobileDayList from './MobileDayList'

const DAY_ABBREVS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

/**
 * Mobile week view: horizontal date strip + day list below for selected day.
 */
export default function WeekViewMobile({
  weekDates,
  tasks,
  events,
  familyMembers,
  selectedDate,
  onSelectDate,
  onQuickAddTask,
  onQuickAddEvent,
  onEditTask,
  onEditEvent,
  onToggleComplete,
}) {
  const todayKey = formatDateKey(new Date())
  const selectedKey = selectedDate ? formatDateKey(selectedDate) : null
  const tasksByDate = groupByDate(tasks || [], 'due_date')
  const eventsByDate = groupByDate(events || [], 'date')

  return (
    <div>
      {/* Date strip */}
      <div className="flex justify-between gap-1 mb-3">
        {weekDates.map((date, i) => {
          const dateKey = formatDateKey(date)
          const isToday = dateKey === todayKey
          const isSelected = dateKey === selectedKey
          const dayTasks = tasksByDate[dateKey] || []
          const dayEvents = eventsByDate[dateKey] || []
          const hasItems = dayTasks.length > 0 || dayEvents.length > 0

          return (
            <button
              key={i}
              onClick={() => onSelectDate(date)}
              className={`flex-1 flex flex-col items-center py-2 rounded-xl transition-colors ${
                isSelected
                  ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                  : 'bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700'
              }`}
            >
              <span className={`text-xs ${isSelected ? 'text-white/80' : 'text-text-muted dark:text-gray-500'}`}>
                {DAY_ABBREVS[i]}
              </span>
              <span
                className={`text-sm font-semibold mt-0.5 ${
                  isToday && !isSelected ? 'text-terracotta-500 dark:text-blue-400' : ''
                }`}
              >
                {date.getDate()}
              </span>
              {/* Dot indicator */}
              {hasItems && (
                <span
                  className={`w-1.5 h-1.5 rounded-full mt-0.5 ${
                    isSelected ? 'bg-white/80' : 'bg-terracotta-400 dark:bg-blue-400'
                  }`}
                />
              )}
            </button>
          )
        })}
      </div>

      {/* Day detail */}
      {selectedDate && (
        <div className="rounded-xl bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 px-3">
          <MobileDayList
            tasks={tasks}
            events={events}
            date={selectedDate}
            familyMembers={familyMembers}
            onQuickAddTask={onQuickAddTask}
            onQuickAddEvent={onQuickAddEvent}
            onEditTask={onEditTask}
            onEditEvent={onEditEvent}
            onToggleComplete={onToggleComplete}
          />
        </div>
      )}
    </div>
  )
}
