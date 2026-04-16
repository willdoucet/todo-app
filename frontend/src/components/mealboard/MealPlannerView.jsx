import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import MealboardNav from './MealboardNav'
import WeekSelector from './WeekSelector'
import SwimlaneGrid from './SwimlaneGrid'
import MobileDayView from './MobileDayView'
import ProgressTracker from './ProgressTracker'
import FamilyStrip from './FamilyStrip'
import ShoppingCard from './ShoppingCard'
import AddMealPopover from './AddMealPopover'
import WelcomeCard from './WelcomeCard'
import ItemDetailDrawer from './ItemDetailDrawer'
import ItemFormModal from './ItemFormModal'
import useDelayedFlag from '../../hooks/useDelayedFlag'

const WELCOME_DISMISSED_KEY = 'mealboard_welcome_dismissed'

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

export default function MealPlannerView() {
  // Data state
  const [currentDate, setCurrentDate] = useState(new Date())
  const [settings, setSettings] = useState(null)
  const [weekDates, setWeekDates] = useState(() => getWeekDates(new Date(), 'monday'))
  const [slotTypes, setSlotTypes] = useState([])
  const [mealEntries, setMealEntries] = useState([])
  const [familyMembers, setFamilyMembers] = useState([])
  const [items, setItems] = useState([])  // unified Item model (recipes + food items)
  const [loading, setLoading] = useState(true)
  const [initialLoaded, setInitialLoaded] = useState(false)

  // Filter state
  const [filterFamilyMemberId, setFilterFamilyMemberId] = useState(null)

  // Add meal popover state — context persists across close so the leave animation
  // still has data to render; parent clears it in the Transition.Root afterLeave hook.
  const [addMealContext, setAddMealContext] = useState(null)
  const [isAddMealOpen, setIsAddMealOpen] = useState(false)

  // Compact mode for small screens
  const [isCompactMode, setIsCompactMode] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth < 768 : false
  )

  // Tracks the latest in-flight fetch; stale responses (rapid prev/next clicks)
  // are dropped instead of overwriting fresh data.
  const fetchRequestIdRef = useRef(0)

  // Delayed spinner — only shows for genuinely slow loads (>200ms)
  const showSpinner = useDelayedFlag(!initialLoaded || loading, 200)

  // Welcome card dismissal (tracked in localStorage)
  const [welcomeDismissed, setWelcomeDismissed] = useState(() =>
    typeof window !== 'undefined' ? !!localStorage.getItem(WELCOME_DISMISSED_KEY) : true
  )

  // Item detail drawer state
  const [drawerItemId, setDrawerItemId] = useState(null)

  // Item edit modal state — opened from the detail drawer's Edit button
  const [editingItem, setEditingItem] = useState(null)

  const dismissWelcome = () => {
    localStorage.setItem(WELCOME_DISMISSED_KEY, '1')
    setWelcomeDismissed(true)
  }

  // Load initial data
  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    try {
      const [settingsRes, slotsRes, familyRes, itemsRes] = await Promise.all([
        axios.get(`${API_BASE}/app-settings/`),
        axios.get(`${API_BASE}/meal-slot-types/`),
        axios.get(`${API_BASE}/family-members/`),
        axios.get(`${API_BASE}/items/`),  // unified — fetches both recipes and food items
      ])
      setSettings(settingsRes.data)
      setSlotTypes(slotsRes.data.filter((s) => s.is_active))
      setFamilyMembers(familyRes.data.filter((m) => !m.is_system))
      setItems(itemsRes.data)

      // Recalculate week dates with actual week_start_day setting
      const dates = getWeekDates(new Date(), settingsRes.data.week_start_day)
      setWeekDates(dates)
    } catch (err) {
      console.error('Failed to load initial data:', err)
    } finally {
      setInitialLoaded(true)
    }
  }

  // Load meal entries when week or filter changes
  useEffect(() => {
    if (weekDates.length === 7) {
      fetchMealEntries()
    }
  }, [weekDates, filterFamilyMemberId])

  const fetchMealEntries = async () => {
    const requestId = ++fetchRequestIdRef.current
    setLoading(true)
    try {
      const startDate = formatDateKey(weekDates[0])
      const endDate = formatDateKey(weekDates[6])
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
      if (filterFamilyMemberId) {
        params.set('family_member_id', filterFamilyMemberId)
      }
      const res = await axios.get(`${API_BASE}/meal-entries/?${params}`)
      // Drop stale responses if a newer fetch has already started.
      if (requestId === fetchRequestIdRef.current) {
        setMealEntries(res.data)
      }
    } catch (err) {
      if (requestId === fetchRequestIdRef.current) {
        console.error('Failed to load meal entries:', err)
      }
    } finally {
      if (requestId === fetchRequestIdRef.current) {
        setLoading(false)
      }
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

  const handleGoToToday = () => {
    const today = new Date()
    setCurrentDate(today)
    setWeekDates(getWeekDates(today, settings?.week_start_day || 'monday'))
  }

  const handleOpenAddMeal = (date, slotTypeId, anchorRect) => {
    setAddMealContext({ date, slotTypeId, anchorRect })
    setIsAddMealOpen(true)
  }

  const handleCloseAddMeal = () => {
    setIsAddMealOpen(false)
  }

  const handleMealCreated = (newEntry) => {
    setMealEntries((prev) => [...prev, newEntry])
    setIsAddMealOpen(false)
    // Auto-dismiss welcome card after first meal is added
    if (!welcomeDismissed) {
      dismissWelcome()
    }
  }

  const handleAddFirstMeal = () => {
    // Open add meal for today's dinner (or first available slot) to make onboarding easy
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayInWeek = weekDates.find(
      (d) => d.toDateString() === today.toDateString()
    ) || weekDates[0]
    const dinnerSlot = slotTypes.find((s) => s.name.toLowerCase().includes('dinner')) || slotTypes[0]
    if (dinnerSlot) {
      setAddMealContext({ date: todayInWeek, slotTypeId: dinnerSlot.id })
      setIsAddMealOpen(true)
    }
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

  // Jump to Current Week: hidden when the displayed week already contains today
  const isOnCurrentWeek = (() => {
    if (weekDates.length !== 7) return false
    const t = new Date()
    t.setHours(0, 0, 0, 0)
    const start = new Date(weekDates[0])
    start.setHours(0, 0, 0, 0)
    const end = new Date(weekDates[6])
    end.setHours(0, 0, 0, 0)
    return t >= start && t <= end
  })()

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="px-4 sm:px-6 lg:px-8 py-2.5 border-b border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
        {/* Desktop header (>=1280px / xl) — single row */}
        <div className="hidden xl:flex xl:items-center xl:gap-6">
          <h1 className="text-xl font-bold text-terracotta-600 dark:text-blue-400 tracking-tight">
            What's Cooking?
          </h1>
          <div className="flex-1" />
          {!isOnCurrentWeek && <JumpToCurrentWeekButton onClick={handleGoToToday} />}
          <WeekSelector
            weekDates={weekDates}
            onPrevWeek={handlePrevWeek}
            onNextWeek={handleNextWeek}
            compact={false}
          />
        </div>

        {/* Mobile/Tablet header (<xl).
            Responsive behavior per plan §1654-1662:
              - <768px: button stacks below the nav/selector row (flex-wrap)
              - 768-1199px: button sits left of the selector inline */}
        <div className="xl:hidden flex flex-col gap-2 md:grid md:grid-cols-[auto_1fr_auto] md:items-center md:gap-3">
          <div className="flex items-center justify-between md:justify-start">
            <MealboardNav variant="dropdown" compact={isCompactMode} />
          </div>
          <div className="flex items-center justify-center gap-2">
            {!isOnCurrentWeek && (
              <div className="hidden md:block">
                <JumpToCurrentWeekButton onClick={handleGoToToday} />
              </div>
            )}
            <WeekSelector
              weekDates={weekDates}
              onPrevWeek={handlePrevWeek}
              onNextWeek={handleNextWeek}
              compact={isCompactMode}
            />
          </div>
          {/* mobile-only: full-width Jump to Current Week, stacked below the row */}
          {!isOnCurrentWeek && (
            <div className="md:hidden">
              <JumpToCurrentWeekButton
                onClick={handleGoToToday}
                className="w-full justify-center min-h-[44px]"
              />
            </div>
          )}
          <div className="hidden md:block" />
        </div>
      </div>

      {/* Family strip + Shopping card — family left, shopping always right */}
      <div className="px-4 sm:px-6 lg:px-8 py-3 flex items-center gap-2.5 border-b border-card-border dark:border-gray-700">
        <FamilyStrip
          familyMembers={familyMembers}
          selectedId={filterFamilyMemberId}
          onSelect={handleFamilyFilterToggle}
        />
        <div className="ml-auto">
          <ShoppingCard
            settings={settings}
            onSettingsChange={setSettings}
            mealEntries={mealEntries}
            onRetrySync={fetchMealEntries}
          />
        </div>
      </div>

      {/* Swimlane grid */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-4">
        {/* Welcome card — shown only on empty mealboard when not dismissed */}
        {!loading && !welcomeDismissed && mealEntries.length === 0 && slotTypes.length > 0 && (
          <WelcomeCard onDismiss={dismissWelcome} onAddFirst={handleAddFirstMeal} />
        )}
        {/* Content renders from frame zero — no conditional spinner gate */}
        <div className="relative">
          {isCompactMode ? (
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
              onViewRecipe={(itemId) => setDrawerItemId(itemId)}
              initialLoaded={initialLoaded}
            />
          )}
          {/* Delayed spinner overlay — bare spinner, no backdrop (design review 1A) */}
          {showSpinner && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-8 h-8 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin motion-safe:transition-opacity motion-safe:duration-150" />
            </div>
          )}
        </div>
      </div>

      {/* Progress tracker */}
      <div className="px-4 sm:px-6 lg:px-8 py-4 border-t border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
        <ProgressTracker slotTypes={slotTypes} mealEntries={mealEntries} />
      </div>

      {/* Add meal popover — always mounted so Transition.Root can play leave animations */}
      <AddMealPopover
        context={addMealContext}
        isOpen={isAddMealOpen}
        slotTypes={slotTypes}
        items={items}
        familyMembers={familyMembers}
        onClose={handleCloseAddMeal}
        onCreated={handleMealCreated}
        onAfterLeave={() => setAddMealContext(null)}
      />

      {/* Item detail drawer */}
      <ItemDetailDrawer
        itemId={drawerItemId}
        isOpen={drawerItemId !== null}
        onClose={() => setDrawerItemId(null)}
        onEditItem={(item) => setEditingItem(item)}
      />

      {/* Item edit modal — opened from the drawer's "Edit recipe" button.
          After a successful save, refetch both the items list (for
          AddMealPopover search) and the meal entries (so meal cards pick up
          the renamed item). */}
      <ItemFormModal
        isOpen={editingItem !== null}
        onClose={() => setEditingItem(null)}
        type={editingItem?.item_type}
        initialItem={editingItem}
        onSubmit={async (payload) => {
          const res = await axios.patch(`${API_BASE}/items/${editingItem.id}`, payload)
          setItems((prev) => prev.map((it) => (it.id === editingItem.id ? res.data : it)))
          setEditingItem(null)
          // Meal cards display entry.item.name from the meal-entries payload;
          // refetching rehydrates them with the new name.
          fetchMealEntries()
        }}
      />
    </div>
  )
}

/**
 * "Jump to Current Week" button — primary-styled navigation affordance.
 *
 * Restyled from secondary (bg-warm-sand) to primary terracotta per
 * mealboard-main-page-updates-plan-20260415-164719.md premise 1: navigation
 * discoverability trumps visual primacy protection for "Add meal" (which lives
 * inside swimlanes, not the header). Hidden (not disabled) when the displayed
 * week already contains today (premise 3).
 */
function JumpToCurrentWeekButton({ onClick, className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        inline-flex items-center gap-2 px-4 py-2
        bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700
        text-white rounded-lg font-medium text-sm transition-colors
        ${className}
      `}
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
      Jump to Current Week
    </button>
  )
}
