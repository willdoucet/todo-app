import { Popover, PopoverButton, PopoverPanel } from '@headlessui/react'

/**
 * Quick-add popover — shows "New Task" and "New Event" options.
 * Triggered from calendar views (day click, "+" button, slot click).
 */
export default function QuickAddPopover({ onNewTask, onNewEvent, children }) {
  return (
    <Popover className="relative">
      <PopoverButton as="div" className="cursor-pointer">
        {children}
      </PopoverButton>

      <PopoverPanel
        anchor="bottom"
        className="z-50 w-48 rounded-xl bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 shadow-lg p-1.5"
      >
        {({ close }) => (
          <>
            <button
              onClick={() => { onNewTask(); close() }}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-text-primary dark:text-gray-200 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
            >
              {/* Checkbox icon */}
              <svg className="w-4 h-4 text-terracotta-500 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
              New Task
            </button>
            <button
              onClick={() => { onNewEvent(); close() }}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-text-primary dark:text-gray-200 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
            >
              {/* Clock icon */}
              <svg className="w-4 h-4 text-terracotta-500 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              New Event
            </button>
          </>
        )}
      </PopoverPanel>
    </Popover>
  )
}
