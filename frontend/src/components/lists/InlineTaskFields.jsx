import { useState, useEffect, useCallback } from 'react'
import useDebounce from '../../hooks/useDebounce'

const PRIORITY_OPTIONS = [
  { value: 0, label: 'None' },
  { value: 9, label: 'Low' },
  { value: 5, label: 'Med' },
  { value: 1, label: 'High' },
]

export default function InlineTaskFields({ task, familyMembers = [], onUpdateTask }) {
  const [description, setDescription] = useState(task.description || '')
  const [dueDate, setDueDate] = useState(task.due_date?.split('T')[0] || '')

  // Sync local state when task changes externally (e.g. server reconcile
  // after another tab edits the task). Local edits flow through
  // handleDescriptionChange below and stay in sync via debounced save.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDescription(task.description || '')
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDueDate(task.due_date?.split('T')[0] || '')
  }, [task.description, task.due_date])

  // Debounced save for description (textarea)
  const debouncedSaveDescription = useDebounce(
    useCallback((value) => {
      const payload = value.trim() ? { description: value.trim() } : { description: null }
      onUpdateTask(task.id, payload)
    }, [task.id, onUpdateTask]),
    500
  )

  const handleDescriptionChange = (e) => {
    setDescription(e.target.value)
    debouncedSaveDescription(e.target.value)
  }

  const handleDueDateChange = (e) => {
    const value = e.target.value
    setDueDate(value)
    onUpdateTask(task.id, { due_date: value || null })
  }

  const handleAssigneeClick = (memberId) => {
    // Toggle: if already assigned, clear; otherwise assign
    const newValue = task.assigned_to === memberId ? null : memberId
    onUpdateTask(task.id, { assigned_to: newValue })
  }

  const handlePriorityClick = (value) => {
    if (task.priority !== value) {
      onUpdateTask(task.id, { priority: value })
    }
  }

  return (
    <div className="space-y-3.5">
      {/* Due Date */}
      <div>
        <label className="block text-[11px] font-semibold uppercase tracking-wider text-text-muted dark:text-gray-500 mb-1.5">
          Due Date
        </label>
        <input
          type="date"
          value={dueDate}
          onChange={handleDueDateChange}
          className={`
            px-2.5 py-1.5 text-[13px] font-medium
            bg-white dark:bg-gray-700
            border border-card-border dark:border-gray-600 rounded-lg
            outline-none transition-colors
            focus:border-terracotta-500 dark:focus:border-blue-500
            focus:ring-2 focus:ring-terracotta-500/10 dark:focus:ring-blue-500/10
            ${dueDate ? 'text-text-primary dark:text-gray-100' : 'text-text-muted dark:text-gray-500'}
          `}
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-[11px] font-semibold uppercase tracking-wider text-text-muted dark:text-gray-500 mb-1.5">
          Description
        </label>
        <textarea
          value={description}
          onChange={handleDescriptionChange}
          placeholder="Add a description..."
          rows={2}
          className="
            w-full px-2.5 py-1.5 text-[13px]
            bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100
            border border-card-border dark:border-gray-600 rounded-lg
            outline-none transition-colors resize-vertical min-h-[56px]
            placeholder:text-text-muted dark:placeholder:text-gray-500
            focus:border-terracotta-500 dark:focus:border-blue-500
            focus:ring-2 focus:ring-terracotta-500/10 dark:focus:ring-blue-500/10
          "
        />
      </div>

      {/* Assigned To — pills */}
      <div>
        <label className="block text-[11px] font-semibold uppercase tracking-wider text-text-muted dark:text-gray-500 mb-1.5">
          Assigned To
        </label>
        <div className="flex gap-1.5 flex-wrap">
          {familyMembers.length === 0 ? (
            <span className="text-xs text-text-muted dark:text-gray-500 italic">No members</span>
          ) : (
            familyMembers.map(member => {
              const isActive = task.assigned_to === member.id
              return (
                <button
                  key={member.id}
                  type="button"
                  onClick={() => handleAssigneeClick(member.id)}
                  className={`
                    inline-flex items-center gap-1.5 px-3 py-1 text-[12px] font-medium
                    rounded-full border-[1.5px] transition-all duration-150 cursor-pointer
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500
                    ${isActive
                      ? 'bg-terracotta-500 dark:bg-blue-600 text-white border-terracotta-500 dark:border-blue-600 shadow-sm'
                      : 'bg-white dark:bg-gray-700 text-text-secondary dark:text-gray-300 border-card-border dark:border-gray-600 hover:border-terracotta-500 dark:hover:border-blue-500'}
                  `}
                >
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: member.color || '#9A9287' }}
                  />
                  {member.name}
                </button>
              )
            })
          )}
        </div>
      </div>

      {/* Priority — pills */}
      <div>
        <label className="block text-[11px] font-semibold uppercase tracking-wider text-text-muted dark:text-gray-500 mb-1.5">
          Priority
        </label>
        <div className="flex gap-1.5 flex-wrap">
          {PRIORITY_OPTIONS.map(({ value, label }) => {
            const isActive = (task.priority ?? 0) === value
            const activeColor =
              value === 1 ? 'bg-red-500 dark:bg-red-600 text-white border-red-500 dark:border-red-600' :
              value === 5 ? 'bg-amber-500 dark:bg-amber-600 text-white border-amber-500 dark:border-amber-600' :
              value === 9 ? 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 border-card-border dark:border-gray-600' :
              'bg-gray-200 dark:bg-gray-700 text-text-secondary dark:text-gray-300 border-gray-200 dark:border-gray-600'

            return (
              <button
                key={value}
                type="button"
                onClick={() => handlePriorityClick(value)}
                className={`
                  px-3 py-1 text-[12px] font-medium rounded-full border-[1.5px]
                  transition-all duration-150 cursor-pointer
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500
                  ${isActive
                    ? activeColor
                    : 'bg-white dark:bg-gray-700 text-text-muted dark:text-gray-400 border-card-border dark:border-gray-600 hover:border-terracotta-500 dark:hover:border-blue-500'}
                `}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
