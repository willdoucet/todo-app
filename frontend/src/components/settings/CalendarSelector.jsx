/**
 * Presentational component for Step 2 of iCloud connection flow.
 * Shows a checkbox list of calendars with color dots, event counts,
 * and shared-calendar warnings.
 */
export default function CalendarSelector({
  calendars = [],
  selected = [],
  onChange,
}) {
  const allSelected = calendars.length > 0 && selected.length === calendars.length
  const noneSelected = selected.length === 0

  const toggleCalendar = (url) => {
    if (selected.includes(url)) {
      onChange(selected.filter((u) => u !== url))
    } else {
      onChange([...selected, url])
    }
  }

  const toggleAll = () => {
    if (allSelected) {
      onChange([])
    } else {
      onChange(calendars.map((c) => c.url))
    }
  }

  return (
    <div className="space-y-2">
      {calendars.length > 1 && (
        <button
          type="button"
          onClick={toggleAll}
          className="text-sm text-terracotta-500 dark:text-blue-400 hover:underline mb-1"
        >
          {allSelected ? 'Deselect All' : 'Select All'}
        </button>
      )}

      {calendars.map((cal) => (
        <label
          key={cal.url}
          className="flex items-center gap-3 p-3 rounded-lg hover:bg-warm-beige dark:hover:bg-gray-700 cursor-pointer transition-colors"
        >
          <input
            type="checkbox"
            checked={selected.includes(cal.url)}
            onChange={() => toggleCalendar(cal.url)}
            className="h-4 w-4 rounded border-card-border text-terracotta-500 focus:ring-terracotta-500 dark:border-gray-600 dark:text-blue-500 dark:focus:ring-blue-500"
          />

          {/* Color dot */}
          <span
            className="w-3 h-3 rounded-full shrink-0"
            style={{ backgroundColor: cal.color || '#999' }}
          />

          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium text-text-primary dark:text-gray-200 truncate block">
              {cal.name}
            </span>
            <div className="flex items-center gap-2 mt-0.5">
              {cal.event_count != null && (
                <span className="text-xs text-text-muted dark:text-gray-400">
                  {cal.event_count} event{cal.event_count !== 1 ? 's' : ''}
                </span>
              )}
              {cal.already_synced_by && (
                <span className="text-xs text-amber-600 dark:text-amber-400">
                  Already synced from {cal.already_synced_by}'s account
                </span>
              )}
            </div>
          </div>
        </label>
      ))}

      {noneSelected && calendars.length > 0 && (
        <p className="text-sm text-text-muted dark:text-gray-400 italic">
          Select at least one calendar to sync.
        </p>
      )}
    </div>
  )
}
