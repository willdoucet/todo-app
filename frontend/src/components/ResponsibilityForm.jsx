import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const CATEGORIES = [
  { value: 'MORNING', label: '🌅 Morning' },
  { value: 'AFTERNOON', label: '☀️ Afternoon' },
  { value: 'EVENING', label: '🌙 Evening' },
  { value: 'CHORE', label: '🧹 Chore' },
]

const DAYS = [
  { short: 'Sun', full: 'Sunday' },
  { short: 'Mon', full: 'Monday' },
  { short: 'Tue', full: 'Tuesday' },
  { short: 'Wed', full: 'Wednesday' },
  { short: 'Thu', full: 'Thursday' },
  { short: 'Fri', full: 'Friday' },
  { short: 'Sat', full: 'Saturday' },
]

export default function ResponsibilityForm({ initial = null, onSubmit, onCancel }) {
  const isEditMode = !!initial?.id

  const [title, setTitle] = useState(initial?.title || '')
  const [category, setCategory] = useState(initial?.category || 'MORNING')
  const [assignedTo, setAssignedTo] = useState(initial?.assigned_to || null)
  const [frequency, setFrequency] = useState(
    initial?.frequency || ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
  )
  const [familyMembers, setFamilyMembers] = useState([])
  const [isLoadingFamilyMembers, setIsLoadingFamilyMembers] = useState(true)

  useEffect(() => {
    const loadFamilyMembers = async () => {
      try {
        const response = await axios.get(`${API_BASE}/family-members`)
        setFamilyMembers(response.data)

        if (!initial?.assigned_to && response.data.length > 0) {
          setAssignedTo(response.data[0].id)
        }
      } catch (err) {
        console.error('Error loading family members:', err)
      } finally {
        setIsLoadingFamilyMembers(false)
      }
    }
    loadFamilyMembers()
  }, [initial?.assigned_to])

  const toggleDay = (dayFull) => {
    if (frequency.includes(dayFull)) {
      setFrequency(frequency.filter(d => d !== dayFull))
    } else {
      setFrequency([...frequency, dayFull])
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!title.trim()) return
    if (frequency.length === 0) return

    if (isEditMode) {
      // Only send editable fields in edit mode
      onSubmit({
        id: initial.id,
        category,
        assigned_to: assignedTo,
        frequency,
      })
    } else {
      onSubmit({
        title,
        category,
        assigned_to: assignedTo,
        frequency,
      })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
      {/* Title */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
          Title {!isEditMode && <span className="text-red-500 dark:text-red-400">*</span>}
        </label>
        {isEditMode ? (
          <div className="px-4 py-2.5 sm:py-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm sm:text-base">
            {title}
          </div>
        ) : (
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            required
            placeholder="Enter responsibility title"
            className="
              w-full px-4 py-2.5 sm:py-3 border border-gray-300 dark:border-gray-600 
              rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              outline-none transition text-sm sm:text-base
              placeholder:text-gray-400 dark:placeholder:text-gray-500
            "
          />
        )}
      </div>

      {/* Category */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
          Category <span className="text-red-500 dark:text-red-400">*</span>
        </label>
        <select
          value={category}
          onChange={e => setCategory(e.target.value)}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-gray-300 dark:border-gray-600 
            rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            outline-none transition text-sm sm:text-base
          "
        >
          {CATEGORIES.map(cat => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
      </div>

      {/* Assigned To */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
          Assigned To
        </label>
        <select
          value={assignedTo || ''}
          onChange={e => setAssignedTo(parseInt(e.target.value))}
          disabled={isLoadingFamilyMembers}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-gray-300 dark:border-gray-600 
            rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            outline-none transition text-sm sm:text-base
          "
        >
          {isLoadingFamilyMembers ? (
            <option>Loading...</option>
          ) : (
            familyMembers.map(member => (
              <option key={member.id} value={member.id}>
                {member.name}
              </option>
            ))
          )}
        </select>
      </div>

      {/* Frequency - Day Selector */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
          Repeat On <span className="text-red-500 dark:text-red-400">*</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {DAYS.map(day => {
            const isSelected = frequency.includes(day.full)
            return (
              <button
                key={day.short}
                type="button"
                onClick={() => toggleDay(day.full)}
                className={`
                  w-10 h-10 rounded-full text-sm font-medium transition-colors
                  ${isSelected
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-300 dark:hover:bg-gray-600'
                  }
                `}
              >
                {day.short}
              </button>
            )
          })}
        </div>

        {/* Quick presets */}
        <div className="flex gap-3 mt-3">
          <button
            type="button"
            onClick={() => setFrequency(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            Weekdays
          </button>
          <button
            type="button"
            onClick={() => setFrequency(['Saturday', 'Sunday'])}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            Weekends
          </button>
          <button
            type="button"
            onClick={() => setFrequency(['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'])}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            Daily
          </button>
        </div>

        {frequency.length === 0 && (
          <p className="mt-2 text-sm text-red-500 dark:text-red-400">
            Please select at least one day
          </p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 sm:pt-3">
        <button
          type="button"
          onClick={onCancel}
          className="
            px-5 py-2.5 sm:py-2.5 text-gray-700 dark:text-gray-300 font-medium 
            hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors duration-200
            text-sm sm:text-base
          "
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={frequency.length === 0}
          className="
            px-6 py-2.5 sm:py-2.5 bg-blue-600 text-white font-medium 
            rounded-lg hover:bg-blue-700 transition-colors duration-200
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            text-sm sm:text-base
            disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          {isEditMode ? 'Save Changes' : 'Add Responsibility'}
        </button>
      </div>
    </form>
  )
}
