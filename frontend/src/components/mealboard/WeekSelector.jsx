export default function WeekSelector({ weekDates, onPrevWeek, onNextWeek, onToday, compact = false }) {
  const formatWeekRange = () => {
    const start = weekDates[0]
    const end = weekDates[6]

    const startMonth = start.toLocaleDateString('en-US', { month: 'short' })
    const endMonth = end.toLocaleDateString('en-US', { month: 'short' })
    const startDay = start.getDate()
    const endDay = end.getDate()

    if (startMonth === endMonth) {
      return `${startMonth} ${startDay} – ${endDay}`
    }
    return `${startMonth} ${startDay} – ${endMonth} ${endDay}`
  }

  // Show Today button only when today is NOT in the displayed week
  const isCurrentWeek = () => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const start = new Date(weekDates[0])
    start.setHours(0, 0, 0, 0)
    const end = new Date(weekDates[6])
    end.setHours(0, 0, 0, 0)
    return today >= start && today <= end
  }

  const showToday = onToday && !isCurrentWeek()

  return (
    <div
      className="
        inline-flex items-stretch h-[34px]
        bg-card-bg dark:bg-gray-800
        border border-card-border dark:border-gray-700
        rounded-full overflow-hidden
      "
    >
      <button
        type="button"
        onClick={onPrevWeek}
        className="
          flex items-center justify-center px-3
          text-text-muted dark:text-gray-400
          hover:bg-warm-beige dark:hover:bg-gray-700
          hover:text-terracotta-600 dark:hover:text-blue-400
          transition-colors
        "
        aria-label="Previous week"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.25} strokeLinecap="round" strokeLinejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>

      {!compact && (
        <>
          <div className="w-px bg-card-border dark:bg-gray-700 my-1.5" />
          <span className="flex items-center px-4 text-[13px] font-semibold text-text-primary dark:text-gray-100 whitespace-nowrap">
            {formatWeekRange()}
          </span>
        </>
      )}

      {showToday && (
        <>
          <div className="w-px bg-card-border dark:bg-gray-700 my-1.5" />
          <button
            type="button"
            onClick={onToday}
            className="
              flex items-center px-3.5 text-xs font-semibold
              bg-terracotta-500 dark:bg-blue-500 text-white
              hover:bg-terracotta-600 dark:hover:bg-blue-600
              transition-colors
            "
            aria-label="Jump to current week"
          >
            Today
          </button>
        </>
      )}

      <div className="w-px bg-card-border dark:bg-gray-700 my-1.5" />
      <button
        type="button"
        onClick={onNextWeek}
        className="
          flex items-center justify-center px-3
          text-text-muted dark:text-gray-400
          hover:bg-warm-beige dark:hover:bg-gray-700
          hover:text-terracotta-600 dark:hover:text-blue-400
          transition-colors
        "
        aria-label="Next week"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.25} strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    </div>
  )
}
