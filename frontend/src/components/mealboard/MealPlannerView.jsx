import { useState, useEffect } from 'react'
import axios from 'axios'
import MealboardNav from './MealboardNav'
import WeekSelector from './WeekSelector'
import SwimlaneGrid from './SwimlaneGrid'
import MobileDayView from './MobileDayView'
import ProgressTracker from './ProgressTracker'
import FamilyStrip from './FamilyStrip'
import ShoppingCard from './ShoppingCard'
import AddMealPopover from './AddMealPopover'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function getWeekDates(anchorDate, weekStartDay = 'monday') {
  const d = new Date(anchorDate)
  const dayOfWeek = d.getDay() // 0=Sun, 1=Mon, ..., 6=Sat
  const offset = weekStartDay === 'sunday'
    ? -dayOfWeek
    : (dayOfWeek === 0 ? -6 : 1 - dayOfWeek)
  const start = new Date(d)
  start.setDate(d.getDate() + offset)
  start.setHours(0, 0, 0, 0)

  const days = []
  for (let i = 0; i < 7; i++) {
    const day = new Date(start)
    day.setDate(start.getDate() + i)
    days.push(day)
  }
  return days
}

function formatDateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function formatCurrentDate() {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })
}

export default function MealPlannerView() {
  // Data state
  const [currentDate, setCurrentDate] = useState(new Date())
  const [settings, setSettings] = useState(null)
  const [weekDates, setWeekDates] = useState(() => getWeekDates(new Date(), 'monday'))
  const [slotTypes, setSlotTypes] = useState([])
  const [mealEntries, setMealEntries] = useState([])
  const [familyMembers, setFamilyMembers] = useState([])
  const [recipes, setRecipes] = useState([])
  const [foodItems, setFoodItems] = useState([])
  const [loading, setLoading] = useState(true)

  // Filter state
  const [filterFamilyMemberId, setFilterFamilyMemberId] = useState(null)

  // Add meal popover state
  const [addMealContext, setAddMealContext] = useState(null)
  // Shape: { date: Date, slotTypeId: number, anchorRect?: DOMRect }

  // Compact mode for small screens
  const [isCompactMode, setIsCompactMode] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth < 768 : false
  )

  // Load initial data
  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    try {
      const [settingsRes, slotsRes, familyRes, recipesRes, foodsRes] = await Promise.all([
        axios.get(`${API_BASE}/app-settings/`),
        axios.get(`${API_BASE}/meal-slot-types/`),
        axios.get(`${API_BASE}/family-members/`),
        axios.get(`${API_BASE}/recipes`),
        axios.get(`${API_BASE}/food-items/`),
      ])
      setSettings(settingsRes.data)
      setSlotTypes(slotsRes.data.filter((s) => s.is_active))
      setFamilyMembers(familyRes.data.filter((m) => !m.is_system))
      setRecipes(recipesRes.data)
      setFoodItems(foodsRes.data)

      // Recalculate week dates with actual week_start_day setting
      const dates = getWeekDates(new Date(), settingsRes.data.week_start_day)
      setWeekDates(dates)
    } catch (err) {
      console.error('Failed to load initial data:', err)
    }
  }

  // Load meal entries when week or filter changes
  useEffect(() => {
    if (weekDates.length === 7) {
      fetchMealEntries()
    }
  }, [weekDates, filterFamilyMemberId])

  const fetchMealEntries = async () => {
    setLoading(true)
    try {
      const startDate = formatDateKey(weekDates[0])
      const endDate = formatDateKey(weekDates[6])
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
      if (filterFamilyMemberId) {
        params.set('family_member_id', filterFamilyMemberId)
      }
      const res = await axios.get(`${API_BASE}/meal-entries/?${params}`)
      setMealEntries(res.data)
    } catch (err) {
      console.error('Failed to load meal entries:', err)
    } finally {
      setLoading(false)
    }
  }

  // Resize listener
  useEffect(() => {
    const handleResize = () => setIsCompactMode(window.innerWidth < 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const handlePrevWeek = () => {
    const newDate = new Date(currentDate)
    newDate.setDate(newDate.getDate() - 7)
    setCurrentDate(newDate)
    setWeekDates(getWeekDates(newDate, settings?.week_start_day || 'monday'))
  }

  const handleNextWeek = () => {
    const newDate = new Date(currentDate)
    newDate.setDate(newDate.getDate() + 7)
    setCurrentDate(newDate)
    setWeekDates(getWeekDates(newDate, settings?.week_start_day || 'monday'))
  }

  const handleOpenAddMeal = (date, slotTypeId, anchorRect) => {
    setAddMealContext({ date, slotTypeId, anchorRect })
  }

  const handleCloseAddMeal = () => {
    setAddMealContext(null)
  }

  const handleMealCreated = (newEntry) => {
    setMealEntries((prev) => [...prev, newEntry])
    setAddMealContext(null)
  }

  const handleMealDeleted = (entryId) => {
    setMealEntries((prev) => prev.filter((e) => e.id !== entryId))
  }

  const handleMealUpdated = (updated) => {
    setMealEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
  }

  const handleFamilyFilterToggle = (memberId) => {
    setFilterFamilyMemberId((prev) => (prev === memberId ? null : memberId))
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="px-4 sm:px-6 lg:px-8 py-4 border-b border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
        {/* Desktop header (>=1200px) */}
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

        {/* Mobile/Tablet header */}
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
          <div />
        </div>
      </div>

      {/* Family strip + Shopping card */}
      <div className="px-4 sm:px-6 lg:px-8 py-3 flex flex-col sm:flex-row gap-3 border-b border-card-border dark:border-gray-700">
        <FamilyStrip
          familyMembers={familyMembers}
          selectedId={filterFamilyMemberId}
          onSelect={handleFamilyFilterToggle}
        />
        <ShoppingCard settings={settings} onSettingsChange={setSettings} />
      </div>

      {/* Swimlane grid */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : isCompactMode ? (
          <MobileDayView
            weekDates={weekDates}
            slotTypes={slotTypes}
            mealEntries={mealEntries}
            familyMembers={familyMembers}
            onAddMeal={handleOpenAddMeal}
            onMealUpdated={handleMealUpdated}
            onMealDeleted={handleMealDeleted}
          />
        ) : (
          <SwimlaneGrid
            weekDates={weekDates}
            slotTypes={slotTypes}
            mealEntries={mealEntries}
            familyMembers={familyMembers}
            onAddMeal={handleOpenAddMeal}
            onMealUpdated={handleMealUpdated}
            onMealDeleted={handleMealDeleted}
          />
        )}
      </div>

      {/* Progress tracker */}
      <div className="px-4 sm:px-6 lg:px-8 py-4 border-t border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
        <ProgressTracker slotTypes={slotTypes} mealEntries={mealEntries} />
      </div>

      {/* Add meal popover */}
      {addMealContext && (
        <AddMealPopover
          context={addMealContext}
          slotTypes={slotTypes}
          recipes={recipes}
          foodItems={foodItems}
          familyMembers={familyMembers}
          onClose={handleCloseAddMeal}
          onCreated={handleMealCreated}
        />
      )}
    </div>
  )
}
