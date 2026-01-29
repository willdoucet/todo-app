import TaskItem from './TaskItem'

export default function TaskListView({ 
  tasks, 
  isLoading,
  onToggle, 
  onEdit, 
  onDelete 
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
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

      {tasks.length === 0 && (
        <div className="text-center py-16 sm:py-20">
          <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-gray-100 dark:bg-gray-800 mb-4">
            <svg className="w-8 h-8 sm:w-10 sm:h-10 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <p className="text-base sm:text-lg text-gray-500 dark:text-gray-400 font-medium">No tasks yet</p>
          <p className="text-sm sm:text-base text-gray-400 dark:text-gray-500 mt-1">Add your first task to get started!</p>
        </div>
      )}
    </div>
  )
}
