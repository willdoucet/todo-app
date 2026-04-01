import { useState, useMemo } from 'react'
import TaskItem from './TaskItem'
import SectionHeader from './SectionHeader'
import { EmptyTasksState } from '../shared/EmptyState'

// Render a task and its children recursively
function TaskTree({ task, depth, expandedTasks, onToggle, onEdit, onDelete, onToggleExpand }) {
  const isExpanded = expandedTasks.has(task.id)

  return (
    <>
      <TaskItem
        task={task}
        onToggle={onToggle}
        onEdit={() => onEdit(task)}
        onDelete={onDelete}
        depth={depth}
        onToggleExpand={onToggleExpand}
        isExpanded={isExpanded}
      />
      {isExpanded && task.children?.map(child => (
        <TaskTree
          key={child.id}
          task={child}
          depth={depth + 1}
          expandedTasks={expandedTasks}
          onToggle={onToggle}
          onEdit={onEdit}
          onDelete={onDelete}
          onToggleExpand={onToggleExpand}
        />
      ))}
    </>
  )
}

export default function TaskListView({
  tasks,
  sections = [],
  isLoading,
  onToggle,
  onEdit,
  onDelete,
  onAddTask,
  onEditSection,
  onDeleteSection,
}) {
  const [collapsedSections, setCollapsedSections] = useState(new Set())
  const [expandedTasks, setExpandedTasks] = useState(new Set())

  // Group top-level tasks by section
  const { unsectioned, bySectionId, sectionTaskCounts } = useMemo(() => {
    // Only show top-level tasks (parent_id === null)
    const topLevel = tasks.filter(t => !t.parent_id)
    const unsectioned = topLevel.filter(t => !t.section_id)
    const bySectionId = {}
    const sectionTaskCounts = {}

    sections.forEach(s => {
      bySectionId[s.id] = []
      sectionTaskCounts[s.id] = 0
    })

    topLevel.forEach(t => {
      if (t.section_id && bySectionId[t.section_id]) {
        bySectionId[t.section_id].push(t)
        sectionTaskCounts[t.section_id]++
      }
    })

    return { unsectioned, bySectionId, sectionTaskCounts }
  }, [tasks, sections])

  const toggleSection = (sectionId) => {
    setCollapsedSections(prev => {
      const next = new Set(prev)
      if (next.has(sectionId)) {
        next.delete(sectionId)
      } else {
        next.add(sectionId)
      }
      return next
    })
  }

  const toggleExpand = (taskId) => {
    setExpandedTasks(prev => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-terracotta-500 dark:border-blue-600" />
      </div>
    )
  }

  if (tasks.length === 0 && sections.length === 0) {
    return <EmptyTasksState onAction={onAddTask} />
  }

  return (
    <div className="max-w-[960px]">
      {/* Unsectioned tasks */}
      {unsectioned.map((task, i) => (
        <div key={task.id} className={i === 0 ? 'border-t border-[#f0ece5] dark:border-gray-800' : ''}>
          <TaskTree
            task={task}
            depth={0}
            expandedTasks={expandedTasks}
            onToggle={onToggle}
            onEdit={onEdit}
            onDelete={onDelete}
            onToggleExpand={toggleExpand}
          />
        </div>
      ))}

      {/* Sections */}
      {sections.map(section => {
        const isCollapsed = collapsedSections.has(section.id)
        const sectionTasks = bySectionId[section.id] || []

        return (
          <div key={section.id}>
            <SectionHeader
              section={section}
              taskCount={sectionTaskCounts[section.id] || 0}
              isCollapsed={isCollapsed}
              onToggleCollapse={() => toggleSection(section.id)}
              onEdit={onEditSection}
              onDelete={onDeleteSection}
              onAddTask={() => onAddTask?.(section.id)}
            />
            {!isCollapsed && (
              <div className="transition-all duration-150 ease-out">
                {sectionTasks.length === 0 ? (
                  <button
                    onClick={() => onAddTask?.(section.id)}
                    className="w-full flex items-center gap-2 px-3 py-3 text-text-muted hover:text-text-secondary border border-dashed border-card-border bg-warm-beige/30 dark:bg-gray-800/30 dark:border-gray-700 transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    <span className="text-xs">Add a task</span>
                  </button>
                ) : (
                  sectionTasks.map(task => (
                    <TaskTree
                      key={task.id}
                      task={task}
                      depth={0}
                      expandedTasks={expandedTasks}
                      onToggle={onToggle}
                      onEdit={onEdit}
                      onDelete={onDelete}
                      onToggleExpand={toggleExpand}
                    />
                  ))
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
