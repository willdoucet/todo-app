import { useState, useRef, useEffect, useCallback, Suspense, lazy, Component } from 'react'
import { useDarkMode } from '../../contexts/DarkModeContext'

/**
 * Lazy-loaded emoji picker powered by emoji-mart (vanilla web component).
 *
 * Both emoji-mart and @emoji-mart/data are loaded in a single lazy boundary
 * so the Picker always has data when it mounts — no timing gap.
 *
 * Props:
 *   onSelect: (emoji: string | null) => void
 *   children: trigger element (rendered always; clicking it toggles the picker)
 */

// --- Lazy boundary: loads emoji-mart + data in parallel, returns a React wrapper ---
const LazyPickerInner = lazy(async () => {
  const [emojiMartModule, dataModule] = await Promise.all([
    import('emoji-mart'),
    import('@emoji-mart/data'),
  ])
  const PickerClass = emojiMartModule.Picker
  const data = dataModule.default

  function PickerComponent({ onEmojiSelect, theme }) {
    const containerRef = useRef(null)
    const callbackRef = useRef(onEmojiSelect)

    useEffect(() => {
      callbackRef.current = onEmojiSelect
    }, [onEmojiSelect])

    useEffect(() => {
      const node = containerRef.current
      if (!node) return
      const picker = new PickerClass({
        data,
        onEmojiSelect: (emoji) => callbackRef.current(emoji.native),
        theme: theme === 'dark' ? 'dark' : 'light',
        categories: ['frequent', 'foods', 'nature', 'activity', 'objects'],
        maxFrequentRows: 2,
        previewPosition: 'none',
      })
      node.appendChild(picker)
      return () => {
        node.innerHTML = ''
      }
    }, [theme])

    return <div ref={containerRef} className="max-h-80 overflow-hidden rounded-b-xl" />
  }

  return { default: PickerComponent }
})

// --- Error boundary with retry ---
class PickerErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  handleRetry = () => {
    this.setState({ hasError: false })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-80 rounded-xl bg-warm-sand dark:bg-gray-700 gap-2">
          <span className="text-xs text-text-muted dark:text-gray-500">Failed to load emojis</span>
          <button
            type="button"
            onClick={this.handleRetry}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-terracotta-500 dark:bg-blue-600 text-white hover:bg-terracotta-600 dark:hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

// --- Suspense skeleton ---
function PickerSkeleton() {
  return (
    <div className="flex items-center justify-center h-80 rounded-xl bg-warm-sand dark:bg-gray-700 animate-pulse">
      <span className="text-xs text-text-muted dark:text-gray-500">Loading emojis…</span>
    </div>
  )
}

// --- Main component ---
export default function EmojiPicker({ onSelect, children }) {
  const [open, setOpen] = useState(false)
  const panelRef = useRef(null)
  const triggerRef = useRef(null)
  const { isDark } = useDarkMode()

  // Close on click-outside
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (
        panelRef.current && !panelRef.current.contains(e.target) &&
        triggerRef.current && !triggerRef.current.contains(e.target)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Close on Escape (picker-first: stops propagation so the parent Dialog doesn't close)
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        setOpen(false)
      }
    }
    // Use capture phase so we intercept before the Dialog's listener
    document.addEventListener('keydown', handler, true)
    return () => document.removeEventListener('keydown', handler, true)
  }, [open])

  const handleSelect = useCallback((emoji) => {
    onSelect(emoji)
    setOpen(false)
  }, [onSelect])

  const handleClear = useCallback(() => {
    onSelect(null)
    setOpen(false)
  }, [onSelect])

  return (
    <div className="relative inline-block">
      <div ref={triggerRef} onClick={() => setOpen(!open)} className="cursor-pointer">
        {children}
      </div>

      {open && (
        <div
          ref={panelRef}
          className="
            absolute z-50 mt-2 left-0
            bg-card-bg dark:bg-gray-800
            border border-card-border dark:border-gray-700
            rounded-xl shadow-lg
            overflow-hidden
          "
          role="dialog"
          aria-label="Choose an emoji"
        >
          {/* Clear row — above the picker's search */}
          <div className="flex justify-end px-3 pt-2 pb-1">
            <button
              type="button"
              onClick={handleClear}
              className="p-2 text-xs text-text-muted hover:text-terracotta-600 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
            >
              Clear
            </button>
          </div>

          <PickerErrorBoundary>
            <Suspense fallback={<PickerSkeleton />}>
              <LazyPickerInner
                onEmojiSelect={handleSelect}
                theme={isDark ? 'dark' : 'light'}
              />
            </Suspense>
          </PickerErrorBoundary>
        </div>
      )}
    </div>
  )
}
