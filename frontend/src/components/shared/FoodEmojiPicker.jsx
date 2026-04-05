import { useState, useRef, useEffect } from 'react'
import { CURATED_FOOD_EMOJIS } from '../../constants/foodEmojis'

/**
 * Curated food emoji picker. Grid of ~50 food-relevant emojis grouped by category.
 *
 * Props:
 *   selected: current emoji (string, optional)
 *   onSelect: (emoji) => void
 *   children: trigger element (usually a button showing the current emoji)
 */
export default function FoodEmojiPicker({ selected, onSelect, children }) {
  const [open, setOpen] = useState(false)
  const panelRef = useRef(null)
  const triggerRef = useRef(null)

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

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  const handlePick = (emoji) => {
    onSelect(emoji)
    setOpen(false)
  }

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
            w-72 max-h-80 overflow-y-auto
            bg-card-bg dark:bg-gray-800
            border border-card-border dark:border-gray-700
            rounded-xl shadow-lg
            p-3
          "
          role="dialog"
          aria-label="Choose a food emoji"
        >
          {CURATED_FOOD_EMOJIS.map((group) => (
            <div key={group.label} className="mb-3 last:mb-0">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted dark:text-gray-400 mb-1.5 px-1">
                {group.label}
              </div>
              <div className="grid grid-cols-8 gap-1">
                {group.emojis.map((emoji) => (
                  <button
                    key={emoji}
                    type="button"
                    onClick={() => handlePick(emoji)}
                    className={`
                      w-7 h-7 flex items-center justify-center rounded-md text-base
                      hover:bg-warm-beige dark:hover:bg-gray-700 transition-colors
                      ${selected === emoji ? 'bg-peach-100 dark:bg-blue-900/40 ring-1 ring-terracotta-500 dark:ring-blue-500' : ''}
                    `}
                    aria-label={`Choose ${emoji}`}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </div>
          ))}

          <div className="pt-2 mt-2 border-t border-card-border dark:border-gray-700">
            <button
              type="button"
              onClick={() => handlePick(null)}
              className="text-xs text-text-muted dark:text-gray-400 hover:text-text-secondary dark:hover:text-gray-300"
            >
              Clear emoji
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
