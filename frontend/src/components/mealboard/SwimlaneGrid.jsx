import { useMemo } from 'react'
import MealCard from './MealCard'

// Gradient backgrounds per slot type (light mode → dark mode)
const SWIMLANE_GRADIENTS_LIGHT = {
  // Fallback: compute from slot color
  default: (color) => `linear-gradient(135deg, ${color}20, ${color}30)`, // 20/30 = alpha
}

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

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/**
 * Horizontal swimlane grid.
 * Rows = meal slot types, columns = days of the week.
 * Mobile: switches to day-focused swipeable view (handled separately).
 */
export default function SwimlaneGrid({
  weekDates,
  slotTypes,
  mealEntries,
  familyMembers,
  onAddMeal,
  onMealUpdated,
  onMealDeleted,
  onViewRecipe,
  initialLoaded,
}) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // Group meal entries by (date, slot_type_id) for fast lookup
  const entriesByDaySlot = useMemo(() => {
    const map = {}
    for (const entry of mealEntries) {
      const key = `${entry.date}::${entry.meal_slot_type_id}`
      if (!map[key]) map[key] = []
      map[key].push(entry)
    }
    // Sort entries within each cell by sort_order
    for (const key in map) {
      map[key].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    }
    return map
  }, [mealEntries])

  const getEntries = (date, slotTypeId) => {
    const key = `${formatDateKey(date)}::${slotTypeId}`
    return entriesByDaySlot[key] || []
  }

  // Compute prep-time summary per day (sum of prep_time + cook_time across all recipe meals)
  const prepTimeByDay = useMemo(() => {
    const map = {}
    for (const date of weekDates) {
      const key = formatDateKey(date)
      let total = 0
      for (const entry of mealEntries) {
        if (entry.date === key && entry.item?.item_type === 'recipe' && entry.item.recipe_detail) {
          const rd = entry.item.recipe_detail
          total += (rd.prep_time_minutes || 0) + (rd.cook_time_minutes || 0)
        }
      }
      map[key] = total
    }
    return map
  }, [weekDates, mealEntries])

  if (slotTypes.length === 0) {
    // During initial load, slotTypes is [] because the API hasn't responded yet.
    // Return null so the parent's delayed spinner overlay handles the loading state.
    // Only show the "no slots" message after data has loaded and there truly are none.
    if (!initialLoaded) return null
    return (
      <div className="text-center py-16">
        <p className="text-sm text-text-muted dark:text-gray-400 mb-2">
          No meal slots configured
        </p>
        <p className="text-xs text-text-muted dark:text-gray-500">
          Go to Settings → Mealboard to add slots
        </p>
      </div>
    )
  }

  return (
    <div role="grid" aria-label="Weekly meal plan">
      {/* Day headers */}
      <div
        className="grid grid-cols-[80px_repeat(7,1fr)] gap-0 mb-2 sm:grid-cols-[100px_repeat(7,1fr)]"
        role="row"
      >
        <div role="columnheader" /> {/* Spacer for slot label column */}
        {weekDates.map((date) => {
          const isToday = isSameDay(date, today)
          return (
            <div
              key={date.toISOString()}
              className="text-center px-1 py-2"
              role="columnheader"
              aria-label={date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
            >
              <div
                className={`text-[10px] font-semibold uppercase tracking-wider ${
                  isToday ? 'text-terracotta-500 dark:text-blue-400' : 'text-text-muted dark:text-gray-400'
                }`}
              >
                {DAY_NAMES[date.getDay()]}
              </div>
              {isToday ? (
                <div
                  className="
                    w-9 h-9 mx-auto mt-1 rounded-xl
                    bg-gradient-to-br from-terracotta-500 to-peach-200
                    dark:from-blue-500 dark:to-blue-400
                    text-white font-bold text-base
                    flex items-center justify-center
                    shadow-md
                  "
                >
                  {date.getDate()}
                </div>
              ) : (
                <div className="text-lg font-bold text-text-primary dark:text-gray-100 mt-0.5">
                  {date.getDate()}
                </div>
              )}
              {/* Prep-time summary */}
              {prepTimeByDay[formatDateKey(date)] > 0 && (
                <div className="text-[10px] text-text-muted dark:text-gray-400 mt-0.5">
                  ⏲ {prepTimeByDay[formatDateKey(date)]}m
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Swimlane rows */}
      <div className="space-y-2">
        {slotTypes.map((slot, idx) => {
          const slotColor = slot.color || '#9CA3AF'
          const gradient = `linear-gradient(135deg, ${slotColor}14, ${slotColor}1F)` // 14/1F alpha hex

          return (
            <div
              key={slot.id}
              className="
                swimlane-enter
                grid grid-cols-[80px_repeat(7,1fr)]
                sm:grid-cols-[100px_repeat(7,1fr)]
                rounded-2xl overflow-hidden border
                transition-all
              "
              style={{
                background: gradient,
                borderColor: `${slotColor}40`,
                animationDelay: `${idx * 70}ms`,
              }}
              role="row"
              aria-label={slot.name}
            >
              {/* Left rail label */}
              <div
                className="flex flex-col items-center justify-center gap-1 py-3 px-2 border-r"
                style={{ borderColor: `${slotColor}40` }}
                role="rowheader"
              >
                {slot.icon && <span className="text-lg leading-none">{slot.icon}</span>}
                <span
                  className="text-[10px] font-bold uppercase tracking-wide text-center leading-tight"
                  style={{ color: slotColor }}
                >
                  {slot.name}
                </span>
              </div>

              {/* Day cells */}
              {weekDates.map((date, idx) => {
                const entries = getEntries(date, slot.id)
                const isToday = isSameDay(date, today)
                const isLast = idx === weekDates.length - 1

                return (
                  <LaneCell
                    key={`${slot.id}-${date.toISOString()}`}
                    date={date}
                    slotType={slot}
                    entries={entries}
                    familyMembers={familyMembers}
                    isToday={isToday}
                    isLast={isLast}
                    onAddMeal={onAddMeal}
                    onMealUpdated={onMealUpdated}
                    onMealDeleted={onMealDeleted}
                    onViewRecipe={onViewRecipe}
                  />
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Single cell in the swimlane grid (one day × one slot type).
 * Shows either empty state (dashed + button) or stacked meal cards with hover-add button.
 */
function LaneCell({ date, slotType, entries, familyMembers, isToday, isLast, onAddMeal, onMealUpdated, onMealDeleted, onViewRecipe }) {
  const hasMeals = entries.length > 0

  const handleAddClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    onAddMeal(date, slotType.id, rect)
  }

  const cellLabel = `${slotType.name}, ${date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}`
  return (
    <div
      className={`
        group/cell p-1.5 flex flex-col gap-1.5
        ${!isLast ? 'border-r border-black/5 dark:border-white/5' : ''}
        ${isToday ? 'bg-white/30 dark:bg-white/5' : ''}
      `}
      role="gridcell"
      aria-label={`${cellLabel}${hasMeals ? `, ${entries.length} meal${entries.length === 1 ? '' : 's'}` : ', empty'}`}
    >
      {hasMeals ? (
        <>
          {entries.map((entry) => (
            <MealCard
              key={entry.id}
              entry={entry}
              slotType={slotType}
              familyMembers={familyMembers}
              onUpdated={onMealUpdated}
              onDeleted={onMealDeleted}
              onViewRecipe={onViewRecipe}
            />
          ))}
          {/* Inline add button — always visible, subtle */}
          <button
            type="button"
            onClick={handleAddClick}
            className="
              flex items-center justify-center
              px-2 py-1 rounded-md text-xs
              border border-dashed border-black/8 dark:border-white/8
              text-text-muted/50 dark:text-gray-600
              hover:border-terracotta-500 hover:text-terracotta-500
              dark:hover:border-blue-500 dark:hover:text-blue-400
              transition-all
            "
            aria-label={`Add meal to ${slotType.name} on ${date.toLocaleDateString()}`}
          >
            +
          </button>
        </>
      ) : (
        <button
          type="button"
          onClick={handleAddClick}
          className="
            flex-1 min-h-[48px] rounded-lg
            border-2 border-dashed border-black/10 dark:border-white/10
            text-text-muted dark:text-gray-500 text-lg font-medium
            hover:border-terracotta-500 hover:text-terracotta-500 hover:bg-white/50
            dark:hover:border-blue-500 dark:hover:text-blue-400 dark:hover:bg-white/5
            transition-all
          "
          aria-label={`Add meal to ${slotType.name} on ${date.toLocaleDateString()}`}
        >
          +
        </button>
      )}
    </div>
  )
}
