import { NavLink, useLocation } from 'react-router-dom'
import { useState, useRef, useEffect } from 'react'

const menuItems = [
  {
    name: 'Meal Planner',
    path: '/mealboard/planner',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    )
  },
  {
    name: 'Recipes',
    path: '/mealboard/recipes',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    )
  },
  {
    name: 'Shopping',
    path: '/mealboard/shopping',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    )
  },
  {
    name: 'Recipe Finder',
    path: '/mealboard/finder',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
    disabled: true
  }
]

export default function MealboardNav({ variant = 'sidebar', compact = false }) {
  const location = useLocation()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  const currentItem = menuItems.find(item => location.pathname.startsWith(item.path)) || menuItems[0]

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (variant === 'dropdown') {
    return (
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`flex items-center gap-2 rounded-lg bg-warm-sand dark:bg-gray-700 text-text-primary dark:text-gray-100 font-medium hover:bg-warm-beige dark:hover:bg-gray-600 transition-colors ${
            compact ? 'p-2' : 'px-3 py-2'
          }`}
        >
          {currentItem.icon}
          {!compact && <span>{currentItem.name}</span>}
          <svg
            className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 mt-2 w-48 bg-card-bg dark:bg-gray-800 rounded-xl shadow-lg border border-card-border dark:border-gray-700 py-2 z-50">
            {menuItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.disabled ? '#' : item.path}
                onClick={(e) => {
                  if (item.disabled) {
                    e.preventDefault()
                  } else {
                    setIsOpen(false)
                  }
                }}
                className={({ isActive }) => `
                  flex items-center gap-3 px-4 py-2.5 text-sm
                  ${item.disabled
                    ? 'text-text-muted dark:text-gray-500 cursor-not-allowed'
                    : isActive
                      ? 'bg-peach-100 text-terracotta-600 dark:bg-blue-600/20 dark:text-blue-400'
                      : 'text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-700'
                  }
                `}
              >
                {item.icon}
                <span>{item.name}</span>
                {item.disabled && (
                  <span className="ml-auto text-xs bg-warm-sand dark:bg-gray-700 px-1.5 py-0.5 rounded">Soon</span>
                )}
              </NavLink>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <nav className="w-56 bg-warm-sand/50 dark:bg-gray-800/50 border-r border-card-border dark:border-gray-700 flex flex-col h-full">
      <div className="p-6 border-b border-card-border dark:border-gray-700">
        <h1 className="text-xl font-bold text-text-primary dark:text-gray-100">Mealboard</h1>
      </div>

      <div className="flex-1 py-4">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.disabled ? '#' : item.path}
            onClick={(e) => item.disabled && e.preventDefault()}
            className={({ isActive }) => `
              flex items-center gap-3 mx-3 px-4 py-3 rounded-xl text-sm font-medium
              transition-all duration-200
              ${item.disabled
                ? 'text-text-muted dark:text-gray-500 cursor-not-allowed'
                : isActive
                  ? 'bg-peach-100 text-terracotta-600 dark:bg-blue-600 dark:text-white shadow-sm'
                  : 'text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-700 hover:text-terracotta-600 dark:hover:text-blue-400'
              }
            `}
          >
            {item.icon}
            <span>{item.name}</span>
            {item.disabled && (
              <span className="ml-auto text-xs bg-warm-sand dark:bg-gray-700 px-1.5 py-0.5 rounded">Soon</span>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
