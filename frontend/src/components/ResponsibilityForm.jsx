import { useState, useEffect } from 'react'
import axios from 'axios'
import PhotoUpload from './PhotoUpload'

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
  const [description, setDescription] = useState(initial?.description || '')
  const [category, setCategory] = useState(initial?.category || 'MORNING')
  const [assignedTo, setAssignedTo] = useState(initial?.assigned_to || null)
  const [frequency, setFrequency] = useState(
    initial?.frequency || ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
  )
  const [iconUrl, setIconUrl] = useState(initial?.icon_url || null)
  const [familyMembers, setFamilyMembers] = useState([])
  const [stockIcons, setStockIcons] = useState([])
  const [isLoadingFamilyMembers, setIsLoadingFamilyMembers] = useState(true)
  const [showCustomUpload, setShowCustomUpload] = useState(false)

  useEffect(() => {
    const loadData = async () => {
      try {
        const [membersRes, iconsRes] = await Promise.all([
          axios.get(`${API_BASE}/family-members`),
          axios.get(`${API_BASE}/upload/stock-icons`),
        ])
        
        setFamilyMembers(membersRes.data)
        setStockIcons(iconsRes.data)

        if (!initial?.assigned_to && membersRes.data.length > 0) {
          setAssignedTo(membersRes.data[0].id)
        }
      } catch (err) {
        console.error('Error loading data:', err)
      } finally {
        setIsLoadingFamilyMembers(false)
      }
    }
    loadData()
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
        description: description.trim() || null,
        category,
        assigned_to: assignedTo,
        frequency,
        icon_url: iconUrl,
      })
    } else {
      onSubmit({
        title,
        description: description.trim() || null,
        category,
        assigned_to: assignedTo,
        frequency,
        icon_url: iconUrl,
      })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
      {/* Title */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Title {!isEditMode && <span className="text-red-500 dark:text-red-400">*</span>}
        </label>
        {isEditMode ? (
          <div className="px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-700 rounded-lg bg-warm-beige dark:bg-gray-800 text-text-secondary dark:text-gray-300 text-sm sm:text-base">
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
              w-full px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-600
              rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
              focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
              outline-none transition text-sm sm:text-base
              placeholder:text-text-muted dark:placeholder:text-gray-500
            "
          />
        )}
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Description <span className="text-text-muted dark:text-gray-500 text-xs font-normal">(optional)</span>
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Add details about this responsibility..."
          rows={2}
          maxLength={500}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-600
            rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
            focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
            outline-none transition text-sm sm:text-base resize-none
            placeholder:text-text-muted dark:placeholder:text-gray-500
          "
        />
        <p className="mt-1 text-xs text-text-muted dark:text-gray-500 text-right">
          {description.length}/500
        </p>
      </div>

      {/* Category */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Category <span className="text-red-500 dark:text-red-400">*</span>
        </label>
        <select
          value={category}
          onChange={e => setCategory(e.target.value)}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-600
            rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
            focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
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
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Assigned To
        </label>
        <select
          value={assignedTo || ''}
          onChange={e => setAssignedTo(parseInt(e.target.value))}
          disabled={isLoadingFamilyMembers}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-600
            rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
            focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
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
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
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
                    ? 'bg-terracotta-500 text-white dark:bg-blue-600'
                    : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-400 hover:bg-warm-sand dark:hover:bg-gray-600'
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
            className="text-xs text-terracotta-600 dark:text-blue-400 hover:underline"
          >
            Weekdays
          </button>
          <button
            type="button"
            onClick={() => setFrequency(['Saturday', 'Sunday'])}
            className="text-xs text-terracotta-600 dark:text-blue-400 hover:underline"
          >
            Weekends
          </button>
          <button
            type="button"
            onClick={() => setFrequency(['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'])}
            className="text-xs text-terracotta-600 dark:text-blue-400 hover:underline"
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

      {/* Icon Selection */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Icon <span className="text-text-muted dark:text-gray-500 text-xs font-normal">(optional)</span>
        </label>

        {/* Current icon preview and clear button */}
        {iconUrl && (
          <div className="flex items-center gap-3 mb-3 p-2 bg-warm-beige dark:bg-gray-800 rounded-lg">
            <img
              src={iconUrl.startsWith('http') ? iconUrl : `${API_BASE}${iconUrl}`}
              alt="Selected icon"
              className="w-10 h-10 rounded object-cover"
            />
            <span className="text-sm text-text-secondary dark:text-gray-400 flex-1">Selected icon</span>
            <button
              type="button"
              onClick={() => setIconUrl(null)}
              className="text-xs text-red-500 hover:text-red-600 dark:text-red-400"
            >
              Remove
            </button>
          </div>
        )}

        {/* Stock icons grid */}
        <div className="grid grid-cols-5 gap-2 mb-3">
          {stockIcons.map(icon => (
            <button
              key={icon.id}
              type="button"
              onClick={() => {
                setIconUrl(icon.url)
                setShowCustomUpload(false)
              }}
              className={`
                p-2 rounded-lg border-2 transition-all
                ${iconUrl === icon.url
                  ? 'border-terracotta-500 bg-peach-100 dark:bg-blue-900/20 dark:border-blue-500'
                  : 'border-card-border dark:border-gray-700 hover:border-terracotta-200 dark:hover:border-gray-600'
                }
              `}
              title={icon.label}
            >
              <img
                src={`${API_BASE}${icon.url}`}
                alt={icon.label}
                className="w-8 h-8 mx-auto object-contain"
              />
            </button>
          ))}
        </div>

        {/* Custom upload toggle */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowCustomUpload(!showCustomUpload)}
            className="text-xs text-terracotta-600 dark:text-blue-400 hover:underline"
          >
            {showCustomUpload ? 'Hide custom upload' : 'Upload custom icon'}
          </button>
        </div>

        {/* Custom upload area */}
        {showCustomUpload && (
          <div className="mt-3">
            <PhotoUpload
              currentUrl={iconUrl && !stockIcons.some(s => s.url === iconUrl) ? iconUrl : null}
              onUpload={(url) => setIconUrl(url)}
              uploadEndpoint="/upload/responsibility-icon"
              placeholder="Upload Icon"
              size="md"
            />
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 sm:pt-3">
        <button
          type="button"
          onClick={onCancel}
          className="
            px-5 py-2.5 sm:py-2.5 text-text-secondary dark:text-gray-300 font-medium
            hover:bg-warm-beige dark:hover:bg-gray-700 rounded-lg transition-colors duration-200
            text-sm sm:text-base
          "
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={frequency.length === 0}
          className="
            px-6 py-2.5 sm:py-2.5 bg-terracotta-500 text-white font-medium
            rounded-lg hover:bg-terracotta-600 transition-colors duration-200
            focus:outline-none focus:ring-2 focus:ring-terracotta-500 focus:ring-offset-2
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
