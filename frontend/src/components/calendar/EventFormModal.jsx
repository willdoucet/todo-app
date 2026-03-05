import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import axios from 'axios'
import { formatDateKey, convertTime } from './calendarUtils'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function extractErrorMessage(err, fallback) {
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
  }
  if (typeof detail === 'string') return detail
  return fallback
}

/**
 * Modal for creating/editing calendar events.
 * Follows AddMealModal Dialog pattern.
 */
export default function EventFormModal({
  isOpen,
  onClose,
  onSaved,
  initialEvent = null,
  defaultDate = null,
  defaultTime = null,
  familyMembers = [],
  calendars = [],
  displayTimezone = null,
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [date, setDate] = useState('')
  const [allDay, setAllDay] = useState(false)
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [assignedTo, setAssignedTo] = useState('')
  const [selectedCalendarId, setSelectedCalendarId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null) // 'save' | 'delete' | 'sync-to-icloud' | 'remove-from-icloud' | null

  // Whether the event's timezone differs from display timezone
  const hasTzDiff = initialEvent?.timezone && displayTimezone && initialEvent.timezone !== displayTimezone

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      if (initialEvent) {
        const rawDate = String(initialEvent.date).slice(0, 10)
        const rawStart = initialEvent.start_time || ''
        const rawEnd = initialEvent.end_time || ''

        // If event timezone differs from display timezone, convert for display
        if (hasTzDiff && rawStart) {
          const startConverted = convertTime(rawDate, rawStart, initialEvent.timezone, displayTimezone)
          const endConverted = rawEnd ? convertTime(rawDate, rawEnd, initialEvent.timezone, displayTimezone) : { date: rawDate, time: '' }
          setDate(startConverted.date)
          setStartTime(startConverted.time)
          setEndTime(endConverted.time)
        } else {
          setDate(rawDate)
          setStartTime(rawStart)
          setEndTime(rawEnd)
        }

        setTitle(initialEvent.title || '')
        setDescription(initialEvent.description || '')
        setAllDay(initialEvent.all_day || false)
        setAssignedTo(initialEvent.assigned_to ?? '')
        setSelectedCalendarId(initialEvent.calendar_id ?? '')
      } else {
        setTitle('')
        setDescription('')
        setDate(defaultDate ? formatDateKey(defaultDate) : formatDateKey(new Date()))
        setAllDay(false)
        setStartTime(defaultTime || '')
        setEndTime(defaultTime ? addOneHour(defaultTime) : '')
        setAssignedTo('')
        setSelectedCalendarId('')
      }
      setError(null)
      setConfirmAction(null)
    }
  }, [isOpen, initialEvent, defaultDate, defaultTime, hasTzDiff, displayTimezone])

  const isICloud = initialEvent?.source === 'ICLOUD'
  const calIdNum = selectedCalendarId ? parseInt(selectedCalendarId) : null
  const oldCalId = initialEvent?.calendar_id ?? null
  const isAddingToICloud = !oldCalId && calIdNum
  const isRemovingFromICloud = oldCalId && !calIdNum

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim()) return

    // Show confirmation for source transitions
    if (isAddingToICloud && confirmAction !== 'sync-to-icloud') {
      setConfirmAction('sync-to-icloud')
      return
    }
    if (isRemovingFromICloud && confirmAction !== 'remove-from-icloud') {
      setConfirmAction('remove-from-icloud')
      return
    }
    // Show confirmation for iCloud events before saving
    if (isICloud && !isAddingToICloud && !isRemovingFromICloud && confirmAction !== 'save') {
      setConfirmAction('save')
      return
    }
    setConfirmAction(null)

    setLoading(true)
    setError(null)

    // Build payload — convert times back to event timezone if needed
    let payloadDate = date
    let payloadStart = allDay ? null : startTime || null
    let payloadEnd = allDay ? null : endTime || null

    if (hasTzDiff && initialEvent && payloadStart) {
      const startBack = convertTime(date, payloadStart, displayTimezone, initialEvent.timezone)
      payloadDate = startBack.date
      payloadStart = startBack.time
      if (payloadEnd) {
        const endBack = convertTime(date, payloadEnd, displayTimezone, initialEvent.timezone)
        payloadEnd = endBack.time
      }
    }

    const payload = {
      title: title.trim(),
      description: description.trim() || null,
      date: payloadDate,
      all_day: allDay,
      start_time: payloadStart,
      end_time: payloadEnd,
      assigned_to: assignedTo ? parseInt(assignedTo) : null,
      calendar_id: calIdNum,
    }

    try {
      if (initialEvent) {
        await axios.patch(`${API_BASE}/calendar-events/${initialEvent.id}`, payload)
      } else {
        await axios.post(`${API_BASE}/calendar-events`, payload)
      }
      onSaved()
      onClose()
    } catch (err) {
      console.error('Error saving event:', err)
      setError(extractErrorMessage(err, 'Failed to save event'))
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!initialEvent) return

    // Show confirmation for iCloud events before deleting
    if (isICloud && confirmAction !== 'delete') {
      setConfirmAction('delete')
      return
    }
    setConfirmAction(null)

    setLoading(true)
    try {
      await axios.delete(`${API_BASE}/calendar-events/${initialEvent.id}`)
      onSaved()
      onClose()
    } catch (err) {
      console.error('Error deleting event:', err)
      setError(extractErrorMessage(err, 'Failed to delete event'))
    } finally {
      setLoading(false)
    }
  }

  const isEditable = !initialEvent || initialEvent.source !== 'GOOGLE'
  const isValid = title.trim().length > 0

  return (
    <Transition show={isOpen} as="div">
      <Dialog onClose={onClose} className="relative z-50">
        <Transition.Child
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30 dark:bg-black/50" />
        </Transition.Child>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="w-full max-w-lg rounded-2xl bg-card-bg dark:bg-gray-800 shadow-2xl">
              <form onSubmit={handleSubmit}>
                {/* Header */}
                <div className="px-6 py-4 border-b border-card-border dark:border-gray-700">
                  <Dialog.Title className="text-xl font-semibold text-text-primary dark:text-gray-100">
                    {initialEvent ? 'Edit Event' : 'New Event'}
                  </Dialog.Title>
                </div>

                {/* Body */}
                <div className="px-6 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
                  {/* iCloud sync badge */}
                  {isICloud && (
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
                        </svg>
                        Synced from iCloud
                      </span>
                      {initialEvent?.sync_status === 'PENDING_PUSH' && (
                        <span className="text-xs text-text-muted dark:text-gray-400 italic">
                          Syncing...
                        </span>
                      )}
                    </div>
                  )}

                  {/* Timezone info (read-only) */}
                  {hasTzDiff && (
                    <p className="text-xs text-text-muted dark:text-gray-400">
                      Event timezone: {initialEvent.timezone}
                    </p>
                  )}

                  {/* Confirmation banners */}
                  {confirmAction === 'sync-to-icloud' && (
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                      <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                        This event will be synced to iCloud Calendar. Continue?
                      </p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setConfirmAction(null)}
                          className="px-3 py-1.5 text-xs font-medium text-text-secondary dark:text-gray-300 hover:bg-white dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                        >
                          Sync to iCloud
                        </button>
                      </div>
                    </div>
                  )}

                  {confirmAction === 'remove-from-icloud' && (
                    <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                      <p className="text-sm text-amber-800 dark:text-amber-200 mb-2">
                        This event will be removed from iCloud Calendar but kept locally. Continue?
                      </p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setConfirmAction(null)}
                          className="px-3 py-1.5 text-xs font-medium text-text-secondary dark:text-gray-300 hover:bg-white dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors"
                        >
                          Remove from iCloud
                        </button>
                      </div>
                    </div>
                  )}

                  {confirmAction === 'save' && (
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                      <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                        This event is synced from iCloud. Your changes will be pushed back to iCloud Calendar. Continue?
                      </p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setConfirmAction(null)}
                          className="px-3 py-1.5 text-xs font-medium text-text-secondary dark:text-gray-300 hover:bg-white dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                        >
                          Save & Sync
                        </button>
                      </div>
                    </div>
                  )}

                  {confirmAction === 'delete' && (
                    <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                      <p className="text-sm text-red-800 dark:text-red-200 mb-2">
                        This will also delete the event from iCloud Calendar. This action cannot be undone. Continue?
                      </p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setConfirmAction(null)}
                          className="px-3 py-1.5 text-xs font-medium text-text-secondary dark:text-gray-300 hover:bg-white dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={handleDelete}
                          className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
                        >
                          Delete from both
                        </button>
                      </div>
                    </div>
                  )}

                  {error && (
                    <p className="text-sm text-red-500 dark:text-red-400">{error}</p>
                  )}

                  {/* Title */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Title <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      required
                      disabled={!isEditable}
                      placeholder="Event title"
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 disabled:opacity-50"
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Description
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={2}
                      disabled={!isEditable}
                      placeholder="Optional description"
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 resize-none disabled:opacity-50"
                    />
                  </div>

                  {/* Calendar (iCloud sync target) */}
                  {calendars.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                        Calendar
                      </label>
                      <select
                        value={selectedCalendarId}
                        onChange={(e) => setSelectedCalendarId(e.target.value)}
                        disabled={!isEditable}
                        className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 disabled:opacity-50"
                      >
                        <option value="">App only (no sync)</option>
                        {calendars.map((cal) => {
                          // Disable cross-integration calendars when editing iCloud events
                          const isCrossIntegration = isICloud && initialEvent?.calendar_integration_id &&
                            cal.calendar_integration_id !== initialEvent.calendar_integration_id
                          return (
                            <option
                              key={cal.id}
                              value={cal.id}
                              disabled={isCrossIntegration}
                            >
                              {cal.name} ({cal.family_member_name}'s iCloud)
                            </option>
                          )
                        })}
                      </select>
                    </div>
                  )}

                  {/* Date */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Date <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="date"
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                      required
                      disabled={!isEditable}
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 disabled:opacity-50"
                    />
                  </div>

                  {/* All Day Toggle */}
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-text-primary dark:text-gray-200">
                      All Day
                    </label>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={allDay}
                      disabled={!isEditable}
                      onClick={() => setAllDay(!allDay)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-terracotta-500 focus:ring-offset-2 disabled:opacity-50 ${
                        allDay ? 'bg-terracotta-500 dark:bg-blue-600' : 'bg-warm-sand dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          allDay ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  {/* Time inputs (hidden when all-day) */}
                  {!allDay && (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                          Start Time
                        </label>
                        <input
                          type="time"
                          value={startTime}
                          onChange={(e) => setStartTime(e.target.value)}
                          disabled={!isEditable}
                          className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 disabled:opacity-50"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                          End Time
                        </label>
                        <input
                          type="time"
                          value={endTime}
                          onChange={(e) => setEndTime(e.target.value)}
                          disabled={!isEditable}
                          className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 disabled:opacity-50"
                        />
                      </div>
                    </div>
                  )}

                  {/* Assigned To */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Assigned To
                    </label>
                    <select
                      value={assignedTo}
                      onChange={(e) => setAssignedTo(e.target.value)}
                      disabled={!isEditable}
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 disabled:opacity-50"
                    >
                      <option value="">Unassigned</option>
                      {familyMembers.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-card-border dark:border-gray-700 flex justify-between">
                  {/* Delete button (edit mode only, manual events only) */}
                  <div>
                    {initialEvent && isEditable && (
                      <button
                        type="button"
                        onClick={handleDelete}
                        disabled={loading}
                        className="px-4 py-2.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl font-medium transition-colors text-sm"
                      >
                        Delete
                      </button>
                    )}
                  </div>

                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={onClose}
                      disabled={loading}
                      className="px-4 py-2.5 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-700 rounded-xl font-medium transition-colors"
                    >
                      Cancel
                    </button>
                    {isEditable && (
                      <button
                        type="submit"
                        disabled={loading || !isValid}
                        className="px-6 py-2.5 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Saving...' : initialEvent ? 'Save Changes' : 'Create Event'}
                      </button>
                    )}
                  </div>
                </div>
              </form>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  )
}

function addOneHour(timeStr) {
  if (!timeStr) return ''
  const [h, m] = timeStr.split(':').map(Number)
  const newH = Math.min(h + 1, 23)
  return `${String(newH).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}
