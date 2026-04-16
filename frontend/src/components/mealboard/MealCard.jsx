import { useState } from 'react'
import axios from 'axios'
import MemberAvatar from '../shared/MemberAvatar'
import ItemIcon from './ItemIcon'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Meal card for the swimlane grid. Branches on `entry.item?.item_type`:
 *
 * - Recipe variant — vertical text-only card (approved mockup D v3): participant
 *   avatars top, name centered, cook time + servings metadata, cooked badge,
 *   hover action icons.
 * - Food-item variant — horizontal pill (Chunk 2 item 5): ItemIcon 24px left +
 *   name right, single row, ≤60px tall, no cook-time metadata. Plan success
 *   criterion (§2030): "emoji to the left of the title, both on a single row,
 *   card height ≤60% of baseline".
 *
 * Outer chrome (background, border, hover states) is shared across both variants.
 */
export default function MealCard({ entry, slotType, familyMembers, onUpdated, onDeleted, onViewRecipe }) {
  const [isWorking, setIsWorking] = useState(false)
  const [isPulsing, setIsPulsing] = useState(false)

  // Unified item model: entry.item replaces entry.recipe + entry.food_item
  const item = entry.item || null
  const isRecipe = item?.item_type === 'recipe'
  const isFoodItem = item?.item_type === 'food_item'
  const displayName = item?.name || entry.custom_meal_name || 'Untitled meal'

  const rd = item?.recipe_detail || {}
  const cookTime = isRecipe ? (rd.prep_time_minutes || 0) + (rd.cook_time_minutes || 0) : null
  const servings = isRecipe ? rd.servings : null

  // Participant display: hide when participants match slot defaults or all members
  const participants = entry.participants || []
  const allMembers = familyMembers.filter((m) => !m.is_system)
  const isEveryone =
    participants.length === 0 ||
    (participants.length === allMembers.length && allMembers.length > 0)

  // Check if participants match slot defaults (by ID set equality)
  const slotDefaults = slotType?.default_participants || []
  const hasDefaultParticipants =
    isEveryone ||
    (slotDefaults.length > 0 &&
      participants.length === slotDefaults.length &&
      new Set(participants.map((p) => p.id)).size === new Set([...participants.map((p) => p.id), ...slotDefaults]).size)
  const showAvatars = !isEveryone && !hasDefaultParticipants

  const handleToggleCooked = async (e) => {
    e.stopPropagation()
    if (isWorking) return
    setIsWorking(true)
    try {
      const markingCooked = !entry.was_cooked
      const res = await axios.patch(`${API_BASE}/meal-entries/${entry.id}`, {
        was_cooked: markingCooked,
      })
      // Pulse only on false → true (marking cooked), not on unmarking
      if (markingCooked) {
        setIsPulsing(true)
        setTimeout(() => setIsPulsing(false), 300)
      }
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

  const handleViewRecipe = (e) => {
    e.stopPropagation()
    if (isRecipe && onViewRecipe && item) {
      onViewRecipe(item.id)
    }
  }

  const handleCardClick = () => {
    if (isRecipe && onViewRecipe && item) {
      onViewRecipe(item.id)
    }
  }

  // Outer chrome shared by both variants
  const containerBase = `meal-card-enter group relative transition-all cursor-pointer select-none rounded-xl border`
  const containerColor = entry.was_cooked
    ? 'bg-sage-50 dark:bg-green-900/10 border-sage-200 dark:border-green-800'
    : 'bg-card-bg dark:bg-gray-800 border-card-border/60 dark:border-gray-700 hover:shadow-md'
  const pulseStyle = isPulsing
    ? { animation: `${document.documentElement.classList.contains('dark') ? 'meal-card-cooked-pulse-dark' : 'meal-card-cooked-pulse'} 300ms ease` }
    : undefined

  // Food-item variant: horizontal pill, compact, icon-left + name-right.
  // Height target ≤60% of the recipe baseline (≤60px) per plan §2030.
  if (isFoodItem) {
    return (
      <div
        className={`${containerBase} ${containerColor} flex items-center gap-2 px-2.5 py-1.5 min-h-[48px]`}
        onClick={handleCardClick}
        style={pulseStyle}
      >
        <ItemIcon item={item} size={24} />
        <span
          className={`flex-1 text-sm font-medium leading-tight truncate ${
            entry.was_cooked
              ? 'line-through text-sage-600 dark:text-green-500'
              : 'text-text-primary dark:text-gray-100'
          }`}
        >
          {displayName}
        </span>
        {showAvatars && (
          <div className="flex -space-x-1 flex-shrink-0">
            {participants.slice(0, 3).map((p) => (
              <MemberAvatar
                key={p.id}
                name={p.name}
                photoUrl={p.photo_url}
                color={p.color}
                size="xs"
                className="w-4 h-4 ring-2 ring-card-bg dark:ring-gray-800"
              />
            ))}
          </div>
        )}
        {entry.was_cooked && (
          <span className="bounce-in text-[10px] font-semibold text-sage-600 dark:text-green-400 flex-shrink-0">✓</span>
        )}

        {/* Hover action icons — 24×24 for the dense food-item row, top-right */}
        <div
          className="
            absolute top-1 right-1
            flex items-center gap-1
            max-md:opacity-100
            md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100
            transition-opacity duration-150
          "
        >
          <button
            type="button"
            onClick={handleToggleCooked}
            disabled={isWorking}
            title={entry.was_cooked ? 'Mark as not cooked' : 'Mark as cooked'}
            aria-label={entry.was_cooked ? 'Mark as not cooked' : 'Mark as cooked'}
            className="w-6 h-6 flex items-center justify-center rounded-full bg-sage-50 dark:bg-green-900/20 text-sage-600 dark:text-green-400 hover:bg-sage-100 dark:hover:bg-green-900/30 transition-colors disabled:opacity-50"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isWorking}
            title="Delete meal"
            aria-label="Delete meal"
            className="w-6 h-6 flex items-center justify-center rounded-full bg-terracotta-50 dark:bg-red-900/20 text-terracotta-600 dark:text-red-400 hover:bg-terracotta-100 dark:hover:bg-red-900/30 transition-colors disabled:opacity-50"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    )
  }

  // Recipe variant (and custom meals): vertical text-only card, preserved as-is
  return (
    <div
      className={`${containerBase} ${containerColor} flex flex-col items-center justify-center text-center px-2 py-3 min-h-[100px]`}
      onClick={handleCardClick}
      style={pulseStyle}
    >
      {/* Participant avatars — only when non-default */}
      {showAvatars && (
        <div className="flex -space-x-1 mb-1.5">
          {participants.slice(0, 5).map((p) => (
            <MemberAvatar
              key={p.id}
              name={p.name}
              photoUrl={p.photo_url}
              color={p.color}
              size="xs"
              className="w-5 h-5 ring-2 ring-card-bg dark:ring-gray-800"
            />
          ))}
        </div>
      )}

      {/* Name — dominant element */}
      <div
        className={`
          text-base font-medium leading-tight
          ${entry.was_cooked
            ? 'line-through text-sage-600 dark:text-green-500'
            : 'text-text-primary dark:text-gray-100'
          }
        `}
      >
        {displayName}
      </div>

      {/* Metadata row */}
      {(cookTime || servings) && (
        <div className="flex items-center gap-1.5 mt-1 text-xs text-text-muted dark:text-gray-400">
          {cookTime > 0 && (
            <span className="flex items-center gap-0.5">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10" />
                <path strokeLinecap="round" d="M12 6v6l4 2" />
              </svg>
              {cookTime}m
            </span>
          )}
          {cookTime > 0 && servings && <span>·</span>}
          {servings && <span>{servings} servings</span>}
        </div>
      )}

      {/* Cooked badge */}
      {entry.was_cooked && (
        <div className="bounce-in mt-1.5 text-xs font-semibold text-sage-600 dark:text-green-400">
          ✓ Cooked
        </div>
      )}

      {/* Hover action icons — desktop: hover-reveal, mobile: always visible */}
      <div
        className="
          absolute bottom-2 left-1/2 -translate-x-1/2
          flex items-center gap-1.5
          max-md:opacity-100
          md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100
          transition-opacity duration-150
        "
      >
        {/* View recipe (only for recipe entries) */}
        {isRecipe && (
          <button
            type="button"
            onClick={handleViewRecipe}
            title="View recipe"
            aria-label="View recipe"
            className="
              w-8 h-8 flex items-center justify-center rounded-full
              bg-warm-sand dark:bg-gray-700
              border border-card-border dark:border-gray-600
              text-text-secondary dark:text-gray-300
              hover:bg-warm-beige dark:hover:bg-gray-600
              transition-colors
            "
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
            </svg>
          </button>
        )}

        {/* Cooked toggle */}
        <button
          type="button"
          onClick={handleToggleCooked}
          disabled={isWorking}
          title={entry.was_cooked ? 'Mark as not cooked' : 'Mark as cooked'}
          aria-label={entry.was_cooked ? 'Mark as not cooked' : 'Mark as cooked'}
          className="
            w-8 h-8 flex items-center justify-center rounded-full
            bg-sage-50 dark:bg-green-900/20
            text-sage-600 dark:text-green-400
            hover:bg-sage-100 dark:hover:bg-green-900/30
            transition-colors disabled:opacity-50
          "
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </button>

        {/* Delete */}
        <button
          type="button"
          onClick={handleDelete}
          disabled={isWorking}
          title="Delete meal"
          aria-label="Delete meal"
          className="
            w-8 h-8 flex items-center justify-center rounded-full
            bg-terracotta-50 dark:bg-red-900/20
            text-terracotta-600 dark:text-red-400
            hover:bg-terracotta-100 dark:hover:bg-red-900/30
            transition-colors disabled:opacity-50
          "
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  )
}
