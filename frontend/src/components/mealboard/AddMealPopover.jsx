import { useState, useEffect, useRef, useMemo } from 'react'
import axios from 'axios'
import MemberAvatar from '../shared/MemberAvatar'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const FILTER_OPTIONS = [
  { value: null, label: 'All' },
  { value: 'recipes', label: 'Recipes' },
  { value: 'food_items', label: 'Food Items' },
]

/**
 * Add meal popover. Opens when user clicks + in any swimlane cell.
 *
 * Features:
 *  - Unified search across recipes + food items
 *  - Optional filter chips (Recipes | Food Items | All)
 *  - Grouped results (Recipes section, Food Items section)
 *  - Custom fallback row: "+ Add '<query>' as custom meal"
 *  - Participant avatar toggles (default = slot type default / everyone)
 *  - Notes field
 *  - Pre-populated slot type + date from the clicked cell
 */
export default function AddMealPopover({
  context, // { date, slotTypeId, anchorRect }
  slotTypes,
  recipes,
  foodItems,
  familyMembers,
  onClose,
  onCreated,
}) {
  const slot = slotTypes.find((s) => s.id === context.slotTypeId)
  const panelRef = useRef(null)
  const searchInputRef = useRef(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState(null) // null, 'recipes', 'food_items'

  // Initialize participant_ids from slot defaults (or all members if empty)
  const defaultParticipantIds = useMemo(() => {
    if (slot?.default_participants && slot.default_participants.length > 0) {
      return slot.default_participants
    }
    return familyMembers.filter((m) => !m.is_system).map((m) => m.id)
  }, [slot, familyMembers])

  const [selectedParticipantIds, setSelectedParticipantIds] = useState(defaultParticipantIds)
  const [notes, setNotes] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Focus search on open
  useEffect(() => {
    setTimeout(() => searchInputRef.current?.focus(), 50)
  }, [])

  // Close on click-outside or Escape
  useEffect(() => {
    const handleClick = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        onClose()
      }
    }
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [onClose])

  // Filter search results
  const { filteredRecipes, filteredFoodItems } = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    const matchRecipes = !filter || filter === 'recipes'
    const matchFoodItems = !filter || filter === 'food_items'

    return {
      filteredRecipes: matchRecipes
        ? recipes.filter((r) => !q || r.name.toLowerCase().includes(q)).slice(0, 8)
        : [],
      filteredFoodItems: matchFoodItems
        ? foodItems.filter((f) => !q || f.name.toLowerCase().includes(q)).slice(0, 8)
        : [],
    }
  }, [searchQuery, filter, recipes, foodItems])

  const handleToggleParticipant = (memberId) => {
    setSelectedParticipantIds((prev) =>
      prev.includes(memberId) ? prev.filter((id) => id !== memberId) : [...prev, memberId]
    )
  }

  const handleCreate = async (itemType, payload) => {
    setIsSubmitting(true)
    setError(null)
    try {
      const body = {
        date: formatDateKey(context.date),
        meal_slot_type_id: context.slotTypeId,
        item_type: itemType,
        ...payload,
        participant_ids: selectedParticipantIds,
        notes: notes.trim() || null,
      }
      const res = await axios.post(`${API_BASE}/meal-entries/`, body)
      onCreated(res.data)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to add meal')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleRecipeSelect = (recipe) => {
    handleCreate('recipe', { recipe_id: recipe.id })
  }

  const handleFoodItemSelect = (item) => {
    handleCreate('food_item', { food_item_id: item.id })
  }

  const handleCustomCreate = () => {
    if (!searchQuery.trim()) return
    handleCreate('custom', { custom_meal_name: searchQuery.trim() })
  }

  const dateLabel = context.date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  })

  const hasAnyResults = filteredRecipes.length > 0 || filteredFoodItems.length > 0

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40" onClick={onClose} />

      {/* Popover */}
      <div
        ref={panelRef}
        className="
          fixed z-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
          w-[min(420px,calc(100vw-2rem))]
          max-h-[min(600px,calc(100vh-4rem))]
          bg-card-bg dark:bg-gray-800
          rounded-2xl shadow-2xl
          border border-card-border dark:border-gray-700
          flex flex-col
          animate-in fade-in zoom-in-95 duration-150
        "
        role="dialog"
        aria-label="Add meal"
      >
        {/* Header with slot + date */}
        <div className="p-4 border-b border-card-border dark:border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            {slot?.icon && <span className="text-xl leading-none">{slot.icon}</span>}
            <div className="flex-1 min-w-0">
              <div
                className="text-xs font-bold uppercase tracking-wide"
                style={{ color: slot?.color || '#9CA3AF' }}
              >
                {slot?.name || 'Meal'}
              </div>
              <div className="text-sm font-medium text-text-primary dark:text-gray-100">
                {dateLabel}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1 text-text-muted hover:text-text-secondary dark:text-gray-500 dark:hover:text-gray-300 rounded"
              aria-label="Close"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Unified search */}
          <div className="relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted dark:text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search recipes, food items, or type anything..."
              className="
                w-full pl-9 pr-3 py-2 text-sm rounded-lg
                border border-card-border dark:border-gray-600
                bg-white dark:bg-gray-700
                text-text-primary dark:text-gray-100
                placeholder-text-muted dark:placeholder-gray-500
                focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
              "
            />
          </div>

          {/* Filter chips */}
          <div className="flex gap-1.5 mt-2">
            {FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.label}
                type="button"
                onClick={() => setFilter(opt.value)}
                className={`
                  px-2.5 py-1 text-[11px] font-semibold rounded-full transition-colors
                  ${
                    filter === opt.value
                      ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                      : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-sand dark:hover:bg-gray-600'
                  }
                `}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Search results (scrollable) */}
        <div className="flex-1 overflow-y-auto p-2">
          {filteredRecipes.length > 0 && (
            <div className="mb-2">
              <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-text-muted dark:text-gray-400">
                Recipes
              </div>
              {filteredRecipes.map((recipe) => (
                <button
                  key={recipe.id}
                  type="button"
                  onClick={() => handleRecipeSelect(recipe)}
                  disabled={isSubmitting}
                  className="
                    w-full flex items-center gap-2 px-2 py-2 rounded-lg text-left
                    hover:bg-warm-beige dark:hover:bg-gray-700 transition-colors
                    disabled:opacity-50
                  "
                >
                  <span className="text-base">📖</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-text-primary dark:text-gray-100 truncate">
                      {recipe.name}
                    </div>
                    {(recipe.cook_time_minutes || recipe.is_favorite) && (
                      <div className="text-[10px] text-text-muted dark:text-gray-400 flex items-center gap-2">
                        {recipe.cook_time_minutes && <span>🕐 {recipe.cook_time_minutes}m</span>}
                        {recipe.is_favorite && <span className="text-terracotta-500 dark:text-blue-400 font-bold">★</span>}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}

          {filteredFoodItems.length > 0 && (
            <div className="mb-2">
              <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-text-muted dark:text-gray-400">
                Food Items
              </div>
              {filteredFoodItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleFoodItemSelect(item)}
                  disabled={isSubmitting}
                  className="
                    w-full flex items-center gap-2 px-2 py-2 rounded-lg text-left
                    hover:bg-warm-beige dark:hover:bg-gray-700 transition-colors
                    disabled:opacity-50
                  "
                >
                  <span className="text-base">{item.emoji || '🍽'}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-text-primary dark:text-gray-100 truncate">
                      {item.name}
                    </div>
                    {item.category && (
                      <div className="text-[10px] text-text-muted dark:text-gray-400 capitalize">
                        {item.category}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}

          {!hasAnyResults && searchQuery && (
            <div className="px-3 py-4 text-center text-xs text-text-muted dark:text-gray-400">
              No recipes or food items match "{searchQuery}"
            </div>
          )}

          {/* Custom fallback row */}
          {searchQuery.trim() && (
            <button
              type="button"
              onClick={handleCustomCreate}
              disabled={isSubmitting}
              className="
                w-full flex items-center gap-2 px-2 py-2 mt-2 rounded-lg text-left
                border-t border-dashed border-card-border dark:border-gray-600 pt-3
                text-text-secondary dark:text-gray-300
                hover:bg-warm-beige dark:hover:bg-gray-700
                transition-colors disabled:opacity-50
              "
            >
              <span className="text-terracotta-500 dark:text-blue-400 text-lg">+</span>
              <span className="text-sm">
                Add <span className="font-semibold text-text-primary dark:text-gray-100">"{searchQuery.trim()}"</span> as custom meal
              </span>
            </button>
          )}

          {!searchQuery && !hasAnyResults && (
            <div className="px-3 py-6 text-center text-xs text-text-muted dark:text-gray-400">
              Start typing to search
            </div>
          )}
        </div>

        {/* Footer: Participants + Notes */}
        <div className="p-3 border-t border-card-border dark:border-gray-700 space-y-2">
          {error && (
            <div className="p-2 rounded-lg text-xs bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          {/* Participants */}
          {familyMembers.length > 0 && (
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-text-muted dark:text-gray-400 mb-1.5">
                Who's eating
              </div>
              <div className="flex gap-1.5 flex-wrap">
                {familyMembers.filter((m) => !m.is_system).map((member) => {
                  const isActive = selectedParticipantIds.includes(member.id)
                  return (
                    <button
                      key={member.id}
                      type="button"
                      onClick={() => handleToggleParticipant(member.id)}
                      className={`
                        transition-all
                        ${isActive ? 'opacity-100 scale-100' : 'opacity-40 scale-90 grayscale'}
                      `}
                      title={member.name}
                      aria-label={`${isActive ? 'Remove' : 'Add'} ${member.name}`}
                      aria-pressed={isActive}
                    >
                      <MemberAvatar name={member.name} photoUrl={member.photo_url} color={member.color} size="sm" />
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Notes (collapsible) */}
          <details className="text-xs">
            <summary className="cursor-pointer text-text-muted dark:text-gray-400 hover:text-text-secondary dark:hover:text-gray-300">
              Add notes...
            </summary>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Double the garlic"
              rows={2}
              className="
                w-full mt-2 px-2 py-1.5 text-xs rounded-lg
                border border-card-border dark:border-gray-600
                bg-white dark:bg-gray-700
                text-text-primary dark:text-gray-100
                focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
                resize-none
              "
            />
          </details>
        </div>
      </div>
    </>
  )
}

function formatDateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
