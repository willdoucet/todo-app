import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import axios from 'axios'
import TaskListView from '../components/TaskListView'
import TodoForm from '../components/TodoForm'
import ResponsibilityForm from '../components/ResponsibilityForm'
import ConfirmDialog from '../components/ConfirmDialog'
import FilterMenu from '../components/FilterMenu'
import AddButton from '../components/AddButton'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import ScheduleView from '../components/ScheduleView'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function TaskPage() {
  // Task state
  const [tasks, setTasks] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isOpen, setIsOpen] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [editingResponsibility, setEditingResponsibility] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem('taskPageActiveTab') || 'todo'
  })
  const [everyoneID, seteveryoneID] = useState(1)

  // Delete confirmation state
  const [deleteConfirmId, setDeleteConfirmId] = useState(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // Schedule state
  const [familyMembers, setFamilyMembers] = useState([])
  const [responsibilities, setResponsibilities] = useState([])
  const [completions, setCompletions] = useState([])
  const [scheduleDate, setScheduleDate] = useState(new Date())
  const [isLoadingSchedule, setIsLoadingSchedule] = useState(false)

  // Derived values for schedule
  const dateString = scheduleDate.toISOString().split('T')[0]

  // Load tasks on mount
  useEffect(() => {
    const loadTasks = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await axios.get(`${API_BASE}/tasks`)
        console.log(response.data)
        setTasks(response.data)
      } catch (err) {
        console.error('Error loading tasks:', err)
        setError(
          err.response?.data?.detail || 'Failed to load tasks, is the backend running?'
        )
      } finally {
        setIsLoading(false)
      }
    }
    loadTasks()
  }, [])

  // Persist activeTab to localStorage
  useEffect(() => {
    localStorage.setItem('taskPageActiveTab', activeTab)
  }, [activeTab])

  // Load schedule data when tab changes or date changes
  useEffect(() => {
    if (activeTab === 'schedule') {
      loadScheduleData()
    }
  }, [activeTab, dateString])

  useEffect(() => {
    console.log(responsibilities)
  }, [responsibilities])

  // Schedule API handlers
  const loadScheduleData = async () => {
    setIsLoadingSchedule(true)
    try {
      const [membersRes, responsibilitiesRes, completionsRes] = await Promise.all([
        axios.get(`${API_BASE}/family-members`),
        axios.get(`${API_BASE}/responsibilities`),
        axios.get(`${API_BASE}/responsibilities/completions?date=${dateString}`),
      ])
      setFamilyMembers(membersRes.data.filter(m => !m.is_system))
      setResponsibilities(responsibilitiesRes.data)
      console.log(responsibilitiesRes.data)
      setCompletions(completionsRes.data)
    } catch (err) {
      console.error('Error loading schedule data:', err)
      setError(err.response?.data?.detail || 'Failed to load schedule')
    } finally {
      console.log(responsibilities)
      setIsLoadingSchedule(false)
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

  // Task form submit handler
  const handleTaskSubmit = async (data) => {
    if (!data) {
      setIsOpen(false)
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      if (editingTask) {
        const response = await axios.patch(
          `${API_BASE}/tasks/${editingTask.id}`,
          data
        )
        setTasks(tasks.map(t => t.id === editingTask.id ? response.data : t))
        setEditingTask(null)
      } else {
        const response = await axios.post(`${API_BASE}/tasks`, data)
        setTasks([...tasks, response.data])
      }
      setIsOpen(false)
    } catch (err) {
      console.error('Error saving task:', err)
      setError(err.response?.data?.detail || 'Failed to save task')
    } finally {
      setIsSubmitting(false)
    }
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
      // Refresh schedule data
      await loadScheduleData()
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
    setEditingTask(null)
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
      await loadScheduleData()
    } catch (err) {
      console.error('Error deleting responsibility:', err)
      setError(err.response?.data?.detail || 'Failed to delete responsibility')
    } finally {
      setDeleteConfirmId(null)
    }
  }

  // Task handlers
  const deleteTask = async (id) => {
    try {
      await axios.delete(`${API_BASE}/tasks/${id}`)
      setTasks(tasks.filter(t => t.id !== id))
    } catch (err) {
      console.error('Error deleting task:', err)
      setError(err.response?.data?.detail || 'Failed to delete task')
    }
  }

  const toggleComplete = async (id) => {
    const task = tasks.find(t => t.id === id)
    if (!task) return

    // Optimistic update
    setTasks(tasks.map(t => t.id === id ? { ...t, completed: !t.completed } : t))

    try {
      const response = await axios.patch(`${API_BASE}/tasks/${id}`, {
        completed: !task.completed
      })
      setTasks(prev => prev.map(t => t.id === id ? response.data : t))
    } catch (err) {
      // Revert on error
      setTasks(prev => prev.map(t => t.id === id ? task : t))
      console.error('Error toggling task:', err)
      setError(err.response?.data?.detail || 'Failed to update task')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 pb-24 sm:pb-20">
      <Sidebar />
      <Header />

      {/* Task list */}
      <main className={`ml-20 px-4 sm:px-6 lg:px-8 py-6 sm:py-8 ${activeTab === 'schedule' ? '' : 'max-w-4xl'}`}>
        {/* Title and Filter */}
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 dark:text-gray-100 tracking-tight">
            My Tasks
          </h1>
          <FilterMenu />
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('todo')}
            className={`
              px-4 py-2 rounded-lg font-medium text-sm sm:text-base transition-colors duration-200
              ${activeTab === 'todo'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }
            `}
          >
            To Do
          </button>
          <button
            onClick={() => setActiveTab('schedule')}
            className={`
              px-4 py-2 rounded-lg font-medium text-sm sm:text-base transition-colors duration-200
              ${activeTab === 'schedule'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }
            `}
          >
            Schedule
          </button>
        </div>

        {activeTab === 'todo' ? (
          <TaskListView 
            tasks={tasks}
            isLoading={isLoading}
            onToggle={toggleComplete}
            onEdit={(task) => {
              setEditingTask(task)
              setIsOpen(true)
            }}
            onDelete={deleteTask}
          />
        ) : (
          <ScheduleView
            familyMembers={familyMembers}
            responsibilities={responsibilities}
            completions={completions}
            currentDate={scheduleDate}
            isLoading={isLoadingSchedule}
            onToggleCompletion={toggleCompletion}
            onPreviousDay={goToPreviousDay}
            onNextDay={goToNextDay}
            everyoneID={everyoneID}
            onEditResponsibility={handleEditResponsibility}
            onDeleteResponsibility={handleDeleteResponsibility}
          />
        )}
      </main>

      {/* Floating Action Button */}
      <AddButton onClick={() => {
        setEditingTask(null)
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
                bg-white dark:bg-gray-800 p-5 sm:p-6 text-left align-middle shadow-2xl 
                transition-all max-h-[90vh] overflow-y-auto
              ">
                <div className="flex justify-between items-center mb-5 sm:mb-6">
                  <Dialog.Title className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100">
                    {editingTask 
                      ? 'Edit Task' 
                      : editingResponsibility 
                        ? 'Edit Responsibility' 
                        : activeTab === 'todo' 
                          ? 'New Task' 
                          : 'New Responsibility'
                    }
                  </Dialog.Title>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                    aria-label="Close dialog"
                  >
                    <XMarkIcon className="h-5 w-5 sm:h-6 sm:w-6" />
                  </button>
                </div>

                {/* Render appropriate form based on context */}
                {(activeTab === 'todo' && !editingResponsibility) || editingTask ? (
                  <TodoForm
                    initial={editingTask}
                    onSubmit={handleTaskSubmit}
                    onCancel={() => setIsOpen(false)}
                  />
                ) : (
                  <ResponsibilityForm
                    initial={editingResponsibility}
                    onSubmit={handleResponsibilitySubmit}
                    onCancel={() => setIsOpen(false)}
                  />
                )}
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
