import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function TimezoneSettings() {
  const [timezone, setTimezone] = useState('')
  const [allTimezones, setAllTimezones] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null) // {type: 'success'|'error', message}

  useEffect(() => {
    Promise.all([
      axios.get(`${API_BASE}/app-settings/`),
      axios.get(`${API_BASE}/app-settings/timezones`),
    ])
      .then(([settingsRes, tzRes]) => {
        setTimezone(settingsRes.data.timezone)
        setAllTimezones(tzRes.data)
      })
      .catch((err) => {
        console.error('Failed to load timezone settings:', err)
        setFeedback({ type: 'error', message: 'Failed to load settings' })
      })
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!search) return allTimezones
    const lower = search.toLowerCase()
    return allTimezones.filter((tz) => tz.toLowerCase().includes(lower))
  }, [allTimezones, search])

  const handleSave = async () => {
    setSaving(true)
    setFeedback(null)
    try {
      const res = await axios.patch(`${API_BASE}/app-settings/`, { timezone })
      setTimezone(res.data.timezone)
      setFeedback({ type: 'success', message: 'Timezone saved. Re-sync calendars to update event times.' })
    } catch (err) {
      const detail = err.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : detail || 'Failed to save'
      setFeedback({ type: 'error', message: msg })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="text-sm text-text-muted dark:text-gray-400 py-4">
        Loading timezone settings...
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {feedback && (
        <div
          className={`p-3 rounded-lg text-sm border ${
            feedback.type === 'success'
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300'
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'
          }`}
        >
          {feedback.message}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1">
          Timezone
        </label>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search timezones..."
          className="w-full px-3 py-2 mb-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
        />
        <select
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          size={6}
          className="w-full px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
        >
          {filtered.map((tz) => (
            <option key={tz} value={tz}>
              {tz}
            </option>
          ))}
        </select>
        <p className="text-xs text-text-muted dark:text-gray-400 mt-1">
          Current: <span className="font-medium">{timezone}</span>
        </p>
      </div>

      <button
        type="button"
        onClick={handleSave}
        disabled={saving}
        className="px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? 'Saving...' : 'Save Timezone'}
      </button>
    </div>
  )
}
