import { useState, useMemo } from 'react'
import { getWeekDates, formatDateKey } from './calendarUtils'

/**
 * Hook for calendar navigation state: current date, view mode, and computed date range.
 */
export default function useCalendarNavigation() {
  const [currentDate, setCurrentDate] = useState(() => new Date())
  const [viewMode, setViewMode] = useState('month') // 'month' | 'week' | 'day'
  const [selectedDate, setSelectedDate] = useState(() => new Date()) // for mobile split view

  const { startDate, endDate } = useMemo(() => {
    const d = new Date(currentDate)
    d.setHours(0, 0, 0, 0)

    if (viewMode === 'day') {
      return { startDate: formatDateKey(d), endDate: formatDateKey(d) }
    }

    if (viewMode === 'week') {
      const week = getWeekDates(d)
      return { startDate: formatDateKey(week[0]), endDate: formatDateKey(week[6]) }
    }

    // month: fetch the full 6-week grid range for padding days
    const year = d.getFullYear()
    const month = d.getMonth()
    const firstDay = new Date(year, month, 1)
    const startDow = firstDay.getDay()
    const gridStart = new Date(year, month, 1 - startDow)
    const gridEnd = new Date(gridStart)
    gridEnd.setDate(gridStart.getDate() + 41) // 6 rows * 7 days - 1
    return { startDate: formatDateKey(gridStart), endDate: formatDateKey(gridEnd) }
  }, [currentDate, viewMode])

  function goToday() {
    const today = new Date()
    setCurrentDate(today)
    setSelectedDate(today)
  }

  function goNext() {
    setCurrentDate((prev) => {
      const d = new Date(prev)
      if (viewMode === 'month') d.setMonth(d.getMonth() + 1)
      else if (viewMode === 'week') d.setDate(d.getDate() + 7)
      else d.setDate(d.getDate() + 1)
      return d
    })
  }

  function goPrev() {
    setCurrentDate((prev) => {
      const d = new Date(prev)
      if (viewMode === 'month') d.setMonth(d.getMonth() - 1)
      else if (viewMode === 'week') d.setDate(d.getDate() - 7)
      else d.setDate(d.getDate() - 1)
      return d
    })
  }

  function setView(mode) {
    setViewMode(mode)
  }

  function setDate(date) {
    setCurrentDate(date)
    setSelectedDate(date)
  }

  return {
    currentDate,
    viewMode,
    selectedDate,
    startDate,
    endDate,
    goToday,
    goNext,
    goPrev,
    setView,
    setDate,
    setSelectedDate,
  }
}
