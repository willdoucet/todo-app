import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import CalendarSelector from './CalendarSelector'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * iCloud Calendar integration management.
 *
 * States:
 * 1. No integrations — "Connect iCloud Calendar" card with form
 * 2. Step 1 — Credentials form (email + password + family member)
 * 3. Step 2 — Calendar selection (after validate)
 * 4. Connected — Status card per integration
 */
export default function ICloudSettings() {
  const [familyMembers, setFamilyMembers] = useState([])
  const [integrations, setIntegrations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Connection flow
  const [step, setStep] = useState(null) // null | 1 | 2
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedMember, setSelectedMember] = useState('')
  const [validating, setValidating] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [calendars, setCalendars] = useState([])
  const [selectedCalendars, setSelectedCalendars] = useState([])

  const pollRef = useRef(null)

  const loadIntegrations = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/integrations/`)
      setIntegrations(res.data)
    } catch (err) {
      console.error('Failed to load integrations:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Load integrations + family members on mount
  useEffect(() => {
    loadIntegrations()
    axios.get(`${API_BASE}/family-members`)
      .then((res) => setFamilyMembers(res.data))
      .catch((err) => console.error('Failed to load family members:', err))
  }, [loadIntegrations])

  // Poll while any integration is SYNCING
  useEffect(() => {
    const hasSyncing = integrations.some((i) => i.status === 'SYNCING')
    if (hasSyncing && !pollRef.current) {
      pollRef.current = setInterval(loadIntegrations, 3000)
    } else if (!hasSyncing && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [integrations, loadIntegrations])

  const resetFlow = () => {
    setStep(null)
    setEmail('')
    setPassword('')
    setSelectedMember('')
    setCalendars([])
    setSelectedCalendars([])
    setError(null)
  }

  // Step 1: Validate credentials
  const handleValidate = async (e) => {
    e.preventDefault()
    if (!email || !password || !selectedMember) return

    setValidating(true)
    setError(null)
    try {
      const res = await axios.post(`${API_BASE}/integrations/icloud/validate`, {
        email,
        password,
        family_member_id: parseInt(selectedMember),
      })
      setCalendars(res.data)
      setSelectedCalendars(res.data.filter((c) => !c.already_synced_by).map((c) => c.url))
      setStep(2)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to connect to iCloud. Check your email and app-specific password.')
    } finally {
      setValidating(false)
    }
  }

  // Step 2: Connect and start sync
  const handleConnect = async () => {
    if (selectedCalendars.length === 0) return

    setConnecting(true)
    setError(null)
    try {
      await axios.post(`${API_BASE}/integrations/icloud/connect`, {
        email,
        password,
        family_member_id: parseInt(selectedMember),
        selected_calendars: selectedCalendars,
      })
      resetFlow()
      await loadIntegrations()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to connect.')
    } finally {
      setConnecting(false)
    }
  }

  // Sync Now
  const handleSync = async (integrationId) => {
    try {
      await axios.post(`${API_BASE}/integrations/${integrationId}/sync`)
      await loadIntegrations()
    } catch (err) {
      console.error('Failed to trigger sync:', err)
    }
  }

  // Disconnect
  const handleDisconnect = async (integrationId) => {
    const confirmed = window.confirm(
      'This will delete all events synced from this account. Events created in Family Hub will also be removed from iCloud. Continue?'
    )
    if (!confirmed) return

    try {
      await axios.delete(`${API_BASE}/integrations/${integrationId}`)
      await loadIntegrations()
    } catch (err) {
      console.error('Failed to disconnect:', err)
    }
  }

  const nonSystemMembers = familyMembers.filter((m) => !m.is_system)

  if (loading) {
    return (
      <div className="text-sm text-text-muted dark:text-gray-400 py-4">
        Loading integrations...
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Connected integrations */}
      {integrations.map((integration) => (
        <IntegrationCard
          key={integration.id}
          integration={integration}
          onSync={() => handleSync(integration.id)}
          onDisconnect={() => handleDisconnect(integration.id)}
        />
      ))}

      {/* Connection flow */}
      {step === null && (
        <button
          type="button"
          onClick={() => setStep(1)}
          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-terracotta-600 dark:text-blue-400 hover:bg-terracotta-50 dark:hover:bg-blue-900/20 rounded-xl transition-colors border border-dashed border-terracotta-300 dark:border-blue-700 w-full justify-center"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Connect iCloud Calendar
        </button>
      )}

      {step === 1 && (
        <div className="border border-card-border dark:border-gray-700 rounded-xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text-primary dark:text-gray-200">
              Connect iCloud Calendar
            </h3>
            <button
              type="button"
              onClick={resetFlow}
              className="text-sm text-text-muted dark:text-gray-400 hover:text-text-primary dark:hover:text-gray-200"
            >
              Cancel
            </button>
          </div>

          <form onSubmit={handleValidate} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1">
                Family Member
              </label>
              <select
                value={selectedMember}
                onChange={(e) => setSelectedMember(e.target.value)}
                required
                className="w-full px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
              >
                <option value="">Select member...</option>
                {nonSystemMembers.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1">
                iCloud Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="name@icloud.com"
                className="w-full px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1">
                App-Specific Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="xxxx-xxxx-xxxx-xxxx"
                className="w-full px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
              />
              <a
                href="https://support.apple.com/en-us/102654"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-terracotta-500 dark:text-blue-400 hover:underline mt-1 inline-block"
              >
                How to generate an app-specific password
              </a>
            </div>

            <button
              type="submit"
              disabled={validating || !email || !password || !selectedMember}
              className="w-full px-4 py-2.5 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {validating ? 'Connecting...' : 'Connect'}
            </button>
          </form>
        </div>
      )}

      {step === 2 && (
        <div className="border border-card-border dark:border-gray-700 rounded-xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text-primary dark:text-gray-200">
              Select Calendars to Sync
            </h3>
            <button
              type="button"
              onClick={resetFlow}
              className="text-sm text-text-muted dark:text-gray-400 hover:text-text-primary dark:hover:text-gray-200"
            >
              Cancel
            </button>
          </div>

          <p className="text-xs text-text-muted dark:text-gray-400">
            Found {calendars.length} calendar{calendars.length !== 1 ? 's' : ''} for {email}
          </p>

          <CalendarSelector
            calendars={calendars}
            selected={selectedCalendars}
            onChange={setSelectedCalendars}
          />

          <button
            type="button"
            onClick={handleConnect}
            disabled={connecting || selectedCalendars.length === 0}
            className="w-full px-4 py-2.5 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {connecting ? 'Starting sync...' : 'Start Sync'}
          </button>
        </div>
      )}
    </div>
  )
}

function IntegrationCard({ integration, onSync, onDisconnect }) {
  const statusConfig = {
    ACTIVE: { label: 'Active', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
    SYNCING: { label: 'Syncing...', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
    ERROR: { label: 'Error', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
    DISCONNECTED: { label: 'Disconnected', color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400' },
  }

  const status = statusConfig[integration.status] || statusConfig.ACTIVE
  const memberName = integration.family_member?.name || 'Unknown'

  return (
    <div className="border border-card-border dark:border-gray-700 rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-text-primary dark:text-gray-200 truncate">
              {integration.email}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${status.color}`}>
              {status.label}
            </span>
          </div>
          <p className="text-xs text-text-muted dark:text-gray-400">
            {memberName} &middot; {integration.selected_calendars?.length || 0} calendar{(integration.selected_calendars?.length || 0) !== 1 ? 's' : ''}
          </p>
          {integration.last_sync_at && (
            <p className="text-xs text-text-muted dark:text-gray-400 mt-0.5">
              Last synced {relativeTime(integration.last_sync_at)}
            </p>
          )}
          {integration.status === 'ERROR' && integration.last_error && (
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">
              {integration.last_error}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={onSync}
            disabled={integration.status === 'SYNCING'}
            className="text-xs px-3 py-1.5 text-terracotta-600 dark:text-blue-400 hover:bg-terracotta-50 dark:hover:bg-blue-900/20 rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {integration.status === 'SYNCING' ? 'Syncing...' : 'Sync Now'}
          </button>
          <button
            type="button"
            onClick={onDisconnect}
            className="text-xs px-3 py-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg font-medium transition-colors"
          >
            Disconnect
          </button>
        </div>
      </div>
    </div>
  )
}

function relativeTime(isoString) {
  if (!isoString) return 'never'
  const now = new Date()
  const then = new Date(isoString)
  const diffMs = now - then
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin} min ago`

  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr} hr ago`

  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`
}
