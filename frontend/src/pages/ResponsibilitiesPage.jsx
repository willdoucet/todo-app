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

  const toggleCompletion = async (responsibilityId, memberId) => {
    try {
      const response = await axios.post(
        `${API_BASE}/responsibilities/${responsibilityId}/complete?date=${dateString}&family_member_id=${memberId}`
      )
      if (response.data.completed) {
        setCompletions([...completions, response.data.completion])
      } else {
        setCompletions(completions.filter(
          c => !(c.responsibility_id === responsibilityId && c.family_member_id === memberId)
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
          category: data.category,
          assigned_to: data.assigned_to,
          frequency: data.frequency,
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
        <div className="flex flex-col items-center mb-4">
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-text-primary dark:text-gray-100 tracking-tight mb-2">
            Responsibilities
          </h1>
        </div>

        {/* Tab Navigation */}
        <div className="flex justify-center gap-2 mb-6">
          <button
            onClick={() => setActiveTab('daily')}
            className={`
              px-4 py-2 rounded-lg font-medium text-sm sm:text-base transition-colors duration-200
              ${activeTab === 'daily'
                ? 'bg-peach-100 text-terracotta-700 dark:bg-blue-600 dark:text-white'
                : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-sand dark:hover:bg-gray-600'
              }
            `}
          >
            Daily View
          </button>
          <button
            onClick={() => setActiveTab('edit')}
            className={`
              px-4 py-2 rounded-lg font-medium text-sm sm:text-base transition-colors duration-200
              ${activeTab === 'edit'
                ? 'bg-peach-100 text-terracotta-700 dark:bg-blue-600 dark:text-white'
                : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-sand dark:hover:bg-gray-600'
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

// Edit Responsibilities Tab - flat list view
function EditResponsibilitiesView({ responsibilities, isLoading, onEdit, onDelete }) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-terracotta-500 dark:border-blue-600"></div>
      </div>
    )
  }

  if (responsibilities.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">
          No responsibilities created yet. Click the + button to add one.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-3">
      {responsibilities.map(responsibility => (
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
  )
}
