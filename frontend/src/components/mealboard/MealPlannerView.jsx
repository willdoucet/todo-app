import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import MealboardNav from './MealboardNav'
import WeekSelector from './WeekSelector'
import MealDayColumn from './MealDayColumn'
import MealPlannerRightPanel from './MealPlannerRightPanel'
import AddMealModal from './AddMealModal'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function getWeekDates(date) {
  const d = new Date(date)
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  const monday = new Date(d.setDate(diff))
  monday.setHours(0, 0, 0, 0)

  const days = []
  for (let i = 0; i < 7; i++) {
    const day = new Date(monday)
    day.setDate(monday.getDate() + i)
    days.push(day)
  }
  return days
}

function formatDateKey(date) {
  return date.toISOString().split('T')[0]
}

function formatCurrentDate() {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric'
  })
}

export default function MealPlannerView() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [weekDates, setWeekDates] = useState(() => getWeekDates(new Date()))
  const [mealPlans, setMealPlans] = useState([])
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showRightPanel, setShowRightPanel] = useState(false)

  // Compact mode for small screens (<768px) - matches calendar column view breakpoint
  const [isCompactMode, setIsCompactMode] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth < 768 : false
  )

  // Modal state
  const [addMealModal, setAddMealModal] = useState({
    open: false,
    date: null,
    category: null
  })

  const todayColumnRef = useRef(null)

  useEffect(() => {
    setWeekDates(getWeekDates(currentDate))
  }, [currentDate])

  useEffect(() => {
    fetchData()
  }, [weekDates])

  useEffect(() => {
    if (todayColumnRef.current && window.innerWidth < 768) {
      todayColumnRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' })
    }
  }, [weekDates])

  // Handle resize for compact mode
  useEffect(() => {
    const handleResize = () => {
      setIsCompactMode(window.innerWidth < 768)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const fetchData = async () => {
    setLoading(true)
    const startDate = formatDateKey(weekDates[0])
    const endDate = formatDateKey(weekDates[6])

    try {
      const [mealPlansRes, recipesRes] = await Promise.all([
        axios.get(`${API_BASE}/meal-plans?start_date=${startDate}&end_date=${endDate}`),
        axios.get(`${API_BASE}/recipes`)
      ])
      setMealPlans(mealPlansRes.data)
      setRecipes(recipesRes.data)
    } catch (err) {
      console.error('Error fetching data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handlePrevWeek = () => {
    const newDate = new Date(currentDate)
    newDate.setDate(newDate.getDate() - 7)
    setCurrentDate(newDate)
  }

  const handleNextWeek = () => {
    const newDate = new Date(currentDate)
    newDate.setDate(newDate.getDate() + 7)
    setCurrentDate(newDate)
  }

  const handleAddMeal = (date, category) => {
    setAddMealModal({ open: true, date, category })
  }

  const handleSaveMeal = async (mealData) => {
    try {
      const response = await axios.post(`${API_BASE}/meal-plans`, mealData)
      setMealPlans([...mealPlans, response.data])
      setAddMealModal({ open: false, date: null, category: null })
    } catch (err) {
      console.error('Error saving meal:', err)
    }
  }

  const handleToggleCooked = async (mealPlan) => {
    try {
      const response = await axios.patch(`${API_BASE}/meal-plans/${mealPlan.id}`, {
        was_cooked: !mealPlan.was_cooked
      })
      setMealPlans(mealPlans.map(mp => mp.id === mealPlan.id ? response.data : mp))
    } catch (err) {
      console.error('Error toggling cooked:', err)
    }
  }

  const handleDeleteMeal = async (mealPlanId) => {
    try {
      await axios.delete(`${API_BASE}/meal-plans/${mealPlanId}`)
      setMealPlans(mealPlans.filter(mp => mp.id !== mealPlanId))
    } catch (err) {
      console.error('Error deleting meal:', err)
    }
  }

  const getMealsForDay = (date) => {
    const dateKey = formatDateKey(date)
    return mealPlans.filter(mp => mp.date === dateKey)
  }

  const getRecipeById = (id) => {
    return recipes.find(r => r.id === id)
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const plannedCount = mealPlans.filter(mp => mp.category === 'DINNER').length
  const totalDays = 7

  const favoriteRecipes = recipes
    .filter(r => r.is_favorite)
    .sort((a, b) => a.name.localeCompare(b.name))

  return (
    <div className="flex-1 flex flex-col xl:flex-row min-h-0">
      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Unified Header - All screen sizes */}
        <div className="px-4 py-3 xl:py-6 border-b border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">

          {/* Desktop Header (>=1200px) - Title/date left, week selector centered */}
          <div className="hidden xl:flex xl:items-center">
            <div className="flex flex-col">
              <span className="text-sm text-text-muted dark:text-gray-400">
                {formatCurrentDate()}
              </span>
              <h1 className="text-2xl font-bold text-text-primary dark:text-gray-100">
                What's Cooking?
              </h1>
            </div>
            <div className="flex-1 flex justify-center">
              <WeekSelector
                weekDates={weekDates}
                onPrevWeek={handlePrevWeek}
                onNextWeek={handleNextWeek}
                compact={false}
              />
            </div>
            <div className="w-32" />
          </div>

          {/* Non-desktop Header (<1200px) - Original 3-column grid */}
          <div className="grid grid-cols-3 items-center xl:hidden">
            <div>
              <MealboardNav variant="dropdown" compact={isCompactMode} />
            </div>
            <div className="flex justify-center">
              <WeekSelector
                weekDates={weekDates}
                onPrevWeek={handlePrevWeek}
                onNextWeek={handleNextWeek}
                compact={isCompactMode}
              />
            </div>
            <div className="flex justify-end">
              <button
                onClick={() => setShowRightPanel(!showRightPanel)}
                className="p-2 rounded-lg bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Week Calendar */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-8 h-8 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="meal-calendar">
              {weekDates.map((date, index) => {
                const isToday = date.getTime() === today.getTime()
                return (
                  <div
                    key={index}
                    ref={isToday ? todayColumnRef : null}
                    className="meal-day-column"
                  >
                    <MealDayColumn
                      date={date}
                      isToday={isToday}
                      meals={getMealsForDay(date)}
                      getRecipeById={getRecipeById}
                      onAddMeal={handleAddMeal}
                      onToggleCooked={handleToggleCooked}
                      onDeleteMeal={handleDeleteMeal}
                    />
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Progress Summary */}
        <div className="px-4 xl:px-6 py-4 border-t border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-sage-100 dark:bg-green-900/30 flex items-center justify-center">
              <svg className="w-5 h-5 text-sage-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-medium text-text-primary dark:text-gray-100">
                {plannedCount} dinner{plannedCount !== 1 ? 's' : ''} planned, {totalDays - plannedCount} to go
              </p>
              <p className="text-sm text-text-secondary dark:text-gray-400">
                You're on track for the week
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2">
              <div className="w-32 h-2 bg-warm-sand dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-terracotta-500 dark:bg-blue-500 rounded-full transition-all"
                  style={{ width: `${(plannedCount / totalDays) * 100}%` }}
                />
              </div>
              <span className="text-sm text-text-muted dark:text-gray-500">
                {plannedCount} of {totalDays} days
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Desktop */}
      <div className="hidden xl:block w-80 border-l border-card-border dark:border-gray-700 flex-shrink-0">
        <MealPlannerRightPanel
          recipes={favoriteRecipes}
          onAddRecipeToDay={(recipe) => setAddMealModal({ open: true, date: today, category: 'DINNER', recipe })}
        />
      </div>

      {/* Right Panel - Mobile Overlay */}
      {showRightPanel && (
        <div className="xl:hidden fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/30" onClick={() => setShowRightPanel(false)} />
          <div className="absolute right-0 top-0 bottom-0 w-80 bg-card-bg dark:bg-gray-800 shadow-xl">
            <div className="flex items-center justify-between p-4 border-b border-card-border dark:border-gray-700">
              <h2 className="font-semibold text-text-primary dark:text-gray-100">Quick Add</h2>
              <button
                onClick={() => setShowRightPanel(false)}
                className="p-2 text-text-muted dark:text-gray-400 hover:text-text-primary dark:hover:text-gray-200"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <MealPlannerRightPanel
              recipes={favoriteRecipes}
              onAddRecipeToDay={(recipe) => {
                setAddMealModal({ open: true, date: today, category: 'DINNER', recipe })
                setShowRightPanel(false)
              }}
            />
          </div>
        </div>
      )}

      {/* Add Meal Modal */}
      <AddMealModal
        isOpen={addMealModal.open}
        onClose={() => setAddMealModal({ open: false, date: null, category: null })}
        onSave={handleSaveMeal}
        date={addMealModal.date}
        category={addMealModal.category}
        recipes={recipes}
        preselectedRecipe={addMealModal.recipe}
      />
    </div>
  )
}
