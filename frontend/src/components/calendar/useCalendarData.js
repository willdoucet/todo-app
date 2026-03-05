import { useState, useEffect, useCallback, useMemo } from 'react'
import axios from 'axios'
import { convertEventForDisplay } from './calendarUtils'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Hook for fetching calendar data (tasks, events, family members) for a date range.
 *
 * @param {string} startDate - YYYY-MM-DD
 * @param {string} endDate - YYYY-MM-DD
 * @param {Set<number>} [activeMembers] - Set of family member IDs to show (null = all)
 */
export default function useCalendarData(startDate, endDate, activeMembers = null) {
  const [tasks, setTasks] = useState([])
  const [events, setEvents] = useState([])
  const [familyMembers, setFamilyMembers] = useState([])
  const [calendars, setCalendars] = useState([])
  const [displayTimezone, setDisplayTimezone] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Pad query range ±1 day to catch events that shift dates after tz conversion
  const paddedRange = useMemo(() => {
    if (!startDate || !endDate) return { start: startDate, end: endDate }
    const s = new Date(startDate + 'T00:00:00')
    const e = new Date(endDate + 'T00:00:00')
    s.setDate(s.getDate() - 1)
    e.setDate(e.getDate() + 1)
    const pad = (d) => d.toISOString().slice(0, 10)
    return { start: pad(s), end: pad(e) }
  }, [startDate, endDate])

  const fetchData = useCallback(async () => {
    if (!paddedRange.start || !paddedRange.end) return
    setLoading(true)
    setError(null)

    try {
      const [tasksRes, eventsRes, membersRes, settingsRes, calendarsRes] = await Promise.all([
        axios.get(`${API_BASE}/tasks?start_date=${startDate}&end_date=${endDate}`),
        axios.get(`${API_BASE}/calendar-events?start_date=${paddedRange.start}&end_date=${paddedRange.end}`),
        axios.get(`${API_BASE}/family-members`),
        axios.get(`${API_BASE}/app-settings/`),
        axios.get(`${API_BASE}/calendars/`),
      ])
      setTasks(tasksRes.data)
      setEvents(eventsRes.data)
      setFamilyMembers(membersRes.data)
      setDisplayTimezone(settingsRes.data.timezone || 'UTC')
      setCalendars(calendarsRes.data)
    } catch (err) {
      console.error('Error fetching calendar data:', err)
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, paddedRange.start, paddedRange.end])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Auto-refetch while any event has PENDING_PUSH (iCloud sync in progress).
  // The Celery push task runs ~30s after save; poll every 10s until resolved.
  useEffect(() => {
    const hasPending = events.some((e) => e.sync_status === 'PENDING_PUSH')
    if (!hasPending) return

    const timer = setTimeout(fetchData, 10000)
    return () => clearTimeout(timer)
  }, [events, fetchData])

  // Client-side filtering by active members
  const filteredTasks = activeMembers
    ? tasks.filter((t) => t.assigned_to === null || activeMembers.has(t.assigned_to))
    : tasks

  const filteredEvents = activeMembers
    ? events.filter((e) => e.assigned_to === null || activeMembers.has(e.assigned_to))
    : events

  // Convert events to display timezone
  const displayEvents = useMemo(() => {
    if (!displayTimezone) return filteredEvents
    return filteredEvents.map((e) => convertEventForDisplay(e, displayTimezone))
  }, [filteredEvents, displayTimezone])

  return {
    tasks: filteredTasks,
    events: filteredEvents,
    displayEvents,
    displayTimezone,
    familyMembers,
    calendars,
    loading,
    error,
    refetch: fetchData,
  }
}
