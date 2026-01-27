// components/TaskForm.jsx
import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'


export default function TaskForm({ initial = null, onSubmit, onCancel }) {
  const [title, setTitle] = useState(initial?.title || '')
  const [description, setDescription] = useState(initial?.description || '')
  const [dueDate, setDueDate] = useState(initial?.due_date?.split('T')[0] || '')
  const [important, setImportant] = useState(initial?.important || false)
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
        
      }finally {
        setIsLoadingFamilyMembers(false)
      }
    }
    loadFamilyMembers()
  }, [initial?.assigned_to])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!title.trim()) return
    onSubmit({
      ...(initial || {}),
      title,
      description: description || undefined,
      due_date: dueDate || undefined,
      important,
      assigned_to: assignedTo,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
      <div>
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
          Title <span className="text-red-500 dark:text-red-400">*</span>
        </label>
        <input
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          required
          placeholder="Enter task title"
          className="
            w-full px-4 py-2.5 sm:py-3 border border-gray-300 dark:border-gray-600 
            rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            outline-none transition text-sm sm:text-base
            placeholder:text-gray-400 dark:placeholder:text-gray-500
          "
        />
      </div>

      <div>
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
          Description
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={4}
          placeholder="Add a description (optional)"
          className="
            w-full px-4 py-2.5 sm:py-3 border border-gray-300 dark:border-gray-600 
            rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            outline-none transition resize-none text-sm sm:text-base
            placeholder:text-gray-400 dark:placeholder:text-gray-500
          "
        />
      </div>

      <div>
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
          Due Date
        </label>
        <input
          type="date"
          value={dueDate}
          onChange={e => setDueDate(e.target.value)}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-gray-300 dark:border-gray-600 
            rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            outline-none transition text-sm sm:text-base
          "
        />
      </div>

      <div>
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300 mb-2">
          Assigned To
        </label>
        <select
          value={assignedTo || ''}
          onChange={e => setAssignedTo(parseInt(e.target.value))}
          disabled={isLoadingFamilyMembers}
          className="
            w-full px-4 py-2.5 sm:py-3 border border-gray-300 dark:border-gray-600 
            rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
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

      <div className="flex items-center justify-between">
        <label className="block text-sm sm:text-base font-medium text-gray-700 dark:text-gray-300">
          Mark as Important
        </label>
        <button
          type="button"
          role="switch"
          aria-checked={important}
          onClick={() => setImportant(!important)}
          className={`
            relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ease-in-out
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            ${important ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}
          `}
        >
          <span
            className={`
              inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ease-in-out
              ${important ? 'translate-x-6' : 'translate-x-1'}
            `}
          />
        </button>
      </div>

      <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 sm:pt-3">
        <button
          type="button"
          onClick={onCancel}
          className="
            px-5 py-2.5 sm:py-2.5 text-gray-700 dark:text-gray-300 font-medium 
            hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors duration-200
            text-sm sm:text-base
          "
        >
          Cancel
        </button>
        <button
          type="submit"
          className="
            px-6 py-2.5 sm:py-2.5 bg-blue-600 text-white font-medium 
            rounded-lg hover:bg-blue-700 transition-colors duration-200
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            text-sm sm:text-base
          "
        >
          {initial?.id ? 'Save Changes' : 'Add Task'}
        </button>
      </div>
    </form>
  )
}
