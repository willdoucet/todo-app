import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { Transition } from '@headlessui/react'
import ItemIcon from '../mealboard/ItemIcon'

/**
 * Singleton undo toast for the soft-delete flow (Expansion B).
 *
 * Design follows mockup `undo-toast-option-a.html` — horizontal pill at bottom-center,
 * slots: ItemIcon · label · countdown ring · Undo button · dismiss (✕).
 *
 * Usage:
 *   1. Wrap the app (or mealboard) in <UndoToastProvider>.
 *   2. From anywhere inside, call `const { show } = useUndoToast()` and invoke
 *      `show({ item, undoToken, onUndo, onExpire })` right after the DELETE response.
 *   3. The provider manages the 15-second countdown, Undo click, and dismiss.
 *
 * States:
 *   - active: countdown ring visible, Undo button enabled
 *   - restoring: spinner replaces Undo, other slots unchanged (optimistic)
 *   - hidden: no toast rendered
 *
 * At most one toast is visible at a time. New show() calls replace the current one
 * (no stacking, no queuing — simpler than the Chunk 6 full spec, sufficient for this
 * refactor's DELETE flow).
 */

const UNDO_WINDOW_MS = 15_000

const UndoToastContext = createContext(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useUndoToast() {
  const ctx = useContext(UndoToastContext)
  if (!ctx) {
    throw new Error('useUndoToast must be used inside <UndoToastProvider>')
  }
  return ctx
}

export function UndoToastProvider({ children }) {
  const [toast, setToast] = useState(null)
  const [restoring, setRestoring] = useState(false)
  const expireTimerRef = useRef(null)
  const expiresAtRef = useRef(null)
  const onExpireRef = useRef(null)

  const clearTimers = () => {
    if (expireTimerRef.current) {
      clearTimeout(expireTimerRef.current)
      expireTimerRef.current = null
    }
    expiresAtRef.current = null
    onExpireRef.current = null
  }

  const hide = useCallback(() => {
    clearTimers()
    setToast(null)
    setRestoring(false)
  }, [])

  const show = useCallback(({ item, undoToken, onUndo, onExpire }) => {
    clearTimers()
    setToast({ item, undoToken, onUndo, onExpire })
    setRestoring(false)
    onExpireRef.current = onExpire || null
    expiresAtRef.current = Date.now() + UNDO_WINDOW_MS

    expireTimerRef.current = setTimeout(() => {
      if (onExpireRef.current) {
        try { onExpireRef.current() } catch { /* swallow */ }
      }
      hide()
    }, UNDO_WINDOW_MS)
  }, [hide])

  // Background-tab catch-up: browsers throttle setTimeout in backgrounded tabs.
  // If the user switches away and comes back after the window expired, dismiss
  // immediately instead of waiting for the delayed timer to fire.
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (
        document.visibilityState === 'visible' &&
        expiresAtRef.current !== null &&
        Date.now() >= expiresAtRef.current
      ) {
        if (onExpireRef.current) {
          try { onExpireRef.current() } catch { /* swallow */ }
        }
        hide()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [hide])

  const handleUndoClick = useCallback(async () => {
    if (!toast || restoring) return
    setRestoring(true)
    try {
      await toast.onUndo(toast.undoToken)
      hide()
    } catch (err) {
      console.warn('Undo failed:', err)
      hide()
    }
  }, [toast, restoring, hide])

  // Cleanup on unmount
  useEffect(() => () => clearTimers(), [])

  const value = { show, hide }

  return (
    <UndoToastContext.Provider value={value}>
      {children}
      <Transition
        show={toast !== null}
        enter="transition ease-out duration-200"
        enterFrom="opacity-0 translate-y-2"
        enterTo="opacity-100 translate-y-0"
        leave="transition ease-in duration-150"
        leaveFrom="opacity-100 translate-y-0"
        leaveTo="opacity-0 translate-y-2"
      >
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="
            fixed bottom-6 left-1/2 -translate-x-1/2 z-[110]
            flex items-center gap-3
            max-w-md mx-4 rounded-xl px-4 py-3 shadow-xl
            bg-text-primary dark:bg-gray-800 text-white
          "
        >
          {toast && (
            <>
              {/* Slot 1: Icon */}
              <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center">
                <ItemIcon item={toast.item} size={22} />
              </div>

              {/* Slot 2: Label */}
              <span className="text-sm font-medium whitespace-nowrap">
                {labelFor(toast.item)}
              </span>

              {/* Slot 3: Countdown ring (or hidden while restoring) */}
              {!restoring && <CountdownRing />}

              {/* Slot 4: Action — Undo button (or spinner during restore) */}
              {restoring ? (
                <Spinner />
              ) : (
                <button
                  type="button"
                  onClick={handleUndoClick}
                  className="
                    px-3 py-1 rounded-md
                    bg-terracotta-500 hover:bg-terracotta-600
                    dark:bg-blue-600 dark:hover:bg-blue-700
                    text-white text-sm font-medium
                    focus:outline-none focus:ring-2 focus:ring-white/50
                  "
                  aria-label={`Undo deletion of ${toast.item?.name || 'item'}`}
                >
                  Undo
                </button>
              )}

              {/* Slot 5: Dismiss */}
              <button
                type="button"
                onClick={hide}
                className="p-1 rounded text-white/70 hover:text-white focus:outline-none focus:ring-2 focus:ring-white/50"
                aria-label="Dismiss"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </>
          )}
        </div>
      </Transition>
    </UndoToastContext.Provider>
  )
}

function labelFor(item) {
  if (!item) return 'Item deleted'
  if (item.item_type === 'recipe') return 'Recipe deleted'
  if (item.item_type === 'food_item') return 'Food item deleted'
  return 'Item deleted'
}

// Pure-CSS countdown ring — animates stroke-dashoffset over 15s via a
// keyframe defined in index.css (`undo-countdown`). React doesn't re-render
// during the animation; the browser compositor handles it for free.
function CountdownRing() {
  const c = 37.7
  return (
    <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="6" stroke="rgba(255,255,255,0.2)" strokeWidth="2" fill="none" />
      <circle
        cx="8" cy="8" r="6"
        stroke="white" strokeWidth="2" fill="none"
        strokeDasharray={c}
        transform="rotate(-90 8 8)"
        style={{
          animation: `undo-countdown ${UNDO_WINDOW_MS}ms linear forwards`,
        }}
      />
    </svg>
  )
}

function Spinner() {
  return (
    <svg className="w-4 h-4 flex-shrink-0 animate-spin" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="6" stroke="rgba(255,255,255,0.2)" strokeWidth="2" fill="none" />
      <path d="M 8 2 A 6 6 0 0 1 14 8" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  )
}
