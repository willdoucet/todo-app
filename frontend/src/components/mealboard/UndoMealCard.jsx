import { useEffect, useRef, useState } from 'react'
import useMediaQuery from '../../hooks/useMediaQuery'

const UNDO_WINDOW_MS = 5000

/**
 * In-place undo card shown in the slot a deleted meal vacated. Rendered by
 * LaneCell (desktop) and MobileDayView (mobile) via the
 * `mergeEntriesWithPendingDeletes` helper. Visual spec is the "Strikethrough
 * Continuity" variant from the Chunk 3 mockups.
 *
 * Behavior:
 *  - The whole card is the undo affordance (single <button>).
 *  - A 3px countdown bar at the bottom shrinks 100% → 0% over 5s (linear).
 *  - Under `prefers-reduced-motion`, the bar is hidden and the inline
 *    "· Ns" suffix decrements each second via setInterval instead.
 *  - Auto-focuses on mount so screen-reader users hear the affordance
 *    immediately after pressing Delete.
 *  - Double-click guard via `isSubmitting` to prevent two POST /undo requests.
 *
 * Parent (MealPlannerView) owns the 5-second timer; this component only
 * displays the countdown and calls `onUndo()` on click. When the parent's
 * timer fires, this component unmounts and the live MealCard flows back in.
 */
export default function UndoMealCard({ mealName, expiresAt, onUndo }) {
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const buttonRef = useRef(null)
  // Synchronous guard — setState re-renders aren't fast enough to debounce
  // rapid double-clicks on the same tick; the ref blocks the second call
  // before it reaches onUndo().
  const submittingRef = useRef(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const remainingMs = () => Math.max(0, expiresAt.getTime() - Date.now())
  const [secondsLeft, setSecondsLeft] = useState(Math.ceil(remainingMs() / 1000))

  // Auto-focus so the screen-reader user immediately hears the undo offer.
  useEffect(() => {
    buttonRef.current?.focus()
  }, [])

  // Reduced-motion: update the seconds-left text each second so the
  // countdown stays accessible without the animated bar.
  useEffect(() => {
    const tick = () => {
      const remaining = Math.ceil(remainingMs() / 1000)
      setSecondsLeft(remaining)
    }
    // Always update the aria-label every second; the bar is CSS-driven and
    // doesn't need a JS tick, but the aria-label + reduced-motion text do.
    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
    // expiresAt is captured at mount; subsequent re-renders reuse the same Date.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleClick = () => {
    if (submittingRef.current) return
    submittingRef.current = true
    setIsSubmitting(true)
    onUndo()
    // The parent tears this card down on success; on failure (410) it replaces
    // it with a toast. Either way, this component unmounts — no need to reset
    // the ref.
  }

  const ariaLabel = `Undo deletion of ${mealName || 'meal'}, ${secondsLeft} seconds remaining`

  return (
    <button
      ref={buttonRef}
      type="button"
      onClick={handleClick}
      disabled={isSubmitting}
      aria-label={ariaLabel}
      className={`
        group relative w-full overflow-hidden
        flex flex-col items-center justify-center text-center
        px-2 py-3 min-h-[100px]
        rounded-xl border border-card-border dark:border-gray-700
        bg-card-bg dark:bg-gray-800
        opacity-85 hover:opacity-100
        hover:border-terracotta-500 dark:hover:border-blue-500
        focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
        transition-[opacity,border-color] duration-150 ease-out
        ${isSubmitting ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'}
      `}
    >
      {/* Struck-through meal name — continuity with the live card's Cooked strike. */}
      <div
        className="
          text-base font-medium leading-tight
          text-text-muted dark:text-gray-500
          line-through decoration-[1.5px]
        "
      >
        {mealName || 'Meal'}
      </div>

      {/* Action line: arrow + "Tap to undo" + (animated bar OR · Ns fallback) */}
      <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-terracotta-600 dark:text-blue-400">
        <svg
          className="w-[13px] h-[13px]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h10a6 6 0 0 1 0 12H9" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 6l-4 4 4 4" />
        </svg>
        <span>Tap to undo</span>
        {/* Reduced-motion users see the seconds count decrement each tick.
            Motion-safe users only see the animated bar at the bottom. */}
        <span className="motion-reduce:inline hidden font-normal text-text-muted dark:text-gray-500">
          · {secondsLeft}s
        </span>
      </div>

      {/* Countdown bar — hidden under prefers-reduced-motion */}
      <span
        className="
          motion-reduce:hidden
          absolute bottom-0 left-0 right-0 h-[3px]
          bg-terracotta-100 dark:bg-blue-900/30
          overflow-hidden
        "
        aria-hidden="true"
      >
        <span
          className="
            block h-full
            bg-terracotta-500 dark:bg-blue-500
            origin-left
          "
          style={{
            animation: prefersReducedMotion
              ? 'none'
              : `undo-bar-shrink ${UNDO_WINDOW_MS}ms linear forwards`,
          }}
        />
      </span>
    </button>
  )
}
