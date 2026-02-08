import { Popover, PopoverButton, PopoverPanel } from '@headlessui/react'
import CalendarItem from './CalendarItem'

/**
 * Desktop popover that appears when clicking a day in MonthView.
 * Shows full task/event list for that day with "View full day" link.
 */
export default function MonthDayPopover({
  date,
  tasks,
  events,
  familyMembers,
  onViewDay,
  onQuickAddTask,
  onQuickAddEvent,
  onEditTask,
  onEditEvent,
  onToggleComplete,
  children,
}) {
  const membersById = Object.fromEntries((familyMembers || []).map((m) => [m.id, m]))
  const dateLabel = date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })

  return (
    <Popover className="relative">
      <PopoverButton as="div" className="cursor-pointer w-full">
        {children}
      </PopoverButton>

      <PopoverPanel
        anchor="bottom"
        className="z-50 w-72 rounded-xl bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 shadow-lg p-3"
      >
        {({ close }) => (
          <>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-text-primary dark:text-gray-100">
                {dateLabel}
              </h4>
              <div className="flex items-center gap-2">
                {(onQuickAddTask || onQuickAddEvent) && (
                  <div className="flex gap-1">
                    {onQuickAddTask && (
                      <button
                        onClick={() => onQuickAddTask(date)}
                        className="p-1 rounded-md text-terracotta-500 dark:text-blue-400 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
                        title="New Task"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                      </button>
                    )}
                  </div>
                )}
                {onViewDay && (
                  <button
                    onClick={() => onViewDay(date)}
                    className="text-xs text-terracotta-500 dark:text-blue-400 hover:underline"
                  >
                    View full day
                  </button>
                )}
              </div>
            </div>

            {tasks.length === 0 && events.length === 0 ? (
              <p className="text-xs text-text-muted dark:text-gray-500">No events or tasks</p>
            ) : (
              <div className="space-y-0.5 max-h-60 overflow-y-auto">
                {events.map((event) => (
                  <CalendarItem
                    key={`event-${event.id}`}
                    item={event}
                    type="event"
                    member={membersById[event.assigned_to] || event.family_member}
                    onClick={onEditEvent ? () => { close(); onEditEvent(event) } : undefined}
                  />
                ))}
                {tasks.map((task) => (
                  <CalendarItem
                    key={`task-${task.id}`}
                    item={task}
                    type="task"
                    member={membersById[task.assigned_to] || task.family_member}
                    onClick={onEditTask ? () => { close(); onEditTask(task) } : undefined}
                    onToggleComplete={onToggleComplete}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </PopoverPanel>
    </Popover>
  )
}
