import { useState, useEffect, useRef, useMemo } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import ShoppingLinkModal from './ShoppingLinkModal'

const OVERFLOW_ITEMS = [
  { key: 'change', label: 'Change list', icon: '🔄' },
  { key: 'unlink', label: 'Unlink', icon: '🔗' },
]

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// How long to poll after a meal add/remove to catch Celery sync completion
const POLL_DURATION_MS = 30000
const POLL_INTERVAL_MS = 5000

/**
 * Shopping list card in the top bar. States:
 * 1. No list linked → "Add a shopping list" → opens link modal
 * 2. List linked, has items → "{N} items on shopping list" → navigates to list
 * 3. List linked, empty → "Shopping list empty" → navigates to list
 *
 * Also shows a warning indicator if any meal entries have shopping_sync_status="failed".
 * Clicking the warning shows the list of failed meals with a retry option.
 */
export default function ShoppingCard({ settings, onSettingsChange, mealEntries = [], onRetrySync }) {
  const [itemCount, setItemCount] = useState(null)
  const [linkedListName, setLinkedListName] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [warningOpen, setWarningOpen] = useState(false)
  const [overflowOpen, setOverflowOpen] = useState(false)
  const [syncPending, setSyncPending] = useState(false)
  const warningPanelRef = useRef(null)
  const warningTriggerRef = useRef(null)
  const overflowRef = useRef(null)
  const navigate = useNavigate()

  const listId = settings?.mealboard_shopping_list_id

  // Identify failed meals from the current week
  const failedMeals = useMemo(
    () => mealEntries.filter((e) => e.shopping_sync_status === 'failed'),
    [mealEntries]
  )

  // Identify pending meals
  const pendingMeals = useMemo(
    () => mealEntries.filter((e) => e.shopping_sync_status === 'pending'),
    [mealEntries]
  )

  const refreshCount = async () => {
    if (!listId) return
    try {
      const [listRes, tasksRes] = await Promise.all([
        axios.get(`${API_BASE}/lists/${listId}`),
        axios.get(`${API_BASE}/tasks?list_id=${listId}`),
      ])
      setLinkedListName(listRes.data.name)
      setItemCount(tasksRes.data.filter((t) => !t.completed).length)
    } catch (err) {
      if (err.response?.status === 404) {
        // Linked list was deleted — clear the link
        try {
          const res = await axios.patch(`${API_BASE}/app-settings/`, {
            mealboard_shopping_list_id: null,
          })
          onSettingsChange(res.data)
        } catch (e) {
          console.error('Failed to clear stale list link:', e)
        }
      } else {
        console.error('Failed to load shopping list:', err)
      }
    }
  }

  // Auto-refresh count on meal entry changes + short poll after changes (catches Celery async)
  useEffect(() => {
    if (!listId) {
      setItemCount(null)
      setLinkedListName(null)
      return
    }
    refreshCount()

    // Start polling if any meals are pending (Celery still processing)
    if (pendingMeals.length > 0) {
      setSyncPending(true)
      const startTime = Date.now()
      const interval = setInterval(() => {
        refreshCount()
        if (onRetrySync) onRetrySync() // refetch meal_entries to clear pending status
        if (Date.now() - startTime >= POLL_DURATION_MS) {
          clearInterval(interval)
          setSyncPending(false)
        }
      }, POLL_INTERVAL_MS)
      return () => {
        clearInterval(interval)
        setSyncPending(false)
      }
    } else {
      setSyncPending(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listId, mealEntries.length, pendingMeals.length])

  // Close warning panel on click-outside / Escape
  useEffect(() => {
    if (!warningOpen) return
    const handleClick = (e) => {
      if (
        warningPanelRef.current && !warningPanelRef.current.contains(e.target) &&
        warningTriggerRef.current && !warningTriggerRef.current.contains(e.target)
      ) {
        setWarningOpen(false)
      }
    }
    const handleKey = (e) => {
      if (e.key === 'Escape') setWarningOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [warningOpen])

  const handleClick = () => {
    if (!listId) {
      setModalOpen(true)
    } else {
      navigate(`/lists?listId=${listId}`)
    }
  }

  const handleRetryMeal = async () => {
    try {
      // Stub: real re-dispatch would PATCH the meal entry to reset
      // shopping_sync_status to "pending"; for now we just refetch the
      // current meal list so the parent picks up any backend-side changes.
      if (onRetrySync) onRetrySync()
    } catch (err) {
      console.error('Failed to retry sync:', err)
    }
  }

  const handleListLinked = (updatedSettings) => {
    onSettingsChange(updatedSettings)
    setModalOpen(false)
  }

  const handleUnlink = async () => {
    setOverflowOpen(false)
    try {
      const res = await axios.patch(`${API_BASE}/app-settings/`, {
        mealboard_shopping_list_id: null,
      })
      onSettingsChange(res.data)
    } catch (err) {
      console.error('Failed to unlink shopping list:', err)
    }
  }

  const handleOverflowAction = (key) => {
    setOverflowOpen(false)
    if (key === 'change') {
      setModalOpen(true)
    } else if (key === 'unlink') {
      handleUnlink()
    }
  }

  // Close overflow menu on click outside
  useEffect(() => {
    if (!overflowOpen) return
    const handler = (e) => {
      if (overflowRef.current && !overflowRef.current.contains(e.target)) {
        setOverflowOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [overflowOpen])

  // Format meal name for display in the warning panel
  const formatMealName = (meal) => {
    if (meal.item?.name) return meal.item.name
    return meal.custom_meal_name || 'Untitled meal'
  }

  const formatMealDate = (dateStr) => {
    const d = new Date(dateStr + 'T00:00:00')
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  }

  // Determine display content (the count gets its own styling)
  let displayContent = <>🛒 Add a shopping list</>
  if (listId) {
    if (itemCount === null) {
      displayContent = <>🛒 Loading...</>
    } else if (itemCount === 0) {
      displayContent = <>🛒 Shopping list empty</>
    } else {
      displayContent = (
        <>
          🛒{' '}
          <span className="font-bold text-terracotta-500 dark:text-blue-400">{itemCount}</span>
          {' '}item{itemCount === 1 ? '' : 's'} in shopping list
        </>
      )
    }
  }

  const hasFailures = failedMeals.length > 0

  // Don't render until settings have loaded — prevents flash of "Add a shopping list"
  if (!settings) return null

  return (
    <div className="relative flex items-center gap-2" style={{ animation: 'swimlane-enter 0.4s ease-out both' }}>
      {/* Main shopping card button */}
      <button
        type="button"
        onClick={handleClick}
        className={`
          relative px-4 py-2 rounded-2xl
          bg-card-bg dark:bg-gray-800
          border border-card-border dark:border-gray-700
          hover:border-terracotta-500 dark:hover:border-blue-500
          text-sm font-medium text-text-secondary dark:text-gray-300
          hover:text-terracotta-600 dark:hover:text-blue-400
          whitespace-nowrap transition-all
          flex items-center gap-2
        `}
        title={listId ? `Open ${linkedListName}` : 'Link a shopping list to auto-sync meal ingredients'}
      >
        {displayContent}
        {/* Pulsing dot for pending sync */}
        {syncPending && !hasFailures && (
          <span
            className="w-2 h-2 rounded-full bg-amber-400 dark:bg-amber-300 animate-pulse"
            title="Syncing shopping items..."
          />
        )}
      </button>

      {/* Overflow menu (⋯) — shown only when a list is linked */}
      {listId && (
        <div className="relative" ref={overflowRef}>
          <button
            type="button"
            onClick={() => setOverflowOpen(!overflowOpen)}
            className="
              p-2 rounded-lg
              text-text-muted dark:text-gray-500
              hover:bg-warm-beige dark:hover:bg-gray-700
              hover:text-text-secondary dark:hover:text-gray-300
              transition-colors
            "
            aria-label="Shopping list options"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M6 10a2 2 0 11-4 0 2 2 0 014 0zm6 0a2 2 0 11-4 0 2 2 0 014 0zm6 0a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </button>
          {overflowOpen && (
            <div
              className="
                absolute top-full right-0 mt-1 z-50
                min-w-[140px]
                bg-card-bg dark:bg-gray-800
                border border-card-border dark:border-gray-700
                rounded-lg shadow-xl
                py-1 overflow-hidden origin-top-right
              "
              style={{ animation: 'view-crossfade 150ms ease both, scale-pop 150ms ease both' }}
              role="menu"
            >
              {OVERFLOW_ITEMS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => handleOverflowAction(item.key)}
                  className="
                    w-full flex items-center gap-2 px-3 py-2
                    text-sm text-text-secondary dark:text-gray-300
                    hover:bg-warm-beige dark:hover:bg-gray-700
                    transition-colors text-left
                  "
                  role="menuitem"
                >
                  <span className="text-xs">{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Failure warning button */}
      {hasFailures && (
        <>
          <button
            ref={warningTriggerRef}
            type="button"
            onClick={() => setWarningOpen(!warningOpen)}
            className="
              relative flex items-center gap-1 px-2 py-2 rounded-xl
              bg-orange-50 dark:bg-orange-900/20
              border border-orange-300 dark:border-orange-700
              text-xs font-semibold text-orange-700 dark:text-orange-400
              hover:bg-orange-100 dark:hover:bg-orange-900/30
              transition-colors
            "
            aria-label={`${failedMeals.length} shopping sync failure${failedMeals.length === 1 ? '' : 's'}`}
          >
            <span className="w-2 h-2 rounded-full bg-orange-500 dark:bg-orange-400 animate-pulse" />
            <span>⚠ {failedMeals.length}</span>
          </button>

          {warningOpen && (
            <div
              ref={warningPanelRef}
              className="
                absolute top-full left-0 mt-2 z-50
                w-[min(360px,calc(100vw-2rem))]
                bg-card-bg dark:bg-gray-800
                border border-card-border dark:border-gray-700
                rounded-xl shadow-xl
                p-3
              "
              role="dialog"
              aria-label="Shopping sync failures"
            >
              <div className="text-sm font-bold text-text-primary dark:text-gray-100 mb-1">
                Shopping sync issues
              </div>
              <p className="text-xs text-text-muted dark:text-gray-400 mb-3">
                These meals' ingredients didn't make it to your shopping list:
              </p>

              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {failedMeals.map((meal) => (
                  <div
                    key={meal.id}
                    className="
                      flex items-center gap-2 px-2 py-1.5 rounded-lg
                      bg-orange-50 dark:bg-orange-900/10
                      border border-orange-200 dark:border-orange-800
                    "
                  >
                    <span className="text-orange-500 dark:text-orange-400 text-sm">⚠</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-text-primary dark:text-gray-100 truncate">
                        {formatMealName(meal)}
                      </div>
                      <div className="text-[10px] text-text-muted dark:text-gray-400">
                        {formatMealDate(meal.date)}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleRetryMeal}
                      className="
                        text-[10px] font-semibold px-2 py-1 rounded
                        bg-orange-500 dark:bg-orange-600 text-white
                        hover:bg-orange-600 dark:hover:bg-orange-700
                        transition-colors
                      "
                    >
                      Retry
                    </button>
                  </div>
                ))}
              </div>

              <div className="mt-2 pt-2 border-t border-card-border dark:border-gray-700">
                <p className="text-[10px] text-text-muted dark:text-gray-500">
                  Sync retries automatically 3 times. If it still fails, the linked list may be unavailable.
                </p>
              </div>
            </div>
          )}
        </>
      )}

      <ShoppingLinkModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onLinked={handleListLinked}
      />
    </div>
  )
}
