import { useState, useEffect } from 'react'
import axios from 'axios'
import MealSlotCard from './MealSlotCard'
import DayPreview from './DayPreview'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function MealboardSettings() {
  const [slotTypes, setSlotTypes] = useState([])
  const [familyMembers, setFamilyMembers] = useState([])
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editingSlotId, setEditingSlotId] = useState(null)
  const [addingNew, setAddingNew] = useState(false)
  const [error, setError] = useState(null)

  // Load all data on mount
  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [slotsRes, membersRes, settingsRes] = await Promise.all([
        axios.get(`${API_BASE}/meal-slot-types/`),
        axios.get(`${API_BASE}/family-members/`),
        axios.get(`${API_BASE}/app-settings/`),
      ])
      setSlotTypes(slotsRes.data)
      setFamilyMembers(membersRes.data)
      setSettings(settingsRes.data)
    } catch (err) {
      console.error('Failed to load mealboard settings:', err)
      setError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = async (slotId, updates) => {
    try {
      const res = await axios.patch(`${API_BASE}/meal-slot-types/${slotId}`, updates)
      setSlotTypes((prev) => prev.map((s) => (s.id === slotId ? res.data : s)))
      setEditingSlotId(null)
    } catch (err) {
      console.error('Failed to update slot:', err)
      setError('Failed to save changes')
    }
  }

  const handleToggleActive = async (slot) => {
    await handleUpdate(slot.id, { is_active: !slot.is_active })
  }

  const handleDelete = async (slotId) => {
    if (!confirm('Delete this meal slot? If it has meals, it will be hidden instead.')) return
    try {
      const res = await axios.delete(`${API_BASE}/meal-slot-types/${slotId}`)
      // If soft-delete (still has entries), update; if hard-delete, remove
      if (res.data.is_active === false) {
        // Soft-deleted — slot still returned
        setSlotTypes((prev) => prev.map((s) => (s.id === slotId ? res.data : s)))
      } else {
        // Hard-deleted — remove from list
        setSlotTypes((prev) => prev.filter((s) => s.id !== slotId))
      }
    } catch (err) {
      console.error('Failed to delete slot:', err)
      setError('Failed to delete slot')
    }
  }

  const handleCreate = async (slotData) => {
    try {
      // Compute sort_order as max+1
      const maxOrder = slotTypes.reduce((max, s) => Math.max(max, s.sort_order), 0)
      const res = await axios.post(`${API_BASE}/meal-slot-types/`, {
        ...slotData,
        sort_order: maxOrder + 1,
      })
      setSlotTypes((prev) => [...prev, res.data])
      setAddingNew(false)
    } catch (err) {
      console.error('Failed to create slot:', err)
      setError('Failed to create slot')
    }
  }

  const handleResetDefaults = async () => {
    if (!confirm('Reset meal slots to defaults? Custom slots without meals will be deleted.')) return
    try {
      const res = await axios.post(`${API_BASE}/meal-slot-types/reset`)
      setSlotTypes(res.data)
    } catch (err) {
      console.error('Failed to reset:', err)
      setError('Failed to reset to defaults')
    }
  }

  const handleSettingChange = async (key, value) => {
    try {
      const res = await axios.patch(`${API_BASE}/app-settings/`, { [key]: value })
      setSettings(res.data)
    } catch (err) {
      console.error('Failed to update settings:', err)
      setError('Failed to save preference')
    }
  }

  if (loading) {
    return <div className="text-sm text-text-muted dark:text-gray-400 py-4">Loading mealboard settings...</div>
  }

  return (
    <div>
      {error && (
        <div className="mb-4 p-3 rounded-lg text-sm bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-6">
        {/* Left column: Slot list */}
        <div>
          <h3 className="text-sm font-semibold text-text-primary dark:text-gray-100 mb-3">
            Meal Slots
          </h3>
          <div className="space-y-2">
            {slotTypes.map((slot) => (
              <MealSlotCard
                key={slot.id}
                slot={slot}
                familyMembers={familyMembers}
                isEditing={editingSlotId === slot.id}
                onStartEdit={() => setEditingSlotId(slot.id)}
                onCancelEdit={() => setEditingSlotId(null)}
                onSave={(updates) => handleUpdate(slot.id, updates)}
                onToggleActive={() => handleToggleActive(slot)}
                onDelete={() => handleDelete(slot.id)}
              />
            ))}

            {addingNew && (
              <MealSlotCard
                slot={null}
                familyMembers={familyMembers}
                isEditing={true}
                isNew={true}
                onStartEdit={() => {}}
                onCancelEdit={() => setAddingNew(false)}
                onSave={handleCreate}
              />
            )}

            {!addingNew && (
              <button
                type="button"
                onClick={() => setAddingNew(true)}
                className="
                  w-full py-2.5 px-4 rounded-xl border-2 border-dashed
                  border-card-border dark:border-gray-600
                  text-sm font-medium text-text-muted dark:text-gray-400
                  hover:border-terracotta-500 hover:text-terracotta-500 dark:hover:border-blue-500 dark:hover:text-blue-400
                  transition-colors
                "
              >
                + Add Meal Slot
              </button>
            )}

            <button
              type="button"
              onClick={handleResetDefaults}
              className="
                text-xs text-text-muted dark:text-gray-400
                hover:text-text-secondary dark:hover:text-gray-300
                underline underline-offset-2 mt-2
              "
            >
              Reset to defaults
            </button>
          </div>
        </div>

        {/* Right column: Day preview (sticky) */}
        <div>
          <div className="lg:sticky lg:top-6">
            <h3 className="text-sm font-semibold text-text-primary dark:text-gray-100 mb-3">
              Day Preview
            </h3>
            <DayPreview slotTypes={slotTypes} editingSlotId={editingSlotId} />
          </div>
        </div>
      </div>

      {/* Preferences row */}
      <div className="mt-6 pt-6 border-t border-card-border dark:border-gray-700">
        <h3 className="text-sm font-semibold text-text-primary dark:text-gray-100 mb-3">
          Preferences
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary dark:text-gray-300 mb-1">
              Week starts on
            </label>
            <select
              value={settings.week_start_day}
              onChange={(e) => handleSettingChange('week_start_day', e.target.value)}
              className="
                w-full px-3 py-2 text-sm rounded-lg
                border border-card-border dark:border-gray-600
                bg-white dark:bg-gray-700
                text-text-primary dark:text-gray-100
                focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
              "
            >
              <option value="monday">Monday</option>
              <option value="sunday">Sunday</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary dark:text-gray-300 mb-1">
              Measurement system
            </label>
            <div className="flex gap-1 p-1 rounded-lg bg-warm-beige dark:bg-gray-700">
              <button
                type="button"
                onClick={() => handleSettingChange('measurement_system', 'imperial')}
                className={`
                  flex-1 py-1.5 text-sm rounded-md font-medium transition-colors
                  ${
                    settings.measurement_system === 'imperial'
                      ? 'bg-white dark:bg-gray-800 text-terracotta-600 dark:text-blue-400 shadow-sm'
                      : 'text-text-muted dark:text-gray-400 hover:text-text-secondary dark:hover:text-gray-300'
                  }
                `}
              >
                Imperial
              </button>
              <button
                type="button"
                onClick={() => handleSettingChange('measurement_system', 'metric')}
                className={`
                  flex-1 py-1.5 text-sm rounded-md font-medium transition-colors
                  ${
                    settings.measurement_system === 'metric'
                      ? 'bg-white dark:bg-gray-800 text-terracotta-600 dark:text-blue-400 shadow-sm'
                      : 'text-text-muted dark:text-gray-400 hover:text-text-secondary dark:hover:text-gray-300'
                  }
                `}
              >
                Metric
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
