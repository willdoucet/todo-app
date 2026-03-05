/**
 * Pure utility functions for calendar date math, positioning, and color resolution.
 */

/**
 * Build a 6x7 grid of Date objects for a given month, starting from Sunday.
 * Includes padding days from previous/next months.
 * @returns {Date[][]} 6 rows of 7 dates
 */
export function getMonthGrid(year, month) {
  const firstDay = new Date(year, month, 1)
  const startDow = firstDay.getDay() // 0=Sunday
  const gridStart = new Date(year, month, 1 - startDow)

  const rows = []
  const cursor = new Date(gridStart)
  for (let r = 0; r < 6; r++) {
    const row = []
    for (let c = 0; c < 7; c++) {
      row.push(new Date(cursor))
      cursor.setDate(cursor.getDate() + 1)
    }
    rows.push(row)
  }
  return rows
}

/**
 * Get 7 dates for the week containing `date`, starting from Sunday.
 * @param {Date} date
 * @returns {Date[]}
 */
export function getWeekDates(date) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  const dow = d.getDay() // 0=Sunday
  const sunday = new Date(d)
  sunday.setDate(d.getDate() - dow)

  const days = []
  for (let i = 0; i < 7; i++) {
    const day = new Date(sunday)
    day.setDate(sunday.getDate() + i)
    days.push(day)
  }
  return days
}

/**
 * Hours for the time-grid axis: 6am through 10pm.
 * @returns {number[]}
 */
export function getTimeGridHours() {
  const hours = []
  for (let h = 6; h <= 22; h++) {
    hours.push(h)
  }
  return hours
}

const AXIS_START = 6 // 6am
const AXIS_END = 22 // 10pm
const AXIS_MINUTES = (AXIS_END - AXIS_START) * 60 // 960

function timeToMinutes(timeStr) {
  const [h, m] = timeStr.split(':').map(Number)
  return h * 60 + m
}

/**
 * Vertical % position for "HH:MM" on the 6am-10pm axis.
 * Clamps to 0-100%.
 */
export function getTimePosition(timeStr) {
  const minutes = timeToMinutes(timeStr)
  const offset = minutes - AXIS_START * 60
  return Math.max(0, Math.min(100, (offset / AXIS_MINUTES) * 100))
}

/**
 * Height % for an event spanning startTime→endTime on the 6am-10pm axis.
 */
export function getEventHeight(startTime, endTime) {
  const startMin = timeToMinutes(startTime)
  const endMin = timeToMinutes(endTime)
  const duration = endMin - startMin
  return Math.max(0, (duration / AXIS_MINUTES) * 100)
}

/**
 * Format a Date to "YYYY-MM-DD" string for API calls and grouping.
 */
export function formatDateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const TERRACOTTA = '#D97452'
const GRAY = '#9CA3AF'

/**
 * Resolve display color for a family member.
 * - System members ("Everyone") → terracotta
 * - Assigned member with color → member.color
 * - Unassigned (null) → gray
 */
export function getMemberColor(member) {
  if (!member) return GRAY
  if (member.is_system) return TERRACOTTA
  return member.color || GRAY
}

/**
 * Group an array of items into a map keyed by date string.
 * @param {object[]} items
 * @param {string} dateKey - property name on each item that holds the date (e.g. 'due_date', 'date')
 * @returns {Object.<string, object[]>}
 */
export function groupByDate(items, dateKey) {
  const map = {}
  for (const item of items) {
    const raw = item[dateKey]
    if (!raw) continue
    // Normalize: take just the YYYY-MM-DD portion
    const key = String(raw).slice(0, 10)
    if (!map[key]) map[key] = []
    map[key].push(item)
  }
  return map
}

// ---------------------------------------------------------------------------
// Timezone conversion utilities
// ---------------------------------------------------------------------------

/**
 * Convert a time from one IANA timezone to another on a specific date.
 * Uses native Intl.DateTimeFormat — no external dependencies.
 *
 * @param {string} dateStr - "YYYY-MM-DD"
 * @param {string} timeStr - "HH:MM"
 * @param {string} fromTz  - IANA timezone (e.g. "America/Los_Angeles")
 * @param {string} toTz    - IANA timezone (e.g. "America/New_York")
 * @returns {{ date: string, time: string }} - converted date + time
 */
export function convertTime(dateStr, timeStr, fromTz, toTz) {
  if (!dateStr || !timeStr || !fromTz || !toTz || fromTz === toTz) {
    return { date: dateStr, time: timeStr }
  }

  const [year, month, day] = dateStr.split('-').map(Number)
  const [hour, minute] = timeStr.split(':').map(Number)

  // Build a Date in the source timezone by using formatToParts to find the
  // UTC offset, then construct a proper UTC timestamp.
  // Step 1: Create a rough UTC date (may be wrong by tz offset)
  const roughUtc = new Date(Date.UTC(year, month - 1, day, hour, minute))

  // Step 2: Find what the "fromTz" offset is at this rough time
  const fromOffset = getTimezoneOffsetMinutes(roughUtc, fromTz)

  // Step 3: Actual UTC = rough - offset (since offset is UTC→local, we subtract)
  const actualUtc = new Date(roughUtc.getTime() - fromOffset * 60000)

  // Step 4: Format in the target timezone
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: toTz,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(actualUtc)

  const p = {}
  for (const { type, value } of parts) {
    p[type] = value
  }

  const convertedDate = `${p.year}-${p.month}-${p.day}`
  // Handle midnight edge case: some locales format hour 0 as "24"
  const h = p.hour === '24' ? '00' : p.hour
  const convertedTime = `${h}:${p.minute}`

  return { date: convertedDate, time: convertedTime }
}

/**
 * Get the UTC offset in minutes for a timezone at a given instant.
 * Positive = ahead of UTC (e.g. +60 for CET), negative = behind (e.g. -300 for EST).
 */
function getTimezoneOffsetMinutes(utcDate, tz) {
  // Format the date in the target tz to extract components
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: tz,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(utcDate)

  const p = {}
  for (const { type, value } of parts) {
    p[type] = value
  }

  const h = p.hour === '24' ? 0 : Number(p.hour)
  const localInTz = new Date(
    Date.UTC(Number(p.year), Number(p.month) - 1, Number(p.day), h, Number(p.minute), Number(p.second))
  )

  // Offset = local representation - actual UTC (in minutes)
  return (localInTz.getTime() - utcDate.getTime()) / 60000
}

/**
 * Convert a calendar event's times for display in a target timezone.
 * All-day events and same-timezone events pass through unchanged.
 *
 * @param {object} event - calendar event with date, start_time, end_time, timezone, all_day
 * @param {string} displayTz - IANA timezone to display in
 * @returns {object} - new event object with converted date/times
 */
export function convertEventForDisplay(event, displayTz) {
  // All-day events have no timezone — pass through
  if (event.all_day || !event.timezone || !displayTz) {
    return event
  }

  // Same timezone — no conversion needed
  if (event.timezone === displayTz) {
    return event
  }

  const dateStr = String(event.date).slice(0, 10)
  let convertedDate = dateStr
  let convertedStart = event.start_time
  let convertedEnd = event.end_time

  if (event.start_time) {
    const result = convertTime(dateStr, event.start_time, event.timezone, displayTz)
    convertedDate = result.date
    convertedStart = result.time
  }

  if (event.end_time) {
    const result = convertTime(dateStr, event.end_time, event.timezone, displayTz)
    convertedEnd = result.time
    // Use the start_time's converted date (end_time date shift is rare and
    // would only matter for multi-day events which we don't support yet)
  }

  return {
    ...event,
    date: convertedDate,
    start_time: convertedStart,
    end_time: convertedEnd,
  }
}
