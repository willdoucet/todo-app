import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import axios from 'axios'
import TodoForm from '../TodoForm'
import { formatDateKey } from './calendarUtils'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Modal wrapping TodoForm for creating/editing tasks from the calendar.
 * Create mode: pre-fills due_date from clicked calendar date.
 * Edit mode: pre-fills all fields from initialTask, PATCH on save, Delete button.
 */
export default function TaskFormModal({
  isOpen,
  onClose,
  onSaved,
  defaultDate = null,
  initialTask = null,
}) {
  const [lists, setLists] = useState([])
  const [selectedListId, setSelectedListId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Fetch available lists when modal opens
  useEffect(() => {
    if (isOpen) {
      setError(null)
      axios.get(`${API_BASE}/lists`).then((res) => {
        setLists(res.data)
        if (initialTask) {
          setSelectedListId(initialTask.list_id)
        } else if (res.data.length > 0 && !selectedListId) {
          setSelectedListId(res.data[0].id)
        }
      }).catch((err) => {
        console.error('Error fetching lists:', err)
      })
    }
  }, [isOpen, initialTask])

  const handleSubmit = async (taskData) => {
    setLoading(true)
    setError(null)
    try {
      const payload = {
        ...taskData,
        list_id: selectedListId,
      }
      if (initialTask) {
        await axios.patch(`${API_BASE}/tasks/${initialTask.id}`, payload)
      } else {
        await axios.post(`${API_BASE}/tasks`, payload)
      }
      onSaved()
      onClose()
    } catch (err) {
      console.error('Error saving task:', err)
      setError(err.response?.data?.detail || 'Failed to save task')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!initialTask) return
    setLoading(true)
    try {
      await axios.delete(`${API_BASE}/tasks/${initialTask.id}`)
      onSaved()
      onClose()
    } catch (err) {
      console.error('Error deleting task:', err)
      setError(err.response?.data?.detail || 'Failed to delete task')
    } finally {
      setLoading(false)
    }
  }

  // Build initial data for TodoForm
  const initialData = initialTask
    ? initialTask
    : defaultDate
      ? { due_date: formatDateKey(defaultDate) + 'T00:00:00' }
      : null

  // Date subtitle
  const dateLabel = initialTask?.due_date
    ? new Date(initialTask.due_date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
    : defaultDate
      ? defaultDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
      : null

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
              {/* Header */}
              <div className="px-6 py-4 border-b border-card-border dark:border-gray-700">
                <Dialog.Title className="text-xl font-semibold text-text-primary dark:text-gray-100">
                  {initialTask ? 'Edit Task' : 'New Task'}
                </Dialog.Title>
                {dateLabel && (
                  <p className="text-sm text-text-secondary dark:text-gray-400 mt-1">
                    {dateLabel}
                  </p>
                )}
              </div>

              {error && (
                <div className="px-6 pt-3">
                  <p className="text-sm text-red-500 dark:text-red-400">{error}</p>
                </div>
              )}

              {/* List selector */}
              <div className="px-6 pt-4">
                <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                  List
                </label>
                <select
                  value={selectedListId || ''}
                  onChange={(e) => setSelectedListId(parseInt(e.target.value))}
                  className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                >
                  {lists.map((list) => (
                    <option key={list.id} value={list.id}>{list.name}</option>
                  ))}
                </select>
              </div>

              {/* TodoForm */}
              <div className="px-6 py-4">
                <TodoForm
                  initial={initialData}
                  listId={selectedListId}
                  onSubmit={handleSubmit}
                  onCancel={onClose}
                />
              </div>

              {/* Delete button (edit mode only) */}
              {initialTask && (
                <div className="px-6 pb-4 -mt-2">
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={loading}
                    className="px-4 py-2.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl font-medium transition-colors text-sm"
                  >
                    Delete Task
                  </button>
                </div>
              )}
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  )
}
