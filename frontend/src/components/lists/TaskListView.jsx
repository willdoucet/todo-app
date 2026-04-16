import { useState, useMemo } from 'react'
import TaskItem from './TaskItem'
import SectionHeader from './SectionHeader'
import AddTaskRow from './AddTaskRow'
import { EmptyTasksState } from '../shared/EmptyState'

// Render a task and its children recursively
function TaskTree({
  task,
  depth,
  expandedTasks,
  onToggle,
  onDelete,
  onUpdateTask,
  onToggleExpand,
  editingTaskId,
  onStartEdit,
  onStopEdit,
  familyMembers,
  isDesktop,
  onOpenModal,
}) {
  const isSubtaskExpanded = expandedTasks.has(task.id)

  return (
    <>
      <TaskItem
        task={task}
        onToggle={onToggle}
        onDelete={onDelete}
        onUpdateTask={onUpdateTask}
        depth={depth}
        onToggleExpand={onToggleExpand}
        isSubtaskExpanded={isSubtaskExpanded}
        isEditing={editingTaskId === task.id}
        onStartEdit={onStartEdit}
        onStopEdit={onStopEdit}
        familyMembers={familyMembers}
        isDesktop={isDesktop}
        onOpenModal={onOpenModal}
      />
      {isSubtaskExpanded && task.children?.map(child => (
        <TaskTree
          key={child.id}
          task={child}
          depth={depth + 1}
          expandedTasks={expandedTasks}
          onToggle={onToggle}
          onDelete={onDelete}
          onUpdateTask={onUpdateTask}
          onToggleExpand={onToggleExpand}
          editingTaskId={editingTaskId}
          onStartEdit={onStartEdit}
          onStopEdit={onStopEdit}
          familyMembers={familyMembers}
          isDesktop={isDesktop}
          onOpenModal={onOpenModal}
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
  onDelete,
  onUpdateTask,
  onAddTask,
  onCreateTask,
  onEditSection,
  onDeleteSection,
  editingTaskId,
  onStartEdit,
  onStopEdit,
  familyMembers = [],
  isDesktop = true,
  onOpenModal,
}) {
  const [collapsedSections, setCollapsedSections] = useState(new Set())
  const [expandedTasks, setExpandedTasks] = useState(new Set())
  // Which add-task row is active (inline input visible). 'unsectioned' or a section ID, null = none
  const [addingInSectionId, setAddingInSectionId] = useState(null)

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

  const taskTreeProps = {
    expandedTasks,
    onToggle,
    onDelete,
    onUpdateTask,
    onToggleExpand: toggleExpand,
    editingTaskId,
    onStartEdit,
    onStopEdit,
    familyMembers,
    isDesktop,
    onOpenModal,
  }

  const hasSections = sections.length > 0

  // Handle AddTaskRow activation — inline on desktop, modal on mobile
  const handleAddTaskClick = (sectionKey) => {
    if (isDesktop) {
      setAddingInSectionId(sectionKey)
    } else {
      onAddTask?.(sectionKey === 'unsectioned' ? undefined : sectionKey)
    }
  }

  // Handle inline add-task save
  const handleAddTaskSave = (title) => {
    const sectionId = addingInSectionId === 'unsectioned' ? null : addingInSectionId
    onCreateTask?.(title, sectionId)
    setAddingInSectionId(null)
  }

  const handleAddTaskCancel = () => {
    setAddingInSectionId(null)
  }

  return (
    <div className="max-w-[960px]">
      {/* Unsectioned tasks */}
      {unsectioned.length > 0 && (
        <>
          {unsectioned.map((task, i) => (
            <div key={task.id} className={i === 0 ? 'border-t border-[#f0ece5] dark:border-gray-800' : ''}>
              <TaskTree task={task} depth={0} {...taskTreeProps} />
            </div>
          ))}
          {/* Add task row after unsectioned tasks */}
          <AddTaskRow
            isActive={addingInSectionId === 'unsectioned'}
            onActivate={() => handleAddTaskClick('unsectioned')}
            onSave={handleAddTaskSave}
            onCancel={handleAddTaskCancel}
          />
        </>
      )}

      {/* If no unsectioned tasks but no sections either, show add row */}
      {unsectioned.length === 0 && !hasSections && (
        <AddTaskRow
          isActive={addingInSectionId === 'unsectioned'}
          onActivate={() => handleAddTaskClick('unsectioned')}
          onSave={handleAddTaskSave}
          onCancel={handleAddTaskCancel}
        />
      )}

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
            />
            {!isCollapsed && (
              <div className="transition-all duration-150 ease-out">
                {sectionTasks.map(task => (
                  <TaskTree key={task.id} task={task} depth={0} {...taskTreeProps} />
                ))}
                {/* Add task row at bottom of each section */}
                <AddTaskRow
                  isActive={addingInSectionId === section.id}
                  onActivate={() => handleAddTaskClick(section.id)}
                  onSave={handleAddTaskSave}
                  onCancel={handleAddTaskCancel}
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
