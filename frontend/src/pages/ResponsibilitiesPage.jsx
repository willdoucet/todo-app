import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import axios from 'axios'
import ResponsibilityForm from '../components/ResponsibilityForm'
import ResponsibilityCard from '../components/ResponsibilityCard'
import ConfirmDialog from '../components/ConfirmDialog'
import AddButton from '../components/AddButton'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import ScheduleView from '../components/ScheduleView'
import usePageTitle from '../hooks/usePageTitle'
import { EmptyResponsibilitiesState } from '../components/EmptyState'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function ResponsibilitiesPage() {
  // UI state
  const [isOpen, setIsOpen] = useState(false)
  const [editingResponsibility, setEditingResponsibility] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem('responsibilitiesPageActiveTab') || 'daily'
  })
  const [everyoneID, setEveryoneID] = useState(1)

  // Delete confirmation state
  const [deleteConfirmId, setDeleteConfirmId] = useState(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // Schedule state
  const [familyMembers, setFamilyMembers] = useState([])
  const [responsibilities, setResponsibilities] = useState([])
  const [completions, setCompletions] = useState([])
  const [scheduleDate, setScheduleDate] = useState(new Date())
  const [isLoading, setIsLoading] = useState(false)

  // Derived values for schedule
  const dateString = scheduleDate.toISOString().split('T')[0]

  // Update page title
  usePageTitle('Responsibilities')

  // Persist activeTab to localStorage
  useEffect(() => {
    localStorage.setItem('responsibilitiesPageActiveTab', activeTab)
  }, [activeTab])

  // Load data on mount and when date changes (for daily view)
  useEffect(() => {
    loadData()
  }, [dateString])

  // API handlers
  const loadData = async () => {
    setIsLoading(true)
    try {
      const [membersRes, responsibilitiesRes, completionsRes] = await Promise.all([
        axios.get(`${API_BASE}/family-members`),
        axios.get(`${API_BASE}/responsibilities`),
        axios.get(`${API_BASE}/responsibilities/completions?date=${dateString}`),
      ])
      setFamilyMembers(membersRes.data.filter(m => !m.is_system))
      setResponsibilities(responsibilitiesRes.data)
      setCompletions(completionsRes.data)
    } catch (err) {
      console.error('Error loading data:', err)
      setError(err.response?.data?.detail || 'Failed to load responsibilities')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleCompletion = async (responsibilityId, memberId, category) => {
    try {
      const response = await axios.post(
        `${API_BASE}/responsibilities/${responsibilityId}/complete?date=${dateString}&family_member_id=${memberId}&category=${category}`
      )
      if (response.data.completed) {
        setCompletions([...completions, response.data.completion])
      } else {
        setCompletions(completions.filter(
          c => !(c.responsibility_id === responsibilityId && c.family_member_id === memberId && c.category === category)
        ))
      }
    } catch (err) {
      console.error('Error toggling completion:', err)
      setError(err.response?.data?.detail || 'Failed to toggle completion')
    }
  }

  const goToPreviousDay = () => {
    const newDate = new Date(scheduleDate)
    newDate.setDate(newDate.getDate() - 1)
    setScheduleDate(newDate)
  }

  const goToNextDay = () => {
    const newDate = new Date(scheduleDate)
    newDate.setDate(newDate.getDate() + 1)
    setScheduleDate(newDate)
  }

  // Responsibility form submit handler
  const handleResponsibilitySubmit = async (data) => {
    if (!data) {
      setIsOpen(false)
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      if (editingResponsibility) {
        // Update existing responsibility
        await axios.patch(`${API_BASE}/responsibilities/${data.id}`, {
          title: data.title,
          description: data.description,
          categories: data.categories,
          assigned_to: data.assigned_to,
          frequency: data.frequency,
          icon_url: data.icon_url,
        })
        setEditingResponsibility(null)
      } else {
        // Create new responsibility
        await axios.post(`${API_BASE}/responsibilities`, data)
      }
      // Refresh data
      await loadData()
      setIsOpen(false)
    } catch (err) {
      console.error('Error saving responsibility:', err)
      setError(err.response?.data?.detail || 'Failed to save responsibility')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Responsibility handlers
  const handleEditResponsibility = (responsibility) => {
    setEditingResponsibility(responsibility)
    setIsOpen(true)
  }

  const handleDeleteResponsibility = (id) => {
    setDeleteConfirmId(id)
    setShowDeleteConfirm(true)
  }

  const confirmDeleteResponsibility = async () => {
    if (!deleteConfirmId) return

    try {
      await axios.delete(`${API_BASE}/responsibilities/${deleteConfirmId}`)
      await loadData()
    } catch (err) {
      console.error('Error deleting responsibility:', err)
      setError(err.response?.data?.detail || 'Failed to delete responsibility')
    } finally {
      setDeleteConfirmId(null)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-warm-cream to-warm-beige dark:from-gray-900 dark:to-gray-800 pb-24 sm:pb-20 sm:pl-20">
      <Sidebar />
      <Header />

      <main className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8 mx-auto max-w-7xl">
        {/* Title */}
        <div className="mb-6">
          <h1 className="text-xl sm:text-2xl font-semibold text-text-primary dark:text-gray-100">
            Responsibilities
          </h1>
        </div>

        {/* Tab Navigation - Segmented Control */}
        <div className="flex gap-1 mb-6 p-1 bg-warm-sand/50 dark:bg-gray-800/50 rounded-xl w-fit">
          <button
            onClick={() => setActiveTab('daily')}
            className={`
              px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200
              ${activeTab === 'daily'
                ? 'bg-white text-terracotta-600 shadow-sm dark:bg-gray-700 dark:text-white'
                : 'text-text-secondary hover:text-text-primary dark:text-gray-400 dark:hover:text-gray-200'
              }
            `}
          >
            Daily View
          </button>
          <button
            onClick={() => setActiveTab('edit')}
            className={`
              px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200
              ${activeTab === 'edit'
                ? 'bg-white text-terracotta-600 shadow-sm dark:bg-gray-700 dark:text-white'
                : 'text-text-secondary hover:text-text-primary dark:text-gray-400 dark:hover:text-gray-200'
              }
            `}
          >
            Edit Responsibilities
          </button>
        </div>

        {/* Error display */}
        {error && (
          <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {activeTab === 'daily' ? (
          <ScheduleView
            familyMembers={familyMembers}
            responsibilities={responsibilities}
            completions={completions}
            currentDate={scheduleDate}
            isLoading={isLoading}
            onToggleCompletion={toggleCompletion}
            onPreviousDay={goToPreviousDay}
            onNextDay={goToNextDay}
            everyoneID={everyoneID}
          />
        ) : (
          <EditResponsibilitiesView
            responsibilities={responsibilities}
            isLoading={isLoading}
            onEdit={handleEditResponsibility}
            onDelete={handleDeleteResponsibility}
            onAdd={() => {
              setEditingResponsibility(null)
              setIsOpen(true)
            }}
          />
        )}
      </main>

      {/* Floating Action Button */}
      <AddButton onClick={() => {
        setEditingResponsibility(null)
        setIsOpen(true)
      }} />

      {/* Create / Edit Modal */}
      <Transition show={isOpen} as="div">
        <Dialog onClose={() => setIsOpen(false)} className="relative z-50">
          {/* Backdrop */}
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/30 dark:bg-black/50" />
          </Transition.Child>

          {/* Panel */}
          <div className="fixed inset-0 flex items-center justify-center p-4 sm:p-6">
            <Transition.Child
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="
                w-full max-w-md transform overflow-hidden rounded-2xl
                bg-card-bg dark:bg-gray-800 p-5 sm:p-6 text-left align-middle shadow-2xl
                transition-all max-h-[90vh] overflow-y-auto
              ">
                <div className="flex justify-between items-center mb-5 sm:mb-6">
                  <Dialog.Title className="text-lg sm:text-xl font-semibold text-text-primary dark:text-gray-100">
                    {editingResponsibility ? 'Edit Responsibility' : 'New Responsibility'}
                  </Dialog.Title>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="text-text-muted dark:text-gray-500 hover:text-text-secondary dark:hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-warm-beige dark:hover:bg-gray-700"
                    aria-label="Close dialog"
                  >
                    <XMarkIcon className="h-5 w-5 sm:h-6 sm:w-6" />
                  </button>
                </div>

                <ResponsibilityForm
                  initial={editingResponsibility}
                  onSubmit={handleResponsibilitySubmit}
                  onCancel={() => setIsOpen(false)}
                />
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={confirmDeleteResponsibility}
        title="Delete Responsibility"
        message="Are you sure you want to delete this responsibility? This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
      />
    </div>
  )
}

// Category metadata for grouping
const CATEGORY_META = {
  MORNING: { icon: '🌅', label: 'Morning' },
  AFTERNOON: { icon: '☀️', label: 'Afternoon' },
  EVENING: { icon: '🌙', label: 'Evening' },
  CHORE: { icon: '🧹', label: 'Chores' },
}

// Edit Responsibilities Tab - grouped by category
function EditResponsibilitiesView({ responsibilities, isLoading, onEdit, onDelete, onAdd }) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-terracotta-500 dark:border-blue-600"></div>
      </div>
    )
  }

  if (responsibilities.length === 0) {
    return <EmptyResponsibilitiesState onAction={onAdd} />
  }

  // Group by category (a responsibility with multiple categories appears in each)
  const grouped = {
    MORNING: responsibilities.filter(r => r.categories.includes('MORNING')),
    AFTERNOON: responsibilities.filter(r => r.categories.includes('AFTERNOON')),
    EVENING: responsibilities.filter(r => r.categories.includes('EVENING')),
    CHORE: responsibilities.filter(r => r.categories.includes('CHORE')),
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {Object.entries(grouped).map(([category, items]) => (
        items.length > 0 && (
          <div key={category}>
            {/* Category header */}
            <h3 className="text-xs font-semibold text-label-green dark:text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <span className="text-sm">{CATEGORY_META[category].icon}</span>
              {CATEGORY_META[category].label}
              <span className="text-text-muted font-normal lowercase">
                · {items.length} {items.length === 1 ? 'item' : 'items'}
              </span>
            </h3>
            <div className="space-y-2">
              {items.map(responsibility => (
                <ResponsibilityCard
                  key={responsibility.id}
                  responsibility={responsibility}
                  isCompleted={false}
                  onToggle={() => {}}
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
              ))}
            </div>
          </div>
        )
      ))}
    </div>
  )
}
