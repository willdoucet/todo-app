import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function TodoForm({ initial = null, listId = null, sectionId = null, onSubmit, onCancel, formRef }) {
  const [title, setTitle] = useState(initial?.title || '')
  const [description, setDescription] = useState(initial?.description || '')
  const [dueDate, setDueDate] = useState(initial?.due_date?.split('T')[0] || '')
  const [priority, setPriority] = useState(initial?.priority ?? 0)
  const [assignedTo, setAssignedTo] = useState(initial?.assigned_to || null)
  const [familyMembers, setFamilyMembers] = useState([])
  const [isLoadingFamilyMembers, setIsLoadingFamilyMembers] = useState(true)

  useEffect(() => {
    const loadFamilyMembers = async () => {
      try {
        const response = await axios.get(`${API_BASE}/family-members`)
        setFamilyMembers(response.data)

        if (!initial?.assigned_to && response.data.length > 0) {
          setAssignedTo(response.data[0].id)
        }
      } catch (err) {
        console.error('Error loading family members:', err)
      } finally {
        setIsLoadingFamilyMembers(false)
      }
    }
    loadFamilyMembers()
  }, [initial?.assigned_to])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!title.trim()) return

    const data = {
      ...(initial || {}),
      title,
      description: description || undefined,
      due_date: dueDate || undefined,
      priority,
      assigned_to: assignedTo,
    }

    // Include list_id and section_id for new tasks
    if (!initial && listId) {
      data.list_id = listId
    }
    if (!initial && sectionId) {
      data.section_id = sectionId
    }

    onSubmit(data)
  }

  return (
    <form ref={formRef} onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
      {/* Title */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Title <span className="text-red-500 dark:text-red-400">*</span>
        </label>
        <input
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          required
          placeholder="Enter task title"
          className="
            w-full px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-600
            rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
            focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
            outline-none transition text-sm sm:text-base
            placeholder:text-text-muted dark:placeholder:text-gray-500
          "
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Description
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={4}
          placeholder="Add a description (optional)"
          className="
            w-full px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-600
            rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
            focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
            outline-none transition resize-none text-sm sm:text-base
            placeholder:text-text-muted dark:placeholder:text-gray-500
          "
        />
      </div>

      {/* Due Date */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Due Date
        </label>
        <input
          type="date"
          value={dueDate}
          onChange={e => setDueDate(e.target.value)}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-600
            rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
            focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
            outline-none transition text-sm sm:text-base
          "
        />
      </div>

      {/* Assigned To */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Assigned To
        </label>
        <select
          value={assignedTo || ''}
          onChange={e => setAssignedTo(parseInt(e.target.value))}
          disabled={isLoadingFamilyMembers}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-card-border dark:border-gray-600
            rounded-lg bg-card-bg dark:bg-gray-700 text-text-primary dark:text-gray-100
            focus:ring-2 focus:ring-terracotta-500 focus:border-terracotta-500
            outline-none transition text-sm sm:text-base
          "
        >
          {isLoadingFamilyMembers ? (
            <option>Loading...</option>
          ) : (
            familyMembers.map(member => (
              <option key={member.id} value={member.id}>
                {member.name}
              </option>
            ))
          )}
        </select>
      </div>

      {/* Priority Selector */}
      <div>
        <label className="block text-sm sm:text-base font-medium text-text-secondary dark:text-gray-300 mb-2">
          Priority
        </label>
        <div className="flex gap-1.5" role="radiogroup" aria-label="Task priority">
          {[
            { value: 0, label: 'None' },
            { value: 9, label: 'Low' },
            { value: 5, label: 'Med' },
            { value: 1, label: 'High' },
          ].map(({ value, label }) => {
            const isActive = priority === value
            const activeColor =
              value === 1 ? 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800' :
              value === 5 ? 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800' :
              value === 9 ? 'bg-warm-beige text-text-secondary border-card-border dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600' :
              'bg-warm-beige text-text-secondary border-card-border dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600'

            return (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={isActive}
                onClick={() => setPriority(value)}
                className={`
                  px-3 py-1.5 text-sm font-medium rounded-lg border transition-all duration-150
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500
                  ${isActive
                    ? activeColor
                    : 'bg-warm-sand/50 text-text-muted border-transparent hover:bg-warm-beige dark:bg-gray-800 dark:text-gray-500 dark:hover:bg-gray-700'
                  }
                `}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 sm:pt-3">
        <button
          type="button"
          onClick={onCancel}
          className="
            px-5 py-2.5 sm:py-2.5 text-text-secondary dark:text-gray-300 font-medium
            hover:bg-warm-beige dark:hover:bg-gray-700 rounded-lg transition-colors duration-200
            text-sm sm:text-base
          "
        >
          Cancel
        </button>
        <button
          type="submit"
          className="
            px-6 py-2.5 sm:py-2.5 bg-terracotta-500 text-white font-medium
            rounded-lg hover:bg-terracotta-600 transition-colors duration-200
            focus:outline-none focus:ring-2 focus:ring-terracotta-500 focus:ring-offset-2
            text-sm sm:text-base
          "
        >
          {initial?.id ? 'Save Changes' : 'Add Task'}
        </button>
      </div>
    </form>
  )
}
