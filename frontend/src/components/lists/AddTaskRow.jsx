import { useState, useRef, useEffect } from 'react'

export default function AddTaskRow({ isActive, onActivate, onSave, onCancel }) {
  const [title, setTitle] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    if (isActive && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isActive])

  // Reset title when deactivated
  useEffect(() => {
    if (!isActive) setTitle('')
  }, [isActive])

  const handleSave = () => {
    const trimmed = title.trim()
    if (trimmed) {
      onSave(trimmed)
      setTitle('')
    } else {
      onCancel()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSave()
    }
    if (e.key === 'Escape') {
      setTitle('')
      onCancel()
    }
  }

  const handleBlur = (e) => {
    // Don't cancel if clicking on action buttons within the row
    if (e.relatedTarget?.closest?.('.add-task-actions')) return
    if (title.trim()) {
      handleSave()
    } else {
      onCancel()
    }
  }

  if (isActive) {
    return (
      <div className="
        w-full flex items-center gap-2 px-3 min-h-[48px]
        bg-[#FDFCFA] dark:bg-gray-800/50
        border-b border-[#f0ece5] dark:border-gray-800
      ">
        <span className="w-[18px] h-[18px] flex items-center justify-center text-[16px] font-light flex-shrink-0 text-terracotta-500 dark:text-blue-400">
          +
        </span>
        <input
          ref={inputRef}
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder="What needs to be done?"
          className="
            flex-1 min-w-0 text-[14px] font-medium bg-transparent outline-none
            text-text-primary dark:text-gray-100
            border-b-2 border-terracotta-500 dark:border-blue-500 py-1
            placeholder:text-text-muted dark:placeholder:text-gray-500
          "
          aria-label="New task title"
        />
        <div className="add-task-actions flex gap-0.5 flex-shrink-0">
          <button
            type="button"
            onClick={handleSave}
            className="
              px-2.5 py-1 text-[11px] font-semibold rounded
              bg-terracotta-500 dark:bg-blue-600 text-white
              hover:bg-terracotta-600 dark:hover:bg-blue-700
              transition-colors duration-75
              focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500
            "
          >
            Save
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="
              px-2 py-1 text-[11px] font-medium rounded
              bg-white dark:bg-gray-700 text-text-muted dark:text-gray-400
              border border-card-border dark:border-gray-600
              hover:bg-warm-beige dark:hover:bg-gray-600
              transition-colors duration-75
              focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500
            "
          >
            Cancel
          </button>
        </div>
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={onActivate}
      className="
        w-full flex items-center gap-2 px-3 min-h-[44px]
        text-text-muted dark:text-gray-500
        hover:text-terracotta-500 dark:hover:text-blue-400
        hover:bg-[#FDFCFA] dark:hover:bg-gray-800/50
        border-b border-[#f0ece5] dark:border-gray-800
        transition-colors duration-150
      "
    >
      <span className="w-[18px] h-[18px] flex items-center justify-center text-[16px] font-light flex-shrink-0 text-terracotta-500 dark:text-blue-400">
        +
      </span>
      <span className="text-[13px] font-medium">Add a task</span>
    </button>
  )
}
