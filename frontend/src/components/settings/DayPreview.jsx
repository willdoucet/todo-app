/**
 * Live preview of a single day of the swimlane grid, showing all active slot
 * types as colored bars. Updates in real-time as slots are reordered, hidden,
 * or color-changed.
 */
export default function DayPreview({ slotTypes, editingSlotId }) {
  return (
    <div
      className="
        rounded-xl border border-card-border dark:border-gray-700
        bg-card-bg dark:bg-gray-800 p-3
      "
    >
      <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted dark:text-gray-400 mb-2 text-center">
        Monday
      </div>

      <div className="space-y-1.5">
        {slotTypes.map((slot) => {
          const isEditing = slot.id === editingSlotId
          const isHidden = !slot.is_active

          return (
            <div
              key={slot.id}
              className={`
                flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs
                transition-all
                ${isHidden ? 'opacity-40' : ''}
                ${isEditing ? 'ring-2 ring-terracotta-500 dark:ring-blue-500 ring-offset-1 dark:ring-offset-gray-800' : ''}
              `}
              style={{
                backgroundColor: isHidden ? 'transparent' : `${slot.color}20`, // 20 = ~12% alpha
                border: `1px solid ${isHidden ? 'transparent' : slot.color + '40'}`,
              }}
            >
              {slot.icon && <span className="text-sm">{slot.icon}</span>}
              <span className="font-medium text-text-primary dark:text-gray-100 truncate flex-1">
                {slot.name}
              </span>
              {isHidden && (
                <span className="text-[9px] uppercase font-bold text-text-muted tracking-wider">
                  Hidden
                </span>
              )}
            </div>
          )
        })}

        {slotTypes.length === 0 && (
          <div className="py-6 text-center text-xs text-text-muted dark:text-gray-500">
            No slots configured
          </div>
        )}
      </div>

      <div className="text-[9px] text-text-muted dark:text-gray-500 mt-3 text-center italic">
        Live preview — updates as you edit
      </div>
    </div>
  )
}
