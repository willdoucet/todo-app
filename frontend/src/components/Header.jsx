import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import DarkModeToggle from './DarkModeToggle'

const menuItems = [
  { name: 'Dashboard', path: '/' },
  { name: 'Lists', path: '/lists' },
  { name: 'Responsibilities', path: '/responsibilities' },
  { name: 'Recipes', path: '/recipes' },
  { name: 'Settings', path: '/settings' },
]

export default function Header() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [weather, setWeather] = useState({ temp: '--', condition: 'Loading...' })
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  useEffect(() => {
    // Update date every minute
    const dateInterval = setInterval(() => {
      setCurrentDate(new Date())
    }, 60000)

    // Fetch weather data (mock for now)
    // In production, you'd call a weather API here
    const fetchWeather = async () => {
      // Mock weather data - replace with actual API call
      // Example: OpenWeatherMap API
      setWeather({
        temp: '72°F',
        condition: 'Sunny'
      })
    }

    fetchWeather()

    return () => clearInterval(dateInterval)
  }, [])

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      month: 'long', 
      day: 'numeric',
      year: 'numeric'
    })
  }

  return (
    <header className="bg-card-bg/90 dark:bg-gray-900/80 backdrop-blur-sm border-b border-card-border/50 dark:border-gray-700/50 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 sm:h-20">
          {/* Left: Mobile Menu Button + Title */}
          <div className="flex items-center gap-3 sm:gap-6 lg:gap-8 sm:pl-4">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="sm:hidden p-2 rounded-lg text-text-secondary dark:text-gray-400 hover:bg-warm-beige dark:hover:bg-gray-800 transition-colors"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>

            {/* Title */}
            <h1 className="text-lg sm:text-xl lg:text-2xl font-bold text-text-primary dark:text-gray-100 tracking-tight">
              Doucet Family Planner
            </h1>

            {/* Weather, Location & Date */}
            <div className="hidden md:flex items-center gap-6">
              {/* Weather */}
              <div className="flex items-center gap-2 text-text-secondary dark:text-gray-300">
                <svg className="w-6 h-6 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                </svg>
                <span className="text-base font-semibold">{weather.temp} • {weather.condition}</span>
              </div>

              {/* Location */}
              <div className="flex items-center gap-2 text-text-secondary dark:text-gray-300">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="text-base font-semibold">Carlsbad, CA</span>
              </div>

              {/* Date */}
              <div className="flex items-center gap-2 text-text-secondary dark:text-gray-300">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span className="text-base font-semibold">{formatDate(currentDate)}</span>
              </div>
            </div>
          </div>

          {/* Right: Dark Mode Toggle */}
          <DarkModeToggle />
        </div>
      </div>

      {/* Mobile Dropdown Menu */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-t border-card-border dark:border-gray-700 bg-card-bg dark:bg-gray-900">
          <nav className="px-4 py-3 space-y-1">
            {menuItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`
                  block px-4 py-3 rounded-lg text-base font-medium transition-colors
                  ${isActive(item.path)
                    ? 'bg-peach-100 text-terracotta-700 dark:bg-blue-600 dark:text-white'
                    : 'text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-800'
                  }
                `}
              >
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  )
}
