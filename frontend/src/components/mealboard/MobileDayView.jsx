import { useState, useEffect, useMemo } from 'react'
import { useSwipeable } from 'react-swipeable'
import MealCard from './MealCard'

const DAY_NAMES_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const DAY_NAMES_FULL = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

function isSameDay(a, b) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function formatDateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * Mobile day view — shows one day at a time as a vertical stack of slot sections.
 * Each section contains the meals for that slot type on the selected day.
 *
 * Navigation:
 *  - Horizontal day pills at the top (scroll to select)
 *  - Swipe left/right to move between days
 */
export default function MobileDayView({
  weekDates,
  slotTypes,
  mealEntries,
  familyMembers,
  onAddMeal,
  onMealUpdated,
  onMealDeleted,
}) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // Find today's index in the week, or default to 0
  const todayIdx = weekDates.findIndex((d) => isSameDay(d, today))
  const [selectedIdx, setSelectedIdx] = useState(todayIdx >= 0 ? todayIdx : 0)

  // Reset selected index when weekDates changes (new week loaded)
  useEffect(() => {
    const newTodayIdx = weekDates.findIndex((d) => isSameDay(d, today))
    setSelectedIdx(newTodayIdx >= 0 ? newTodayIdx : 0)
  }, [weekDates])

  // Group entries by (date, slot_type_id)
  const entriesByDaySlot = useMemo(() => {
    const map = {}
    for (const entry of mealEntries) {
      const key = `${entry.date}::${entry.meal_slot_type_id}`
      if (!map[key]) map[key] = []
      map[key].push(entry)
    }
    for (const key in map) {
      map[key].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    }
    return map
  }, [mealEntries])

  const getEntries = (date, slotTypeId) => {
    const key = `${formatDateKey(date)}::${slotTypeId}`
    return entriesByDaySlot[key] || []
  }

  const goToPrevDay = () => setSelectedIdx((i) => Math.max(0, i - 1))
  const goToNextDay = () => setSelectedIdx((i) => Math.min(weekDates.length - 1, i + 1))

  const swipeHandlers = useSwipeable({
    onSwipedLeft: goToNextDay,
    onSwipedRight: goToPrevDay,
    trackMouse: false,
    preventScrollOnSwipe: false,
  })

  const selectedDate = weekDates[selectedIdx]
  if (!selectedDate) return null

  const isSelectedToday = isSameDay(selectedDate, today)

  const handleAddMeal = (slotTypeId) => {
    onAddMeal(selectedDate, slotTypeId, null)
  }

  return (
    <div>
      {/* Day pills - horizontal scrollable */}
      <div className="flex gap-1.5 mb-3 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-thin">
        {weekDates.map((date, idx) => {
          const isToday = isSameDay(date, today)
          const isSelected = idx === selectedIdx
          return (
            <button
              key={date.toISOString()}
              type="button"
              onClick={() => setSelectedIdx(idx)}
              className={`
                flex-shrink-0 flex flex-col items-center justify-center
                px-3 py-2 rounded-xl min-w-[48px]
                text-xs font-semibold transition-all
                ${
                  isSelected
                    ? 'bg-terracotta-500 dark:bg-blue-600 text-white shadow-md scale-105'
                    : isToday
                      ? 'bg-peach-100 dark:bg-blue-900/30 text-terracotta-600 dark:text-blue-400'
                      : 'bg-card-bg dark:bg-gray-800 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-700'
                }
              `}
            >
              <span className="text-[10px] uppercase tracking-wider opacity-80">
                {DAY_NAMES_SHORT[date.getDay()]}
              </span>
              <span className="text-base font-bold leading-none mt-0.5">{date.getDate()}</span>
            </button>
          )
        })}
      </div>

      {/* Swipeable day content */}
      <div {...swipeHandlers} className="select-none">
        {/* Selected day header */}
        <div className="flex items-center justify-between mb-3 px-1">
          <button
            type="button"
            onClick={goToPrevDay}
            disabled={selectedIdx === 0}
            className="p-1 text-text-muted dark:text-gray-500 disabled:opacity-30"
            aria-label="Previous day"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 className={`text-lg font-bold ${isSelectedToday ? 'text-terracotta-600 dark:text-blue-400' : 'text-text-primary dark:text-gray-100'}`}>
            {DAY_NAMES_FULL[selectedDate.getDay()]}
            <span className="text-sm font-normal text-text-muted dark:text-gray-400 ml-2">
              {selectedDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          </h2>
          <button
            type="button"
            onClick={goToNextDay}
            disabled={selectedIdx === weekDates.length - 1}
            className="p-1 text-text-muted dark:text-gray-500 disabled:opacity-30"
            aria-label="Next day"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Slot sections */}
        <div className="space-y-3">
          {slotTypes.map((slot) => {
            const entries = getEntries(selectedDate, slot.id)
            const slotColor = slot.color || '#9CA3AF'

            return (
              <div
                key={slot.id}
                className="rounded-2xl p-3 border"
                style={{
                  background: `linear-gradient(135deg, ${slotColor}14, ${slotColor}1F)`,
                  borderColor: `${slotColor}40`,
                }}
              >
                {/* Section header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {slot.icon && <span className="text-base leading-none">{slot.icon}</span>}
                    <span
                      className="text-xs font-bold uppercase tracking-wide"
                      style={{ color: slotColor }}
                    >
                      {slot.name}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleAddMeal(slot.id)}
                    className="
                      w-7 h-7 rounded-full flex items-center justify-center
                      bg-white/60 dark:bg-white/10
                      text-text-secondary dark:text-gray-300
                      hover:bg-white dark:hover:bg-white/20
                      transition-colors
                    "
                    aria-label={`Add ${slot.name} meal`}
                  >
                    +
                  </button>
                </div>

                {/* Entries */}
                {entries.length > 0 ? (
                  <div className="space-y-1.5">
                    {entries.map((entry) => (
                      <MealCard
                        key={entry.id}
                        entry={entry}
                        slotType={slot}
                        familyMembers={familyMembers}
                        onUpdated={onMealUpdated}
                        onDeleted={onMealDeleted}
                      />
                    ))}
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleAddMeal(slot.id)}
                    className="
                      w-full py-3 text-xs text-text-muted dark:text-gray-400
                      border-2 border-dashed border-black/10 dark:border-white/10
                      rounded-lg
                      hover:border-terracotta-500 hover:text-terracotta-500
                      dark:hover:border-blue-500 dark:hover:text-blue-400
                      transition-colors
                    "
                  >
                    Tap to add a meal
                  </button>
                )}
              </div>
            )
          })}
        </div>

        {/* Swipe hint */}
        <p className="text-center text-[10px] text-text-muted dark:text-gray-500 mt-4 mb-2">
          Swipe left or right to change days
        </p>
      </div>
    </div>
  )
}
