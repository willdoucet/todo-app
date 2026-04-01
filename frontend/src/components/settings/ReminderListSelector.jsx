/**
 * Presentational component for selecting iCloud reminder lists to sync.
 * Same pattern as CalendarSelector: checkbox list with color dots, task counts,
 * and shared-list warnings.
 */
export default function ReminderListSelector({
  reminderLists = [],
  selected = [],
  onChange,
}) {
  const allSelected = reminderLists.length > 0 && selected.length === reminderLists.length
  const noneSelected = selected.length === 0

  const toggleList = (url) => {
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
      onChange(reminderLists.map((c) => c.url))
    }
  }

  return (
    <div className="space-y-2">
      {reminderLists.length > 1 && (
        <button
          type="button"
          onClick={toggleAll}
          className="text-sm text-terracotta-500 dark:text-blue-400 hover:underline mb-1"
        >
          {allSelected ? 'Deselect All' : 'Select All'}
        </button>
      )}

      {reminderLists.map((list) => (
        <label
          key={list.url}
          className="flex items-center gap-3 p-3 rounded-lg hover:bg-warm-beige dark:hover:bg-gray-700 cursor-pointer transition-colors"
        >
          <input
            type="checkbox"
            checked={selected.includes(list.url)}
            onChange={() => toggleList(list.url)}
            className="h-4 w-4 rounded border-card-border text-terracotta-500 focus:ring-terracotta-500 dark:border-gray-600 dark:text-blue-500 dark:focus:ring-blue-500"
          />

          {/* Color dot */}
          <span
            className="w-3 h-3 rounded-full shrink-0"
            style={{ backgroundColor: list.color || '#999' }}
          />

          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium text-text-primary dark:text-gray-200 truncate block">
              {list.name}
            </span>
            <div className="flex items-center gap-2 mt-0.5">
              {list.task_count != null && (
                <span className="text-xs text-text-muted dark:text-gray-400">
                  {list.task_count} task{list.task_count !== 1 ? 's' : ''}
                </span>
              )}
              {list.already_synced_by && (
                <span className="text-xs text-amber-600 dark:text-amber-400">
                  Already synced from {list.already_synced_by}'s account
                </span>
              )}
            </div>
          </div>
        </label>
      ))}

      {noneSelected && reminderLists.length > 0 && (
        <p className="text-sm text-text-muted dark:text-gray-400 italic">
          Select at least one list to sync.
        </p>
      )}
    </div>
  )
}
