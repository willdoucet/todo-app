import { useState, useRef, useEffect, memo } from 'react'
import SwipeableItem from '../shared/SwipeableItem'
import TaskActionArea from './TaskActionArea'
import InlineTaskFields from './InlineTaskFields'

// Round checkbox — Apple Reminders style (rounded-full)
function CustomCheckbox({ checked, onChange }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={onChange}
      className={`
        w-[18px] h-[18px] rounded-full flex items-center justify-center
        transition-all duration-100 flex-shrink-0
        ${checked
          ? 'bg-terracotta-500 border-terracotta-500 dark:bg-blue-600 dark:border-blue-600'
          : 'border-2 border-[#d4d0c8] dark:border-gray-600 hover:border-terracotta-500 dark:hover:border-blue-500'
        }
        focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500/50 dark:focus-visible:ring-blue-500/50 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900
      `}
    >
      {checked && (
        <svg
          className="w-2.5 h-2.5 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={3}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      )}
    </button>
  )
}

const TaskItem = memo(function TaskItem({
  task,
  onToggle,
  onDelete,
  onUpdateTask,
  depth = 0,
  onToggleExpand,
  isSubtaskExpanded,
  isEditing,
  onStartEdit,
  onStopEdit,
  familyMembers,
  isDesktop,
  onOpenModal,
}) {
  const [editTitle, setEditTitle] = useState(task.title)
  const [isDetailsExpanded, setIsDetailsExpanded] = useState(false)
  const [isTitleFocused, setIsTitleFocused] = useState(false)
  const inputRef = useRef(null)
  const rowRef = useRef(null)

  const memberColor = task.family_member?.color
  const isSystemMember = task.family_member?.is_system || task.family_member?.name === 'Everyone'
  const stripeColor = isSystemMember ? 'transparent' : (memberColor || 'transparent')
  const hasChildren = task.children && task.children.length > 0
  const isEmptyTitle = !editTitle.trim()

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  // Sync editTitle when task changes externally (e.g., after server reconcile
  // from another tab). Skipped while the user is mid-edit so we don't clobber
  // their in-progress text.
  useEffect(() => {
    if (!isEditing) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEditTitle(task.title)
    }
  }, [task.title, isEditing])

  // Click-outside: deselect task and close expanded panel
  useEffect(() => {
    if (!isEditing && !isDetailsExpanded) return

    const handleClickOutside = (e) => {
      if (rowRef.current && !rowRef.current.contains(e.target)) {
        // Save any pending title change, then deselect
        const trimmed = editTitle.trim()
        if (trimmed && trimmed !== task.title) {
          onUpdateTask(task.id, { title: trimmed })
        }
        setIsDetailsExpanded(false)
        setIsTitleFocused(false)
        onStopEdit()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isEditing, isDetailsExpanded, editTitle, task.title, task.id, onUpdateTask, onStopEdit])

  const handleTitleClick = () => {
    if (!isEditing) {
      onStartEdit(task.id)
    }
  }

  const handleSave = () => {
    const trimmed = editTitle.trim()
    if (trimmed && trimmed !== task.title) {
      onUpdateTask(task.id, { title: trimmed })
    }
    setIsTitleFocused(false)
    onStopEdit()
  }

  const handleCancel = () => {
    setEditTitle(task.title)
    setIsTitleFocused(false)
    onStopEdit()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (isEmptyTitle) {
        onDelete(task.id)
      } else {
        handleSave()
      }
    }
    if (e.key === 'Escape') {
      handleCancel()
    }
  }

  const handleBlur = (e) => {
    setIsTitleFocused(false)
    // Don't auto-save/close if focus stays within the task row (action area, expanded panel, etc.)
    if (e.relatedTarget && rowRef.current?.contains(e.relatedTarget)) return
    if (isDetailsExpanded) {
      // Panel is open — save title but don't close edit mode
      const trimmed = editTitle.trim()
      if (trimmed && trimmed !== task.title) {
        onUpdateTask(task.id, { title: trimmed })
      }
      return
    }
    if (isEmptyTitle) {
      handleCancel()
    } else {
      handleSave()
    }
  }

  const handleCheckboxToggle = () => {
    if (isEditing) {
      // Auto-save title, then toggle, then exit edit mode
      const trimmed = editTitle.trim()
      if (trimmed && trimmed !== task.title) {
        onUpdateTask(task.id, { title: trimmed })
      }
      onStopEdit()
    }
    onToggle(task.id)
  }

  const handleToggleDetails = () => {
    if (!isDesktop) {
      // Mobile: open modal instead
      onOpenModal?.(task)
      return
    }
    setIsDetailsExpanded(prev => !prev)
    if (!isEditing) {
      onStartEdit(task.id)
    }
  }

  // Remove completed styling during editing
  const showCompletedStyle = task.completed && !isEditing

  return (
    <SwipeableItem
      onSwipeAction={() => onDelete(task.id)}
      actionType="delete"
      actionLabel="Delete"
    >
      <div
        ref={rowRef}
        className={`
        border-b border-[#f0ece5] dark:border-gray-800
        border-l-[3px]
        transition-colors duration-75
        ${isEditing ? 'bg-[#FDFCFA] dark:bg-gray-800/50' : 'hover:bg-[#f7f4ee] dark:hover:bg-gray-800'}
        ${showCompletedStyle ? 'opacity-50' : ''}
      `}
      style={{ borderLeftColor: stripeColor }}
      >
        {/* Main task row */}
        <div
          className="flex items-center gap-2 px-3 min-h-[48px]"
          style={{ paddingLeft: `${12 + Math.min(depth, 2) * 24}px` }}
        >
          {/* Subtask expand/collapse chevron */}
          {hasChildren ? (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onToggleExpand?.(task.id) }}
              className="w-3 h-3 flex-shrink-0 text-text-muted hover:text-text-secondary transition-transform duration-150"
              style={{ transform: isSubtaskExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}
              aria-label={isSubtaskExpanded ? 'Collapse subtasks' : 'Expand subtasks'}
            >
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z" />
              </svg>
            </button>
          ) : depth > 0 ? (
            <span className="w-3 flex-shrink-0" />
          ) : null}

          <CustomCheckbox
            checked={task.completed}
            onChange={handleCheckboxToggle}
          />

          {/* Title: inline edit or display */}
          <div className="flex-1 min-w-0" onClick={handleTitleClick}>
            {isEditing ? (
              <input
                ref={inputRef}
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={handleBlur}
                onFocus={() => setIsTitleFocused(true)}
                className={`
                  w-full text-[14px] font-medium bg-transparent outline-none
                  text-text-primary dark:text-gray-100
                  border-b-2 py-1
                  placeholder:text-text-muted dark:placeholder:text-gray-500
                  ${!isTitleFocused
                    ? 'border-transparent'
                    : isEmptyTitle
                      ? 'border-red-500 dark:border-red-400'
                      : 'border-terracotta-500 dark:border-blue-500'}
                `}
                placeholder="Task title..."
                aria-label={`Edit task: ${task.title}`}
              />
            ) : (
              <span className={`
                text-[14px] font-medium truncate block cursor-text
                ${showCompletedStyle
                  ? 'line-through text-text-muted dark:text-gray-500'
                  : 'text-text-primary dark:text-gray-100'}
              `}>
                {task.title}
              </span>
            )}
          </div>

          {/* Action area */}
          <div className="task-action-area">
            <TaskActionArea
              task={task}
              isEditing={isEditing}
              isEmptyTitle={isEmptyTitle}
              isDetailsExpanded={isDetailsExpanded}
              onDelete={onDelete}
              onSave={handleSave}
              onCancel={handleCancel}
              onToggleDetails={handleToggleDetails}
            />
          </div>
        </div>

        {/* Expand panel — CSS grid animation (Step 4 will add transition) */}
        <div
          className="grid transition-[grid-template-rows] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]"
          style={{ gridTemplateRows: isDetailsExpanded && isDesktop ? '1fr' : '0fr' }}
        >
          <div className="overflow-hidden">
            {isDetailsExpanded && isDesktop && (
              <div className="px-3 pb-3" style={{ paddingLeft: `${42 + Math.min(depth, 2) * 24}px` }}>
                <div className="p-3.5 bg-[#FDFCFA] dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-[10px] shadow-[inset_0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none">
                  <InlineTaskFields
                    task={task}
                    familyMembers={familyMembers}
                    onUpdateTask={onUpdateTask}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </SwipeableItem>
  )
})

export default TaskItem
