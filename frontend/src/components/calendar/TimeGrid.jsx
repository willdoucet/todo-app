import { useState, useEffect, useRef } from 'react'
import { getTimeGridHours, getTimePosition, getEventHeight, getMemberColor } from './calendarUtils'

const HOUR_HEIGHT = 60 // px per hour
const hours = getTimeGridHours() // 6..22
const GRID_HEIGHT = hours.length * HOUR_HEIGHT // 17 hours * 60px = 1020px

/**
 * Vertical time axis with positioned events. 6am–10pm, 60px/hour.
 * @param {object} props
 * @param {object[]} props.events - CalendarEvent objects with start_time/end_time
 * @param {object[]} props.familyMembers
 * @param {function} [props.onQuickAddTask] - Called with (timeStr) when user picks "New Task"
 * @param {function} [props.onQuickAddEvent] - Called with (timeStr) when user picks "New Event"
 * @param {boolean} [props.showHourLabels=true] - Show hour labels in left gutter
 */
export default function TimeGrid({ events, familyMembers, onQuickAddTask, onQuickAddEvent, onEditEvent, showHourLabels = true }) {
  const membersById = Object.fromEntries((familyMembers || []).map((m) => [m.id, m]))
  const hasQuickAdd = onQuickAddTask || onQuickAddEvent

  // Filter to timed events only (exclude all-day)
  const timedEvents = (events || []).filter((e) => e.start_time && !e.all_day)

  // Simple overlap layout: group overlapping events into columns
  const positioned = layoutEvents(timedEvents)

  // Quick-add choice state
  const [quickAdd, setQuickAdd] = useState(null) // { time, top }
  const quickAddRef = useRef(null)

  // Close quick-add on outside click
  useEffect(() => {
    if (!quickAdd) return
    function handleClickOutside(e) {
      if (quickAddRef.current && !quickAddRef.current.contains(e.target)) {
        setQuickAdd(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [quickAdd])

  function handleGridClick(e) {
    if (!hasQuickAdd) return
    const rect = e.currentTarget.getBoundingClientRect()
    const y = e.clientY - rect.top
    const minutesFromStart = (y / GRID_HEIGHT) * hours.length * 60
    const totalMinutes = 6 * 60 + minutesFromStart // 6am base
    const hour = Math.floor(totalMinutes / 60)
    const min = Math.round((totalMinutes % 60) / 15) * 15 // snap to 15min
    const timeStr = `${String(hour).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`
    setQuickAdd({ time: timeStr, top: y })
  }

  return (
    <div className="flex" style={{ height: GRID_HEIGHT }}>
      {/* Hour labels gutter */}
      {showHourLabels && (
        <div className="w-12 shrink-0 relative">
          {hours.map((h) => (
            <div
              key={h}
              className="absolute text-xs text-text-muted dark:text-gray-500 -translate-y-1/2"
              style={{ top: (h - 6) * HOUR_HEIGHT }}
            >
              {formatHour(h)}
            </div>
          ))}
        </div>
      )}

      {/* Grid area */}
      <div
        className="flex-1 relative border-l border-card-border dark:border-gray-700 cursor-pointer"
        onClick={handleGridClick}
      >
        {/* Hour lines */}
        {hours.map((h) => (
          <div
            key={h}
            className="absolute w-full border-t border-card-border/50 dark:border-gray-700/50"
            style={{ top: (h - 6) * HOUR_HEIGHT }}
          />
        ))}

        {/* Events */}
        {positioned.map(({ event, column, totalColumns }) => {
          const member = membersById[event.assigned_to] || event.family_member
          const color = getMemberColor(member)
          const top = (getTimePosition(event.start_time) / 100) * GRID_HEIGHT
          const height = (getEventHeight(event.start_time, event.end_time) / 100) * GRID_HEIGHT
          const width = `${(1 / totalColumns) * 100}%`
          const left = `${(column / totalColumns) * 100}%`

          return (
            <div
              key={event.id}
              className={`absolute rounded-md px-1.5 py-0.5 text-xs overflow-hidden ${onEditEvent ? 'cursor-pointer hover:brightness-90' : ''}`}
              style={{
                top,
                height: Math.max(height, 20),
                width,
                left,
                backgroundColor: color + '33',
                borderLeft: `3px solid ${color}`,
              }}
              title={`${event.title} (${event.start_time}–${event.end_time})`}
              onClick={onEditEvent ? (e) => { e.stopPropagation(); onEditEvent(event) } : undefined}
            >
              <div className="font-medium text-text-primary dark:text-gray-200 truncate">
                {event.title}
              </div>
              <div className="text-text-muted dark:text-gray-500">
                {event.start_time}–{event.end_time}
              </div>
            </div>
          )
        })}

        {/* Quick-add choice popup */}
        {quickAdd && (
          <div
            ref={quickAddRef}
            className="absolute z-50 w-40 rounded-xl bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 shadow-lg p-1.5"
            style={{ top: quickAdd.top, left: '50%', transform: 'translateX(-50%)' }}
          >
            {onQuickAddTask && (
              <button
                onClick={() => { onQuickAddTask(quickAdd.time); setQuickAdd(null) }}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-text-primary dark:text-gray-200 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
              >
                <svg className="w-4 h-4 text-terracotta-500 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
                New Task
              </button>
            )}
            {onQuickAddEvent && (
              <button
                onClick={() => { onQuickAddEvent(quickAdd.time); setQuickAdd(null) }}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-text-primary dark:text-gray-200 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
              >
                <svg className="w-4 h-4 text-terracotta-500 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                New Event
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function formatHour(h) {
  if (h === 0 || h === 24) return '12 AM'
  if (h === 12) return '12 PM'
  return h < 12 ? `${h} AM` : `${h - 12} PM`
}

/**
 * Simple equal-width column layout for overlapping events.
 * Returns array of { event, column, totalColumns }.
 */
function layoutEvents(events) {
  if (events.length === 0) return []

  // Sort by start_time, then by end_time
  const sorted = [...events].sort((a, b) => {
    if (a.start_time < b.start_time) return -1
    if (a.start_time > b.start_time) return 1
    if (a.end_time < b.end_time) return -1
    if (a.end_time > b.end_time) return 1
    return 0
  })

  // Group overlapping events
  const groups = []
  let currentGroup = [sorted[0]]

  for (let i = 1; i < sorted.length; i++) {
    const event = sorted[i]
    const groupEnd = currentGroup.reduce(
      (max, e) => (e.end_time > max ? e.end_time : max),
      currentGroup[0].end_time
    )
    if (event.start_time < groupEnd) {
      currentGroup.push(event)
    } else {
      groups.push(currentGroup)
      currentGroup = [event]
    }
  }
  groups.push(currentGroup)

  // Assign columns within each group
  const result = []
  for (const group of groups) {
    const totalColumns = group.length
    group.forEach((event, column) => {
      result.push({ event, column, totalColumns })
    })
  }

  return result
}
