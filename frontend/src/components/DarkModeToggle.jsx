import { useDarkMode } from '../contexts/DarkModeContext'
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline'

export default function DarkModeToggle() {
  const { isDark, toggleDarkMode } = useDarkMode()

  return (
    <button
      onClick={toggleDarkMode}
      className="
        p-2 rounded-lg 
        bg-gray-100 dark:bg-gray-800 
        text-gray-700 dark:text-gray-300
        hover:bg-gray-200 dark:hover:bg-gray-700
        transition-colors duration-200
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        dark:focus:ring-offset-gray-800
      "
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? (
        <SunIcon className="h-5 w-5 sm:h-6 sm:w-6" />
      ) : (
        <MoonIcon className="h-5 w-5 sm:h-6 sm:w-6" />
      )}
    </button>
  )
}
