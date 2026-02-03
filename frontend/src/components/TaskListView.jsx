import TaskItem from './TaskItem'
import { EmptyTasksState } from './EmptyState'

export default function TaskListView({
  tasks,
  isLoading,
  onToggle,
  onEdit,
  onDelete,
  onAddTask,
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-terracotta-500 dark:border-blue-600" />
      </div>
    )
  }

  if (tasks.length === 0) {
    return <EmptyTasksState onAction={onAddTask} />
  }

  return (
    <div className="space-y-3 sm:space-y-4">
      {tasks.map(task => (
        <TaskItem
          key={task.id}
          task={task}
          onToggle={onToggle}
          onEdit={() => onEdit(task)}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}
