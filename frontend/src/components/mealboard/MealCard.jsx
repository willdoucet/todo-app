import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import MemberAvatar from '../shared/MemberAvatar'
import ItemIcon from './ItemIcon'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Meal card for the swimlane grid. Branches on `entry.item?.item_type`:
 *
 * - Recipe variant — vertical card: body (name, cook-time pill, cooked badge)
 *   plus a hover-expand action zone that reveals Mark-cooked + Delete on
 *   desktop hover/focus. Mobile keeps the zone permanently visible.
 * - Food-item variant — same outer chrome and hover-expand structure; body is
 *   a vertical stack (ItemIcon 24px centered on top, name below, optional
 *   avatars + cooked-✓ mini-row). Button chip scales with the smaller body
 *   (24×24 visible) vs. recipe (32×32); outer <button> is 44×44 in both
 *   variants to hit WCAG 2.5.5 AAA.
 *
 * Both variants render a role="status" aria-live="polite" inline error
 * element (auto-clears after 3s) below the action zone — kept OUTSIDE the
 * collapsible action-zone container so desktop mouse-leave after a failed
 * click cannot clip the error before the user reads it.
 */

// 44×44 WCAG 2.5.5 AAA tap target wrapping a variant-sized visible chip.
// Local to MealCard: used by both recipe and food-item action zones.
function CardActionButton({ onClick, disabled, label, variant, size, children }) {
  const chipSize = size === 'sm' ? 'w-6 h-6' : 'w-8 h-8'
  const chipColor = variant === 'cooked'
    ? 'bg-sage-50 dark:bg-green-900/20 text-sage-600 dark:text-green-400 group-hover/btn:bg-sage-100 dark:group-hover/btn:bg-green-900/30'
    : 'bg-terracotta-50 dark:bg-red-900/20 text-terracotta-600 dark:text-red-400 group-hover/btn:bg-terracotta-100 dark:group-hover/btn:bg-red-900/30'
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className="group/btn w-11 h-11 flex items-center justify-center rounded-full disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-terracotta-500 dark:focus-visible:outline-terracotta-400"
    >
      <span className={`${chipSize} flex items-center justify-center rounded-full transition-colors ${chipColor}`}>
        {children}
      </span>
    </button>
  )
}

// Inline status message for failed PATCH/DELETE. Rendered as a sibling of the
// action-zone div (not inside it) so desktop mouse-leave after a failed click
// doesn't clip the message before the 3-second window ends.
function CardErrorFlash({ kind }) {
  if (!kind) return null
  return (
    <div
      role="status"
      aria-live="polite"
      className="px-2 pb-1.5 text-[11px] text-terracotta-600 dark:text-red-400 text-center"
    >
      {kind === 'gone' ? 'This meal was already deleted.' : "Couldn't save — try again."}
    </div>
  )
}

export default function MealCard({ entry, slotType, familyMembers, onUpdated, onDeleted, onViewRecipe }) {
  const [isWorking, setIsWorking] = useState(false)
  const [isPulsing, setIsPulsing] = useState(false)
  const [lastError, setLastError] = useState(null)
  const errorTimerRef = useRef(null)

  // Unified item model: entry.item replaces entry.recipe + entry.food_item
  const item = entry.item || null
  const isRecipe = item?.item_type === 'recipe'
  const isFoodItem = item?.item_type === 'food_item'
  const displayName = item?.name || entry.custom_meal_name || 'Untitled meal'

  const rd = item?.recipe_detail || {}
  const cookTime = isRecipe ? (rd.prep_time_minutes || 0) + (rd.cook_time_minutes || 0) : null

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

  const flashError = (kind) => {
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
    setLastError(kind)
    errorTimerRef.current = setTimeout(() => {
      setLastError(null)
      errorTimerRef.current = null
    }, 3000)
  }

  useEffect(() => () => {
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
  }, [])

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
      if (lastError) setLastError(null)
      onUpdated(res.data)
    } catch (err) {
      console.error('meal_card_toggle_cooked_failed', {
        entryId: entry.id,
        status: err?.response?.status ?? null,
        err,
      })
      flashError(err?.response?.status === 404 ? 'gone' : 'retry')
    } finally {
      setIsWorking(false)
    }
  }

  const handleDelete = async (e) => {
    e.stopPropagation()
    if (isWorking) return
    setIsWorking(true)
    try {
      const res = await axios.delete(`${API_BASE}/meal-entries/${entry.id}`)
      // New backend: `{ entry, undo_token, expires_at }`.
      // Mixed-version guard: if `undo_token` is missing (briefly-old backend),
      // degrade to the old hard-delete UX rather than blocking the user.
      const undoToken = res?.data?.undo_token
      const expiresAt = res?.data?.expires_at
      if (lastError) setLastError(null)
      if (undoToken && expiresAt) {
        onDeleted(entry.id, { undoToken, expiresAt, entry })
      } else {
        console.error('delete_missing_undo_token', entry.id)
        onDeleted(entry.id)
      }
    } catch (err) {
      console.error('meal_card_delete_failed', {
        entryId: entry.id,
        status: err?.response?.status ?? null,
        err,
      })
      flashError(err?.response?.status === 404 ? 'gone' : 'retry')
      setIsWorking(false)
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

  // Shared action-zone className string (verbatim between variants).
  const actionZoneClass = `
    flex justify-center gap-1.5 pb-2 pt-0
    max-md:max-h-[48px] max-md:opacity-100
    md:max-h-0 md:opacity-0 md:pb-0
    md:group-hover:max-h-[48px] md:group-hover:opacity-100 md:group-hover:pb-2
    md:group-focus-within:max-h-[48px] md:group-focus-within:opacity-100 md:group-focus-within:pb-2
    motion-safe:transition-[max-height,opacity,padding-bottom]
    motion-safe:duration-180 motion-safe:ease-out
  `

  // Food-item variant: vertical layout — ItemIcon (24px) on top, name centered
  // below, optional avatars + cooked-✓ inline mini-row, then a hover-expand
  // action zone identical in structure to the recipe variant. Body min-h-[52px]
  // (taller than the 48px pill it replaces); buttons stay 24×24 (smaller than
  // recipe's 32×32) so they scale with the smaller body. The "≤60% recipe
  // baseline" goal from the original Chunk 2 was retired in plan §20260418-183015.
  if (isFoodItem) {
    return (
      <div
        className={`${containerBase} ${containerColor} flex flex-col overflow-hidden`}
        onClick={handleCardClick}
        style={pulseStyle}
        data-testid="meal-card"
        data-variant="food_item"
        data-entry-id={entry.id}
      >
        <div className="flex flex-col items-center justify-center text-center px-2 py-2 min-h-[52px]">
          <ItemIcon item={item} size={24} />
          <div
            className={`mt-1 text-sm font-medium leading-tight text-center line-clamp-2 ${
              entry.was_cooked
                ? 'line-through text-sage-600 dark:text-green-500'
                : 'text-text-primary dark:text-gray-100'
            }`}
          >
            {displayName}
          </div>
          {(showAvatars || entry.was_cooked) && (
            <div className="flex items-center justify-center gap-1 mt-0.5">
              {showAvatars && participants.slice(0, 3).map((p) => (
                <MemberAvatar
                  key={p.id}
                  name={p.name}
                  photoUrl={p.photo_url}
                  color={p.color}
                  size="xs"
                  className="w-4 h-4 ring-2 ring-card-bg dark:ring-gray-800"
                />
              ))}
              {entry.was_cooked && (
                <span className="bounce-in text-[10px] font-semibold text-sage-600 dark:text-green-400">✓</span>
              )}
            </div>
          )}
        </div>

        <div className={actionZoneClass}>
          <CardActionButton
            onClick={handleToggleCooked}
            disabled={isWorking}
            label={entry.was_cooked ? 'Mark as not cooked' : 'Mark as cooked'}
            variant="cooked"
            size="sm"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </CardActionButton>
          <CardActionButton
            onClick={handleDelete}
            disabled={isWorking}
            label="Delete meal"
            variant="delete"
            size="sm"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </CardActionButton>
        </div>

        <CardErrorFlash kind={lastError} />
      </div>
    )
  }

  // Recipe variant (and custom meals): body holds content at min-h-[100px], action
  // zone below expands on hover/focus (desktop) or is permanently visible (mobile).
  // Expansion uses max-height + opacity transitions; motion-safe: gates the
  // motion on prefers-reduced-motion.
  return (
    <div
      className={`${containerBase} ${containerColor} flex flex-col overflow-hidden`}
      onClick={handleCardClick}
      style={pulseStyle}
      data-testid="meal-card"
      data-variant="recipe"
      data-entry-id={entry.id}
    >
      {/* Card body — sized to preserve the pre-Chunk-2 baseline look */}
      <div className="flex flex-col items-center justify-center text-center px-2 py-3 min-h-[100px]">
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

        {/* Metadata row — cook-time only, centered */}
        {cookTime > 0 && (
          <div className="flex items-center justify-center gap-0.5 mt-1 text-xs text-text-muted dark:text-gray-400">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10" />
              <path strokeLinecap="round" d="M12 6v6l4 2" />
            </svg>
            {cookTime}m
          </div>
        )}

        {/* Cooked badge */}
        {entry.was_cooked && (
          <div className="bounce-in mt-1.5 text-xs font-semibold text-sage-600 dark:text-green-400">
            ✓ Cooked
          </div>
        )}
      </div>

      <div className={actionZoneClass}>
        <CardActionButton
          onClick={handleToggleCooked}
          disabled={isWorking}
          label={entry.was_cooked ? 'Mark as not cooked' : 'Mark as cooked'}
          variant="cooked"
          size="md"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </CardActionButton>
        <CardActionButton
          onClick={handleDelete}
          disabled={isWorking}
          label="Delete meal"
          variant="delete"
          size="md"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </CardActionButton>
      </div>

      <CardErrorFlash kind={lastError} />
    </div>
  )
}
