import {
  getMonthGrid,
  getWeekDates,
  getTimeGridHours,
  getTimePosition,
  getEventHeight,
  formatDateKey,
  getMemberColor,
  groupByDate,
} from '../../../src/components/calendar/calendarUtils'

describe('getMonthGrid', () => {
  it('returns 6 rows of 7 dates', () => {
    const grid = getMonthGrid(2026, 1) // February 2026
    expect(grid).toHaveLength(6)
    grid.forEach((row) => expect(row).toHaveLength(7))
  })

  it('starts each row on Sunday', () => {
    const grid = getMonthGrid(2026, 1)
    grid.forEach((row) => {
      expect(row[0].getDay()).toBe(0) // Sunday
    })
  })

  it('includes the first day of the month', () => {
    const grid = getMonthGrid(2026, 1) // Feb 2026
    const allDates = grid.flat()
    const hasFirstDay = allDates.some(
      (d) => d.getFullYear() === 2026 && d.getMonth() === 1 && d.getDate() === 1
    )
    expect(hasFirstDay).toBe(true)
  })

  it('includes padding days from adjacent months', () => {
    // Feb 2026 starts on Sunday, so row 0 col 0 is Feb 1.
    // Last cells will be from March.
    const grid = getMonthGrid(2026, 1)
    const lastRow = grid[5]
    const lastDate = lastRow[6]
    expect(lastDate.getMonth()).toBe(2) // March
  })

  it('returns 42 total dates', () => {
    const grid = getMonthGrid(2026, 0) // January 2026
    expect(grid.flat()).toHaveLength(42)
  })
})

describe('getWeekDates', () => {
  it('returns 7 dates', () => {
    const dates = getWeekDates(new Date(2026, 1, 7)) // Saturday Feb 7, 2026
    expect(dates).toHaveLength(7)
  })

  it('starts on Sunday', () => {
    const dates = getWeekDates(new Date(2026, 1, 11)) // Wednesday Feb 11
    expect(dates[0].getDay()).toBe(0) // Sunday
  })

  it('ends on Saturday', () => {
    const dates = getWeekDates(new Date(2026, 1, 11))
    expect(dates[6].getDay()).toBe(6) // Saturday
  })

  it('contains the input date', () => {
    const input = new Date(2026, 1, 11) // Wednesday
    const dates = getWeekDates(input)
    const hasInputDate = dates.some(
      (d) => d.getDate() === 11 && d.getMonth() === 1
    )
    expect(hasInputDate).toBe(true)
  })

  it('returns consecutive days', () => {
    const dates = getWeekDates(new Date(2026, 1, 7))
    for (let i = 1; i < dates.length; i++) {
      const diff = dates[i].getTime() - dates[i - 1].getTime()
      expect(diff).toBe(24 * 60 * 60 * 1000) // exactly 1 day
    }
  })
})

describe('getTimeGridHours', () => {
  it('returns hours 6 through 22', () => {
    const hours = getTimeGridHours()
    expect(hours[0]).toBe(6)
    expect(hours[hours.length - 1]).toBe(22)
  })

  it('returns 17 hours', () => {
    expect(getTimeGridHours()).toHaveLength(17)
  })
})

describe('getTimePosition', () => {
  it('returns 0% for 6:00 (axis start)', () => {
    expect(getTimePosition('06:00')).toBe(0)
  })

  it('returns 100% for 22:00 (axis end)', () => {
    expect(getTimePosition('22:00')).toBe(100)
  })

  it('returns 50% for 14:00 (midpoint)', () => {
    expect(getTimePosition('14:00')).toBe(50)
  })

  it('clamps below 0% for times before 6am', () => {
    expect(getTimePosition('04:00')).toBe(0)
  })

  it('clamps above 100% for times after 10pm', () => {
    expect(getTimePosition('23:00')).toBe(100)
  })
})

describe('getEventHeight', () => {
  it('returns ~6.25% for a 1-hour event', () => {
    // 60 minutes / 960 total minutes * 100 = 6.25%
    expect(getEventHeight('09:00', '10:00')).toBeCloseTo(6.25)
  })

  it('returns ~12.5% for a 2-hour event', () => {
    expect(getEventHeight('09:00', '11:00')).toBeCloseTo(12.5)
  })

  it('returns 0 for zero-duration', () => {
    expect(getEventHeight('09:00', '09:00')).toBe(0)
  })
})

describe('formatDateKey', () => {
  it('formats as YYYY-MM-DD', () => {
    const date = new Date(2026, 1, 7) // Feb 7, 2026
    expect(formatDateKey(date)).toBe('2026-02-07')
  })

  it('zero-pads single-digit months and days', () => {
    const date = new Date(2026, 0, 5) // Jan 5
    expect(formatDateKey(date)).toBe('2026-01-05')
  })

  it('uses local time, not UTC', () => {
    // Create a date at 11 PM local — if it were using UTC this could shift to next day
    const date = new Date(2026, 1, 7, 23, 0, 0)
    expect(formatDateKey(date)).toBe('2026-02-07')
  })
})

describe('getMemberColor', () => {
  it('returns terracotta for system members', () => {
    expect(getMemberColor({ is_system: true, color: '#3B82F6' })).toBe('#D97452')
  })

  it('returns member color for normal members', () => {
    expect(getMemberColor({ is_system: false, color: '#3B82F6' })).toBe('#3B82F6')
  })

  it('returns gray for null member', () => {
    expect(getMemberColor(null)).toBe('#9CA3AF')
  })

  it('returns gray for member without color', () => {
    expect(getMemberColor({ is_system: false, color: null })).toBe('#9CA3AF')
  })
})

describe('groupByDate', () => {
  it('groups items by the specified date key', () => {
    const items = [
      { id: 1, due_date: '2026-02-07T10:00:00' },
      { id: 2, due_date: '2026-02-07T14:00:00' },
      { id: 3, due_date: '2026-02-08T09:00:00' },
    ]
    const result = groupByDate(items, 'due_date')
    expect(result['2026-02-07']).toHaveLength(2)
    expect(result['2026-02-08']).toHaveLength(1)
  })

  it('skips items without the date key', () => {
    const items = [
      { id: 1, due_date: '2026-02-07' },
      { id: 2, due_date: null },
      { id: 3 },
    ]
    const result = groupByDate(items, 'due_date')
    expect(result['2026-02-07']).toHaveLength(1)
    expect(Object.keys(result)).toHaveLength(1)
  })

  it('returns empty object for empty array', () => {
    expect(groupByDate([], 'date')).toEqual({})
  })

  it('works with date-only strings', () => {
    const items = [{ id: 1, date: '2026-02-07' }]
    const result = groupByDate(items, 'date')
    expect(result['2026-02-07']).toHaveLength(1)
  })
})
