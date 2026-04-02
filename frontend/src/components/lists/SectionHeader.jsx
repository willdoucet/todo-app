import { useState } from 'react'
import { PencilIcon, TrashIcon } from '@heroicons/react/24/outline'

export default function SectionHeader({
  section,
  taskCount = 0,
  isCollapsed,
  onToggleCollapse,
  onEdit,
  onDelete,
  onAddTask,
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editName, setEditName] = useState(section.name)

  const handleSave = () => {
    if (editName.trim() && editName.trim() !== section.name) {
      onEdit(section.id, { name: editName.trim() })
    }
    setIsEditing(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSave()
    if (e.key === 'Escape') {
      setEditName(section.name)
      setIsEditing(false)
    }
  }

  return (
    <div className="group sticky top-0 z-10 flex items-center gap-2 px-3 py-2 bg-warm-beige dark:bg-gray-800 border-b border-[#f0ece5] dark:border-gray-700">
      {/* Collapse chevron */}
      <button
        type="button"
        onClick={onToggleCollapse}
        className="w-3.5 h-3.5 flex-shrink-0 text-text-muted hover:text-text-secondary transition-transform duration-150"
        style={{ transform: isCollapsed ? 'rotate(0deg)' : 'rotate(90deg)' }}
        aria-label={isCollapsed ? 'Expand section' : 'Collapse section'}
      >
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z" />
        </svg>
      </button>

      {/* Section name */}
      {isEditing ? (
        <input
          type="text"
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          autoFocus
          className="flex-1 text-xs font-semibold uppercase tracking-wider bg-transparent border-b border-terracotta-500 outline-none text-text-primary dark:text-gray-100 pt-0 pb-1.5"
        />
      ) : (
        <span
          className="flex-1 text-xs font-semibold uppercase tracking-wider text-text-secondary dark:text-gray-400 select-none cursor-text"
          onClick={(e) => {
            e.stopPropagation()
            setEditName(section.name)
            setIsEditing(true)
          }}
        >
          {section.name}
        </span>
      )}

      {/* Task count */}
      <span className="text-xs text-text-muted dark:text-gray-500 tabular-nums">
        {taskCount}
      </span>

      {/* Edit/Delete buttons — hover reveal */}
      <div className="hidden sm:flex items-center gap-0.5 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-150">
        <button
          onClick={(e) => {
            e.stopPropagation()
            setEditName(section.name)
            setIsEditing(true)
          }}
          className="p-1 text-text-muted hover:text-text-secondary dark:hover:text-gray-300 rounded hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500"
          aria-label={`Edit section: ${section.name}`}
        >
          <PencilIcon className="w-3 h-3" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(section.id)
          }}
          className="p-1 text-text-muted hover:text-red-500 dark:hover:text-red-400 rounded hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
          aria-label={`Delete section: ${section.name}`}
        >
          <TrashIcon className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}
