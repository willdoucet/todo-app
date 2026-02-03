export default function WeekSelector({ weekDates, onPrevWeek, onNextWeek }) {
  const formatWeekRange = () => {
    const start = weekDates[0]
    const end = weekDates[6]

    const startMonth = start.toLocaleDateString('en-US', { month: 'short' })
    const endMonth = end.toLocaleDateString('en-US', { month: 'short' })
    const startDay = start.getDate()
    const endDay = end.getDate()

    if (startMonth === endMonth) {
      return `${startMonth} ${startDay} - ${endDay}`
    }
    return `${startMonth} ${startDay} - ${endMonth} ${endDay}`
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onPrevWeek}
        className="p-2 rounded-lg bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-600 transition-colors"
        aria-label="Previous week"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <span className="px-4 py-2 min-w-[140px] text-center text-sm font-medium text-text-primary dark:text-gray-100 bg-warm-sand dark:bg-gray-700 rounded-lg">
        {formatWeekRange()}
      </span>

      <button
        onClick={onNextWeek}
        className="p-2 rounded-lg bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-600 transition-colors"
        aria-label="Next week"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  )
}
