import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import axios from 'axios'
import { formatDateKey } from './calendarUtils'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [date, setDate] = useState('')
  const [allDay, setAllDay] = useState(false)
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [assignedTo, setAssignedTo] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      if (initialEvent) {
        setTitle(initialEvent.title || '')
        setDescription(initialEvent.description || '')
        setDate(String(initialEvent.date).slice(0, 10))
        setAllDay(initialEvent.all_day || false)
        setStartTime(initialEvent.start_time || '')
        setEndTime(initialEvent.end_time || '')
        setAssignedTo(initialEvent.assigned_to ?? '')
      } else {
        setTitle('')
        setDescription('')
        setDate(defaultDate ? formatDateKey(defaultDate) : formatDateKey(new Date()))
        setAllDay(false)
        setStartTime(defaultTime || '')
        setEndTime(defaultTime ? addOneHour(defaultTime) : '')
        setAssignedTo('')
      }
      setError(null)
    }
  }, [isOpen, initialEvent, defaultDate, defaultTime])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim()) return

    setLoading(true)
    setError(null)

    const payload = {
      title: title.trim(),
      description: description.trim() || null,
      date,
      all_day: allDay,
      start_time: allDay ? null : startTime || null,
      end_time: allDay ? null : endTime || null,
      assigned_to: assignedTo ? parseInt(assignedTo) : null,
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
      setError(err.response?.data?.detail || 'Failed to save event')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!initialEvent) return
    setLoading(true)
    try {
      await axios.delete(`${API_BASE}/calendar-events/${initialEvent.id}`)
      onSaved()
      onClose()
    } catch (err) {
      console.error('Error deleting event:', err)
      setError(err.response?.data?.detail || 'Failed to delete event')
    } finally {
      setLoading(false)
    }
  }

  const isEditable = !initialEvent || initialEvent.source === 'MANUAL'
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
