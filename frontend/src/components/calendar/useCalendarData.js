import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'

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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    if (!startDate || !endDate) return
    setLoading(true)
    setError(null)

    try {
      const [tasksRes, eventsRes, membersRes] = await Promise.all([
        axios.get(`${API_BASE}/tasks?start_date=${startDate}&end_date=${endDate}`),
        axios.get(`${API_BASE}/calendar-events?start_date=${startDate}&end_date=${endDate}`),
        axios.get(`${API_BASE}/family-members`),
      ])
      setTasks(tasksRes.data)
      setEvents(eventsRes.data)
      setFamilyMembers(membersRes.data)
    } catch (err) {
      console.error('Error fetching calendar data:', err)
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Client-side filtering by active members
  const filteredTasks = activeMembers
    ? tasks.filter((t) => t.assigned_to === null || activeMembers.has(t.assigned_to))
    : tasks

  const filteredEvents = activeMembers
    ? events.filter((e) => e.assigned_to === null || activeMembers.has(e.assigned_to))
    : events

  return {
    tasks: filteredTasks,
    events: filteredEvents,
    familyMembers,
    loading,
    error,
    refetch: fetchData,
  }
}
