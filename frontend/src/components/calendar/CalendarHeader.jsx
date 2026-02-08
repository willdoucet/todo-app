/**
 * Calendar navigation bar — period label, prev/today/next, and view mode toggle.
 */
export default function CalendarHeader({
  currentDate,
  viewMode,
  onPrev,
  onNext,
  onToday,
  onViewChange,
}) {
  const label = formatPeriodLabel(currentDate, viewMode)

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 sm:gap-3">
      {/* Nav buttons */}
      <div className="flex items-center gap-1">
        <button
          onClick={onPrev}
          className="p-2 rounded-lg bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
          aria-label="Previous"
        >
          <svg className="w-4 h-4 sm:w-5 sm:h-5 text-text-secondary dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <button
          onClick={onNext}
          className="p-2 rounded-lg bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors"
          aria-label="Next"
        >
          <svg className="w-4 h-4 sm:w-5 sm:h-5 text-text-secondary dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        <button
          onClick={onToday}
          className="ml-1 px-2.5 py-1.5 text-xs sm:text-sm rounded-lg bg-terracotta-500 dark:bg-blue-600 text-white hover:bg-terracotta-600 dark:hover:bg-blue-700 transition-colors"
        >
          Today
        </button>
      </div>

      {/* Period label */}
      <h2 className="text-base sm:text-xl font-bold text-text-primary dark:text-gray-100 order-first sm:order-none w-full sm:w-auto">
        {label}
      </h2>

      {/* View mode toggle */}
      <div className="ml-auto flex rounded-lg border border-card-border dark:border-gray-700 overflow-hidden">
        {['month', 'week', 'day'].map((mode) => (
          <button
            key={mode}
            onClick={() => onViewChange(mode)}
            className={`px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm capitalize transition-colors ${
              viewMode === mode
                ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                : 'bg-card-bg dark:bg-gray-800 text-text-secondary dark:text-gray-400 hover:bg-warm-sand dark:hover:bg-gray-700'
            }`}
          >
            {mode}
          </button>
        ))}
      </div>
    </div>
  )
}

function formatPeriodLabel(date, viewMode) {
  if (viewMode === 'day') {
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
  }
  if (viewMode === 'week') {
    // Show "Mon D – Mon D, YYYY" for the week range
    const d = new Date(date)
    const dow = d.getDay()
    const sunday = new Date(d)
    sunday.setDate(d.getDate() - dow)
    const saturday = new Date(sunday)
    saturday.setDate(sunday.getDate() + 6)

    const startLabel = sunday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    const endLabel = saturday.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
    return `${startLabel} – ${endLabel}`
  }
  // month
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}
