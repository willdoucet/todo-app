import { useState } from 'react'
import axios from 'axios'
import MemberAvatar from '../shared/MemberAvatar'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Meal card for the swimlane grid.
 * Has 3 variants: recipe (full card), food_item (lighter), custom (text only).
 * All variants support cooked state + participant avatars + hover actions.
 */
export default function MealCard({ entry, slotType, familyMembers, onUpdated, onDeleted }) {
  const [isWorking, setIsWorking] = useState(false)

  const isRecipe = entry.item_type === 'recipe' && entry.recipe
  const isFoodItem = entry.item_type === 'food_item' && entry.food_item
  const isCustom = entry.item_type === 'custom'

  const displayName =
    (isRecipe && entry.recipe.name) ||
    (isFoodItem && entry.food_item.name) ||
    entry.custom_meal_name ||
    'Untitled meal'

  const emoji = isFoodItem ? entry.food_item.emoji : null
  const cookTime = isRecipe ? entry.recipe.cook_time_minutes : null
  const isFavorite = isRecipe ? entry.recipe.is_favorite : false

  // Participant display logic: if all household members → show "Everyone" badge
  // Otherwise show avatars
  const participants = entry.participants || []
  const allMembers = familyMembers.filter((m) => !m.is_system)
  const isEveryone =
    participants.length === 0 ||
    (participants.length === allMembers.length && allMembers.length > 0)

  const handleToggleCooked = async (e) => {
    e.stopPropagation()
    if (isWorking) return
    setIsWorking(true)
    try {
      const res = await axios.patch(`${API_BASE}/meal-entries/${entry.id}`, {
        was_cooked: !entry.was_cooked,
      })
      onUpdated(res.data)
    } catch (err) {
      console.error('Failed to toggle cooked:', err)
    } finally {
      setIsWorking(false)
    }
  }

  const handleDelete = async (e) => {
    e.stopPropagation()
    if (isWorking) return
    setIsWorking(true)
    try {
      await axios.delete(`${API_BASE}/meal-entries/${entry.id}`)
      onDeleted(entry.id)
    } catch (err) {
      console.error('Failed to delete meal:', err)
      setIsWorking(false)
    }
  }

  // Food item variant: lighter, translucent
  if (isFoodItem) {
    return (
      <div
        className={`
          meal-card-enter
          group relative flex items-center gap-1.5 px-2 py-1.5 rounded-lg
          bg-white/65 dark:bg-white/10
          hover:bg-white/90 dark:hover:bg-white/15
          text-xs font-medium text-text-secondary dark:text-gray-300
          transition-all
          ${entry.was_cooked ? 'opacity-60' : ''}
        `}
      >
        {emoji && <span className="text-sm leading-none">{emoji}</span>}
        <span className={`flex-1 truncate ${entry.was_cooked ? 'line-through' : ''}`}>
          {displayName}
        </span>

        {/* Participant mini-avatars */}
        {!isEveryone && participants.length > 0 && (
          <div className="flex -space-x-1">
            {participants.slice(0, 3).map((p) => (
              <MemberAvatar
                key={p.id}
                name={p.name}
                photoUrl={p.photo_url}
                color={p.color}
                size="xs"
                className="ring-2 ring-white dark:ring-gray-800"
              />
            ))}
          </div>
        )}

        <HoverActions
          wasCooked={entry.was_cooked}
          onToggleCooked={handleToggleCooked}
          onDelete={handleDelete}
          isWorking={isWorking}
        />
      </div>
    )
  }

  // Recipe + Custom variants: full white card
  return (
    <div
      className={`
        meal-card-enter
        group relative rounded-xl border border-card-border/60 dark:border-gray-700
        bg-card-bg dark:bg-gray-800
        p-2 transition-all
        hover:shadow-md
        ${entry.was_cooked ? 'bg-sage-50 dark:bg-green-900/10' : ''}
      `}
    >
      {/* Cooked badge (top-right) */}
      {entry.was_cooked && (
        <div
          className="
            bounce-in
            absolute top-1.5 right-1.5 w-5 h-5 rounded-full
            bg-gradient-to-br from-sage-500 to-sage-600
            dark:from-green-500 dark:to-green-600
            text-white text-xs font-bold
            flex items-center justify-center shadow
          "
        >
          ✓
        </div>
      )}

      {/* Name */}
      <div
        className={`
          text-xs font-semibold leading-tight pr-6
          text-text-primary dark:text-gray-100
          ${entry.was_cooked ? 'line-through text-sage-600 dark:text-green-500' : ''}
        `}
      >
        {displayName}
      </div>

      {/* Meta: cook time + favorite */}
      {(cookTime || isFavorite) && (
        <div className="flex items-center gap-1.5 mt-1 text-[10px] text-text-muted dark:text-gray-400">
          {cookTime && (
            <span className="flex items-center gap-0.5">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10" />
                <path strokeLinecap="round" d="M12 6v6l4 2" />
              </svg>
              {cookTime}m
            </span>
          )}
          {isFavorite && (
            <span className="px-1.5 py-0.5 rounded bg-gradient-to-r from-terracotta-500 to-peach-200 dark:from-blue-600 dark:to-blue-400 text-white text-[9px] font-bold">
              ★ FAV
            </span>
          )}
        </div>
      )}

      {/* Notes */}
      {entry.notes && (
        <div className="mt-1 text-[10px] italic text-text-muted dark:text-gray-400 line-clamp-1">
          {entry.notes}
        </div>
      )}

      {/* Footer: participants + actions */}
      <div className="flex items-center justify-between mt-1.5">
        {isEveryone ? (
          <span className="text-[9px] font-semibold text-text-muted dark:text-gray-400 px-1.5 py-0.5 bg-warm-beige dark:bg-gray-700 rounded">
            Everyone
          </span>
        ) : (
          <div className="flex -space-x-1">
            {participants.slice(0, 4).map((p) => (
              <MemberAvatar
                key={p.id}
                name={p.name}
                photoUrl={p.photo_url}
                color={p.color}
                size="xs"
                className="ring-2 ring-card-bg dark:ring-gray-800"
              />
            ))}
            {participants.length > 4 && (
              <span className="text-[9px] text-text-muted ml-0.5 self-center">
                +{participants.length - 4}
              </span>
            )}
          </div>
        )}

        <HoverActions
          wasCooked={entry.was_cooked}
          onToggleCooked={handleToggleCooked}
          onDelete={handleDelete}
          isWorking={isWorking}
        />
      </div>
    </div>
  )
}

function HoverActions({ wasCooked, onToggleCooked, onDelete, isWorking }) {
  return (
    <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
      <button
        type="button"
        onClick={onToggleCooked}
        disabled={isWorking}
        title={wasCooked ? 'Mark as not cooked' : 'Mark as cooked'}
        aria-label={wasCooked ? 'Mark as not cooked' : 'Mark as cooked'}
        className="
          p-1 rounded text-text-muted dark:text-gray-500
          hover:text-sage-600 dark:hover:text-green-400
          hover:bg-sage-50 dark:hover:bg-green-900/20
          transition-colors disabled:opacity-50
        "
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </button>
      <button
        type="button"
        onClick={onDelete}
        disabled={isWorking}
        title="Delete"
        aria-label="Delete meal"
        className="
          p-1 rounded text-text-muted dark:text-gray-500
          hover:text-red-600 dark:hover:text-red-400
          hover:bg-red-50 dark:hover:bg-red-900/20
          transition-colors disabled:opacity-50
        "
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}
