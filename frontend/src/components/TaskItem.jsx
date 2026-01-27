// components/TaskItem.jsx

// Icon component for assigned_to
function AssignedIcon({ familyMember }) {
  const baseClass = "w-4 h-4 sm:w-5 sm:h-5"
  
  // Handle "Everyone" (system member) with group icon
  if (familyMember?.is_system || familyMember?.name === 'Everyone') {
    return (
      <div className="flex items-center justify-center w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-gray-100 dark:bg-gray-700" title="Assigned to Everyone">
        <svg className={`${baseClass} text-gray-500 dark:text-gray-400`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      </div>
    )
  }
  
  // For individual family members, show first letter avatar
  const name = familyMember?.name || '?'
  const initial = name.charAt(0).toUpperCase()
  
  // Generate a consistent color based on the name
  const colors = [
    { bg: 'bg-blue-100 dark:bg-blue-900/40', text: 'text-blue-600 dark:text-blue-400' },
    { bg: 'bg-pink-100 dark:bg-pink-900/40', text: 'text-pink-600 dark:text-pink-400' },
    { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-600 dark:text-green-400' },
    { bg: 'bg-purple-100 dark:bg-purple-900/40', text: 'text-purple-600 dark:text-purple-400' },
    { bg: 'bg-orange-100 dark:bg-orange-900/40', text: 'text-orange-600 dark:text-orange-400' },
  ]
  
  // Simple hash to pick a consistent color
  const colorIndex = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % colors.length
  const color = colors[colorIndex]
  
  return (
    <div 
      className={`flex items-center justify-center w-6 h-6 sm:w-7 sm:h-7 rounded-full ${color.bg}`} 
      title={`Assigned to ${name}`}
    >
      <span className={`text-xs sm:text-sm font-semibold ${color.text}`}>
        {initial}
      </span>
    </div>
  )
}

export default function TaskItem({ task, onToggle, onEdit, onDelete }) {
    const isOverdue = task.due_date && !task.completed && new Date(task.due_date) < new Date()
    
    return (
      <div className={`
        group flex items-start gap-3 sm:gap-4 p-4 sm:p-5 rounded-xl border 
        ${task.completed 
          ? 'bg-gray-50/50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700' 
          : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-md'}
        transition-all duration-200
      `}>
        <input
          type="checkbox"
          checked={task.completed}
          onChange={() => onToggle(task.id)}
          className="
            mt-0.5 sm:mt-1 h-5 w-5 sm:h-6 sm:w-6 rounded border-gray-300 dark:border-gray-600
            text-blue-600 dark:text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
            dark:focus:ring-offset-gray-800 cursor-pointer flex-shrink-0
          "
        />
  
        <div className="flex-1 min-w-0">
          <p className={`
            text-sm sm:text-base font-medium leading-snug
            ${task.completed 
              ? 'line-through text-gray-400 dark:text-gray-500' 
              : 'text-gray-900 dark:text-gray-100'}
          `}>
            {task.title}
          </p>
          {task.description && (
            <p className={`mt-1.5 text-xs sm:text-sm ${
              task.completed ? 'text-gray-400 dark:text-gray-500' : 'text-gray-600 dark:text-gray-400'
            }`}>
              {task.description}
            </p>
          )}
          {task.due_date && (
            <div className="mt-2 flex items-center gap-1.5">
              <svg className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${
                isOverdue ? 'text-red-500 dark:text-red-400' : 'text-gray-400 dark:text-gray-500'
              }`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <p className={`text-xs sm:text-sm font-medium ${
                isOverdue 
                  ? 'text-red-600 dark:text-red-400' 
                  : task.completed 
                    ? 'text-gray-400 dark:text-gray-500' 
                    : 'text-gray-500 dark:text-gray-400'
              }`}>
                Due {new Date(task.due_date).toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric',
                  year: 'numeric'
                })}
              </p>
            </div>
          )}
        </div>

        {/* Status icons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Important icon */}
          {task.important && (
            <div className="flex items-center justify-center w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-amber-100 dark:bg-amber-900/40" title="Important">
              <svg className="w-4 h-4 sm:w-5 sm:h-5 text-amber-500 dark:text-amber-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
            </div>
          )}
          
          {/* Assigned to icon */}
          {task.family_member && (
            <AssignedIcon familyMember={task.family_member} />
          )}
        </div>
  
        {/* Action buttons */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          <button
            onClick={onEdit}
            className="
              sm:opacity-0 sm:group-hover:opacity-100 opacity-100
              px-3 py-1.5 sm:px-3 sm:py-1.5 text-xs sm:text-sm 
              text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 
              hover:bg-blue-50 dark:hover:bg-blue-900/30
              font-medium rounded-lg transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
              dark:focus:ring-offset-gray-800
            "
            aria-label="Edit task"
          >
            <span className="hidden sm:inline">Edit</span>
            <svg className="sm:hidden w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            onClick={() => onDelete(task.id)}
            className="
              sm:opacity-0 sm:group-hover:opacity-100 opacity-100
              px-3 py-1.5 sm:px-3 sm:py-1.5 text-xs sm:text-sm 
              text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 
              hover:bg-red-50 dark:hover:bg-red-900/30
              font-medium rounded-lg transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1
              dark:focus:ring-offset-gray-800
            "
            aria-label="Delete task"
          >
            <span className="hidden sm:inline">Delete</span>
            <svg className="sm:hidden w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    )
  }
