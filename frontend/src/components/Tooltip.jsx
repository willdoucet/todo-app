import { useState, useRef, useEffect, useCallback } from 'react'

/**
 * Tooltip component that shows on hover (desktop) and long-press (mobile).
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - The trigger element
 * @param {string} props.content - The tooltip text content
 * @param {string} [props.position='top'] - Position: 'top', 'bottom', 'left', 'right'
 * @param {number} [props.delay=300] - Hover delay in ms before showing
 * @param {number} [props.longPressDelay=500] - Long press delay in ms for mobile
 * @param {boolean} [props.disabled=false] - Disable tooltip
 */
export default function Tooltip({
  children,
  content,
  position = 'top',
  delay = 300,
  longPressDelay = 500,
  disabled = false,
}) {
  const [isVisible, setIsVisible] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 })
  const triggerRef = useRef(null)
  const tooltipRef = useRef(null)
  const hoverTimeoutRef = useRef(null)
  const longPressTimeoutRef = useRef(null)

  // Calculate tooltip position
  const calculatePosition = useCallback(() => {
    if (!triggerRef.current || !tooltipRef.current) return

    const triggerRect = triggerRef.current.getBoundingClientRect()
    const tooltipRect = tooltipRef.current.getBoundingClientRect()
    const padding = 8

    let top = 0
    let left = 0

    switch (position) {
      case 'top':
        top = triggerRect.top - tooltipRect.height - padding
        left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2
        break
      case 'bottom':
        top = triggerRect.bottom + padding
        left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2
        break
      case 'left':
        top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2
        left = triggerRect.left - tooltipRect.width - padding
        break
      case 'right':
        top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2
        left = triggerRect.right + padding
        break
      default:
        break
    }

    // Keep tooltip within viewport
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight

    if (left < padding) left = padding
    if (left + tooltipRect.width > viewportWidth - padding) {
      left = viewportWidth - tooltipRect.width - padding
    }
    if (top < padding) top = padding
    if (top + tooltipRect.height > viewportHeight - padding) {
      top = viewportHeight - tooltipRect.height - padding
    }

    setTooltipPosition({ top, left })
  }, [position])

  // Show tooltip
  const show = useCallback(() => {
    if (disabled || !content) return
    setIsVisible(true)
  }, [disabled, content])

  // Hide tooltip
  const hide = useCallback(() => {
    setIsVisible(false)
  }, [])

  // Update position when visible
  useEffect(() => {
    if (isVisible) {
      // Use requestAnimationFrame to ensure tooltip is rendered before measuring
      requestAnimationFrame(calculatePosition)
    }
  }, [isVisible, calculatePosition])

  // Cleanup timeouts
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current)
      if (longPressTimeoutRef.current) clearTimeout(longPressTimeoutRef.current)
    }
  }, [])

  // Desktop hover handlers
  const handleMouseEnter = () => {
    if (disabled) return
    hoverTimeoutRef.current = setTimeout(show, delay)
  }

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current)
    hide()
  }

  // Mobile long-press handlers
  const handleTouchStart = () => {
    if (disabled) return
    longPressTimeoutRef.current = setTimeout(show, longPressDelay)
  }

  const handleTouchEnd = () => {
    if (longPressTimeoutRef.current) clearTimeout(longPressTimeoutRef.current)
    // Keep visible briefly after long press
    setTimeout(hide, 1500)
  }

  const handleTouchMove = () => {
    // Cancel long press if user moves finger
    if (longPressTimeoutRef.current) clearTimeout(longPressTimeoutRef.current)
  }

  // Don't render tooltip if no content
  if (!content) {
    return children
  }

  return (
    <>
      {/* Trigger element */}
      <span
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onTouchMove={handleTouchMove}
        className="inline-block"
      >
        {children}
      </span>

      {/* Tooltip */}
      {isVisible && (
        <div
          ref={tooltipRef}
          role="tooltip"
          className="
            fixed z-50 px-3 py-2 text-sm font-medium text-white
            bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg
            max-w-xs break-words
            animate-[fade-in_150ms_ease-out]
            pointer-events-none
          "
          style={{
            top: tooltipPosition.top,
            left: tooltipPosition.left,
          }}
        >
          {content}
          {/* Arrow */}
          <div
            className={`
              absolute w-2 h-2 bg-gray-900 dark:bg-gray-700 rotate-45
              ${position === 'top' ? 'bottom-[-4px] left-1/2 -translate-x-1/2' : ''}
              ${position === 'bottom' ? 'top-[-4px] left-1/2 -translate-x-1/2' : ''}
              ${position === 'left' ? 'right-[-4px] top-1/2 -translate-y-1/2' : ''}
              ${position === 'right' ? 'left-[-4px] top-1/2 -translate-y-1/2' : ''}
            `}
          />
        </div>
      )}
    </>
  )
}

/**
 * A text component that shows a tooltip when the text is truncated.
 * Automatically detects if content is truncated and only shows tooltip if needed.
 */
export function TruncatedText({ children, className = '', as: Component = 'span' }) {
  const [isTruncated, setIsTruncated] = useState(false)
  const textRef = useRef(null)

  useEffect(() => {
    const checkTruncation = () => {
      if (textRef.current) {
        setIsTruncated(textRef.current.scrollWidth > textRef.current.clientWidth)
      }
    }

    checkTruncation()

    // Recheck on resize
    window.addEventListener('resize', checkTruncation)
    return () => window.removeEventListener('resize', checkTruncation)
  }, [children])

  return (
    <Tooltip content={isTruncated ? children : null} position="top">
      <Component ref={textRef} className={`truncate ${className}`}>
        {children}
      </Component>
    </Tooltip>
  )
}
