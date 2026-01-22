// components/AddButton.jsx
export default function AddButton({ onClick }) {
    return (
      <button
        onClick={onClick}
        className="
          fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-20
          w-14 h-14 sm:w-16 sm:h-16 rounded-full 
          bg-gradient-to-br from-blue-600 to-blue-700 dark:from-blue-500 dark:to-blue-600 text-white 
          flex items-center justify-center shadow-xl shadow-blue-500/30 dark:shadow-blue-500/50
          hover:from-blue-700 hover:to-blue-800 dark:hover:from-blue-600 dark:hover:to-blue-700 
          hover:shadow-2xl hover:shadow-blue-500/40 dark:hover:shadow-blue-500/60
          active:scale-95 transition-all duration-200
          focus:outline-none focus:ring-4 focus:ring-blue-500/50 dark:focus:ring-blue-400/50
        "
        aria-label="Add new task"
      >
        <svg className="w-7 h-7 sm:w-8 sm:h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </button>
    )
  }