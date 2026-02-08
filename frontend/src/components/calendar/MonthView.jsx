import { useMemo } from 'react'
import { getMonthGrid, formatDateKey, groupByDate, getMemberColor } from './calendarUtils'
import MonthDayPopover from './MonthDayPopover'
import QuickAddPopover from './QuickAddPopover'
import MobileDayList from './MobileDayList'

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MAX_DOTS = 4

/**
 * Month grid view with colored dots for items.
 * Desktop: click day → popover. Mobile: tap day → split view with MobileDayList below.
 */
export default function MonthView({
  currentDate,
  tasks,
  events,
  familyMembers,
  selectedDate,
  onSelectDate,
  onViewDay,
  onQuickAddTask,
  onQuickAddEvent,
  onEditTask,
  onEditEvent,
  onToggleComplete,
  isMobile,
}) {
  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()
  const grid = useMemo(() => getMonthGrid(year, month), [year, month])
  const tasksByDate = useMemo(() => groupByDate(tasks || [], 'due_date'), [tasks])
  const eventsByDate = useMemo(() => groupByDate(events || [], 'date'), [events])
  const membersById = useMemo(
    () => Object.fromEntries((familyMembers || []).map((m) => [m.id, m])),
    [familyMembers]
  )

  const todayKey = formatDateKey(new Date())
  const selectedKey = selectedDate ? formatDateKey(selectedDate) : null

  return (
    <div>
      {/* Day-of-week headers */}
      <div className="grid grid-cols-7 mb-1">
        {DAY_NAMES.map((name) => (
          <div
            key={name}
            className="text-center text-xs font-medium text-text-muted dark:text-gray-500 py-1"
          >
            {isMobile ? name[0] : name}
          </div>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-7 border border-card-border dark:border-gray-700 rounded-lg overflow-hidden">
        {grid.flat().map((date, i) => {
          const dateKey = formatDateKey(date)
          const isCurrentMonth = date.getMonth() === month
          const isToday = dateKey === todayKey
          const isSelected = dateKey === selectedKey
          const dayTasks = tasksByDate[dateKey] || []
          const dayEvents = eventsByDate[dateKey] || []
          const allItems = [...dayEvents, ...dayTasks]

          // Collect unique colors for dots
          const dotColors = []
          const seen = new Set()
          for (const item of allItems) {
            const memberId = item.assigned_to
            const member = membersById[memberId] || item.family_member
            const color = getMemberColor(member)
            if (!seen.has(color)) {
              seen.add(color)
              dotColors.push(color)
            }
            if (dotColors.length >= MAX_DOTS) break
          }
          const overflow = allItems.length - MAX_DOTS

          const cellContent = (
            <div
              className={`${isMobile ? 'min-h-[44px] p-1' : 'min-h-[80px] p-1.5'} border-b border-r border-card-border/50 dark:border-gray-700/50 transition-colors ${
                !isCurrentMonth
                  ? 'bg-warm-beige/50 dark:bg-gray-900/50'
                  : 'bg-card-bg dark:bg-gray-800'
              } ${isSelected && isMobile ? 'bg-peach-100 dark:bg-blue-900/30' : ''} hover:bg-warm-sand/50 dark:hover:bg-gray-700/50`}
              onClick={isMobile ? () => onSelectDate(date) : undefined}
            >
              {/* Day number */}
              <div className="flex justify-center mb-0.5">
                <span
                  className={`${isMobile ? 'w-6 h-6 text-xs' : 'w-7 h-7 text-sm'} flex items-center justify-center rounded-full font-medium ${
                    isToday
                      ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                      : isCurrentMonth
                        ? 'text-text-primary dark:text-gray-200'
                        : 'text-text-muted dark:text-gray-600'
                  }`}
                >
                  {date.getDate()}
                </span>
              </div>

              {/* Colored dots */}
              {dotColors.length > 0 && (
                <div className="flex items-center justify-center gap-0.5 flex-wrap">
                  {dotColors.map((color, j) => (
                    <span
                      key={j}
                      className={`rounded-full ${isMobile ? 'w-1 h-1' : 'w-1.5 h-1.5'}`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                  {overflow > 0 && (
                    <span className="text-[9px] text-text-muted dark:text-gray-500 leading-none">
                      +{overflow}
                    </span>
                  )}
                </div>
              )}
            </div>
          )

          // Desktop: days with items → MonthDayPopover; empty days → QuickAddPopover.
          // Mobile: just the cell (tap selects, MobileDayList shown below).
          if (!isMobile && allItems.length > 0) {
            return (
              <MonthDayPopover
                key={i}
                date={date}
                tasks={dayTasks}
                events={dayEvents}
                familyMembers={familyMembers}
                onViewDay={onViewDay}
                onQuickAddTask={onQuickAddTask}
                onQuickAddEvent={onQuickAddEvent}
                onEditTask={onEditTask}
                onEditEvent={onEditEvent}
                onToggleComplete={onToggleComplete}
              >
                {cellContent}
              </MonthDayPopover>
            )
          }

          if (!isMobile) {
            return (
              <QuickAddPopover
                key={i}
                onNewTask={() => onQuickAddTask(date)}
                onNewEvent={() => onQuickAddEvent(date)}
              >
                {cellContent}
              </QuickAddPopover>
            )
          }

          return <div key={i}>{cellContent}</div>
        })}
      </div>

      {/* Mobile: selected day detail list */}
      {isMobile && selectedDate && (
        <div className="mt-3 rounded-xl bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 px-3">
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
