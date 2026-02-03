import { useState, useRef } from 'react'
import { useSwipeable } from 'react-swipeable'

/**
 * A wrapper component that adds swipe-to-action functionality.
 * Swipe left to reveal action button (delete/complete).
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - The content to wrap
 * @param {Function} props.onSwipeAction - Called when swipe action is triggered
 * @param {string} [props.actionType='delete'] - Type of action: 'delete' or 'complete'
 * @param {string} [props.actionLabel] - Label for the action button
 * @param {boolean} [props.disabled=false] - Disable swipe functionality
 */
export default function SwipeableItem({
  children,
  onSwipeAction,
  actionType = 'delete',
  actionLabel,
  disabled = false,
}) {
  const [offset, setOffset] = useState(0)
  const [isRevealed, setIsRevealed] = useState(false)
  const containerRef = useRef(null)

  const ACTION_THRESHOLD = 80 // pixels to reveal action
  const TRIGGER_THRESHOLD = 150 // pixels to auto-trigger action

  const actionConfig = {
    delete: {
      label: actionLabel || 'Delete',
      bgColor: 'bg-red-500',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      ),
    },
    complete: {
      label: actionLabel || 'Done',
      bgColor: 'bg-green-500',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ),
    },
  }

  const config = actionConfig[actionType] || actionConfig.delete

  const handlers = useSwipeable({
    onSwiping: (eventData) => {
      if (disabled) return

      // Only allow swiping left (negative deltaX)
      if (eventData.deltaX < 0) {
        const newOffset = Math.min(0, eventData.deltaX)
        setOffset(Math.max(newOffset, -TRIGGER_THRESHOLD - 20))
      }
    },
    onSwipedLeft: (eventData) => {
      if (disabled) return

      if (Math.abs(eventData.deltaX) >= TRIGGER_THRESHOLD) {
        // Auto-trigger action
        triggerAction()
      } else if (Math.abs(eventData.deltaX) >= ACTION_THRESHOLD) {
        // Reveal action button
        setOffset(-ACTION_THRESHOLD)
        setIsRevealed(true)
      } else {
        // Snap back
        resetPosition()
      }
    },
    onSwipedRight: () => {
      if (disabled) return
      resetPosition()
    },
    onTouchEndOrOnMouseUp: () => {
      // If not revealed and offset is small, snap back
      if (!isRevealed && Math.abs(offset) < ACTION_THRESHOLD) {
        resetPosition()
      }
    },
    trackMouse: false, // Only track touch on mobile
    trackTouch: true,
    delta: 10, // Minimum distance before swiping starts
    preventScrollOnSwipe: true,
  })

  const resetPosition = () => {
    setOffset(0)
    setIsRevealed(false)
  }

  const triggerAction = () => {
    // Animate off screen then trigger
    setOffset(-300)
    setTimeout(() => {
      onSwipeAction?.()
      resetPosition()
    }, 200)
  }

  const handleActionClick = () => {
    triggerAction()
  }

  // Close when clicking outside (on the item itself when revealed)
  const handleContentClick = () => {
    if (isRevealed) {
      resetPosition()
    }
  }

  // Don't render swipe UI on desktop (sm and up)
  return (
    <div className="relative overflow-hidden sm:overflow-visible" ref={containerRef}>
      {/* Action button - only visible on mobile */}
      <div
        className={`
          sm:hidden absolute inset-y-0 right-0 flex items-center justify-center
          ${config.bgColor} text-white
          transition-opacity duration-150
          ${Math.abs(offset) > 20 ? 'opacity-100' : 'opacity-0'}
        `}
        style={{ width: ACTION_THRESHOLD }}
      >
        <button
          onClick={handleActionClick}
          className="flex flex-col items-center justify-center gap-1 w-full h-full"
          aria-label={config.label}
        >
          {config.icon}
          <span className="text-xs font-medium">{config.label}</span>
        </button>
      </div>

      {/* Content wrapper with swipe handlers */}
      <div
        {...handlers}
        onClick={handleContentClick}
        className="relative bg-inherit transition-transform duration-150 ease-out sm:transform-none"
        style={{
          transform: `translateX(${offset}px)`,
          // Disable transition during active swiping for responsiveness
          transitionDuration: offset === 0 || offset === -ACTION_THRESHOLD ? '150ms' : '0ms',
        }}
      >
        {children}
      </div>
    </div>
  )
}
