import { useMemo } from 'react'

const ENCOURAGING_MESSAGES = {
  none: "Let's start planning!",
  low: 'Keep planning!',
  mid: 'Halfway there',
  high: 'Almost there! 🎉',
  full: 'Week complete! 🎊',
}

function getMessage(count, total) {
  if (count === 0) return ENCOURAGING_MESSAGES.none
  if (count === total) return ENCOURAGING_MESSAGES.full
  const pct = count / total
  if (pct < 0.3) return ENCOURAGING_MESSAGES.low
  if (pct < 0.7) return ENCOURAGING_MESSAGES.mid
  return ENCOURAGING_MESSAGES.high
}

/**
 * Multi-slot progress tracker shown below the swimlane grid.
 * One card per active slot type showing X/7 planned days + progress bar.
 */
export default function ProgressTracker({ slotTypes, mealEntries }) {
  // Count unique planned days per slot type
  const stats = useMemo(() => {
    return slotTypes.map((slot) => {
      const uniqueDays = new Set(
        mealEntries
          .filter((e) => e.meal_slot_type_id === slot.id)
          .map((e) => e.date)
      )
      const count = uniqueDays.size
      return {
        id: slot.id,
        name: slot.name,
        icon: slot.icon,
        color: slot.color || '#9CA3AF',
        count,
      }
    })
  }, [slotTypes, mealEntries])

  if (slotTypes.length === 0) return null

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary dark:text-gray-100">
          This Week
        </h3>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
        {stats.map((stat) => {
          const pct = Math.round((stat.count / 7) * 100)
          const message = getMessage(stat.count, 7)
          return (
            <div
              key={stat.id}
              className="
                rounded-xl p-3 border
                transition-all
              "
              style={{
                background: `linear-gradient(135deg, ${stat.color}14, ${stat.color}1F)`,
                borderColor: `${stat.color}40`,
              }}
            >
              <div className="flex items-center gap-1.5 mb-1.5">
                {stat.icon && <span className="text-base leading-none">{stat.icon}</span>}
                <span
                  className="text-[10px] font-bold uppercase tracking-wide truncate"
                  style={{ color: stat.color }}
                >
                  {stat.name}
                </span>
              </div>
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-2xl font-bold text-text-primary dark:text-gray-100 leading-none">
                  {stat.count}
                </span>
                <span className="text-sm text-text-muted dark:text-gray-400 font-semibold">/7</span>
              </div>
              {/* Progress bar */}
              <div className="h-1.5 rounded-full bg-white/60 dark:bg-white/10 overflow-hidden mb-1.5">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${pct}%`, backgroundColor: stat.color }}
                />
              </div>
              <div className="text-[10px] font-medium text-text-muted dark:text-gray-400 truncate">
                {message}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
