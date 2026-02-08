import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import Sidebar from '../Sidebar'
import Header from '../Header'
import useCalendarNavigation from './useCalendarNavigation'
import useCalendarData from './useCalendarData'
import usePageTitle from '../../hooks/usePageTitle'
import CalendarHeader from './CalendarHeader'
import FamilyMemberFilter from './FamilyMemberFilter'
import MonthView from './MonthView'
import WeekViewDesktop from './WeekViewDesktop'
import WeekViewMobile from './WeekViewMobile'
import DayView from './DayView'
import EventFormModal from './EventFormModal'
import TaskFormModal from './TaskFormModal'
import { getWeekDates } from './calendarUtils'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * CalendarPage — top-level orchestrator for the calendar dashboard.
 * Renders CalendarHeader + FamilyMemberFilter + the active view (month/week/day).
 * Manages quick-add modal state for tasks and events.
 */
export default function CalendarPage() {
  usePageTitle('Calendar')

  // Responsive breakpoint: 768px
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth < 768 : false
  )

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const nav = useCalendarNavigation()

  // Active member filter (all members active by default)
  const [activeMembers, setActiveMembers] = useState(null) // null = not initialized yet

  const { tasks, events, familyMembers, loading, error, refetch } = useCalendarData(
    nav.startDate,
    nav.endDate,
    activeMembers
  )

  // Initialize activeMembers once familyMembers load
  useEffect(() => {
    if (activeMembers === null && familyMembers.length > 0) {
      setActiveMembers(new Set(familyMembers.map((m) => m.id)))
    }
  }, [familyMembers, activeMembers])

  const handleToggleMember = (memberId) => {
    setActiveMembers((prev) => {
      const next = new Set(prev)
      if (next.has(memberId)) {
        next.delete(memberId)
      } else {
        next.add(memberId)
      }
      return next
    })
  }

  // Navigate to day view when clicking "View full day" in popover
  const handleViewDay = (date) => {
    nav.setDate(date)
    nav.setView('day')
  }

  const weekDates = useMemo(() => getWeekDates(nav.currentDate), [nav.currentDate])

  // The active members set for filtering (pass null if not initialized to show all)
  const activeMembersForFilter = activeMembers || new Set()

  // --- Quick-add modal state ---
  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [eventModalOpen, setEventModalOpen] = useState(false)
  const [quickAddDate, setQuickAddDate] = useState(null)
  const [quickAddTime, setQuickAddTime] = useState(null)

  // --- Edit modal state ---
  const [editTask, setEditTask] = useState(null)
  const [editEvent, setEditEvent] = useState(null)

  const handleQuickAddTask = (date) => {
    setEditTask(null)
    setQuickAddDate(date || nav.currentDate)
    setQuickAddTime(null)
    setTaskModalOpen(true)
  }

  const handleQuickAddEvent = (date, time) => {
    setEditEvent(null)
    setQuickAddDate(date || nav.currentDate)
    setQuickAddTime(time || null)
    setEventModalOpen(true)
  }

  const handleEditTask = (task) => {
    setEditTask(task)
    setTaskModalOpen(true)
  }

  const handleEditEvent = (event) => {
    setEditEvent(event)
    setEventModalOpen(true)
  }

  const handleToggleComplete = async (task) => {
    try {
      await axios.patch(`${API_BASE}/tasks/${task.id}`, {
        completed: !task.completed,
      })
      refetch()
    } catch (err) {
      console.error('Error toggling task completion:', err)
    }
  }

  const handleModalSaved = () => {
    refetch()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-warm-cream to-warm-beige dark:from-gray-900 dark:to-gray-800 sm:pl-20">
      <Sidebar />
      <Header title="Calendar" />

      <main className="px-4 sm:px-6 py-4">
        <CalendarHeader
          currentDate={nav.currentDate}
          viewMode={nav.viewMode}
          onPrev={nav.goPrev}
          onNext={nav.goNext}
          onToday={nav.goToday}
          onViewChange={nav.setView}
        />

        <FamilyMemberFilter
          familyMembers={familyMembers}
          activeMembers={activeMembersForFilter}
          onToggle={handleToggleMember}
        />

        {/* Content area */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <p className="text-red-500 dark:text-red-400">Failed to load calendar data.</p>
            <button
              onClick={refetch}
              className="mt-2 px-4 py-2 text-sm rounded-lg bg-terracotta-500 dark:bg-blue-600 text-white hover:bg-terracotta-600 dark:hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="rounded-xl bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 p-4">
            {nav.viewMode === 'month' && (
              <MonthView
                currentDate={nav.currentDate}
                tasks={tasks}
                events={events}
                familyMembers={familyMembers}
                selectedDate={nav.selectedDate}
                onSelectDate={nav.setSelectedDate}
                onViewDay={handleViewDay}
                onQuickAddTask={handleQuickAddTask}
                onQuickAddEvent={handleQuickAddEvent}
                onEditTask={handleEditTask}
                onEditEvent={handleEditEvent}
                onToggleComplete={handleToggleComplete}
                isMobile={isMobile}
              />
            )}

            {nav.viewMode === 'week' && !isMobile && (
              <WeekViewDesktop
                weekDates={weekDates}
                tasks={tasks}
                events={events}
                familyMembers={familyMembers}
                onQuickAddTask={handleQuickAddTask}
                onQuickAddEvent={handleQuickAddEvent}
                onEditTask={handleEditTask}
                onEditEvent={handleEditEvent}
                onToggleComplete={handleToggleComplete}
              />
            )}

            {nav.viewMode === 'week' && isMobile && (
              <WeekViewMobile
                weekDates={weekDates}
                tasks={tasks}
                events={events}
                familyMembers={familyMembers}
                selectedDate={nav.selectedDate}
                onSelectDate={nav.setSelectedDate}
                onQuickAddTask={handleQuickAddTask}
                onQuickAddEvent={handleQuickAddEvent}
                onEditTask={handleEditTask}
                onEditEvent={handleEditEvent}
                onToggleComplete={handleToggleComplete}
              />
            )}

            {nav.viewMode === 'day' && (
              <DayView
                date={nav.currentDate}
                tasks={tasks}
                events={events}
                familyMembers={familyMembers}
                onQuickAddTask={handleQuickAddTask}
                onQuickAddEvent={handleQuickAddEvent}
                onEditTask={handleEditTask}
                onEditEvent={handleEditEvent}
                onToggleComplete={handleToggleComplete}
              />
            )}
          </div>
        )}
      </main>

      {/* Modals */}
      <TaskFormModal
        isOpen={taskModalOpen}
        onClose={() => { setTaskModalOpen(false); setEditTask(null) }}
        onSaved={handleModalSaved}
        defaultDate={quickAddDate}
        initialTask={editTask}
      />

      <EventFormModal
        isOpen={eventModalOpen}
        onClose={() => { setEventModalOpen(false); setEditEvent(null) }}
        onSaved={handleModalSaved}
        defaultDate={quickAddDate}
        defaultTime={quickAddTime}
        familyMembers={familyMembers}
        initialEvent={editEvent}
      />
    </div>
  )
}
