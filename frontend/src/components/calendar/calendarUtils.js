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
