import { useState, useEffect, useMemo } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import axios from 'axios'
import TaskListView from '../components/TaskListView'
import TodoForm from '../components/TodoForm'
import ListPanel from '../components/ListPanel'
import AddButton from '../components/AddButton'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import usePageTitle from '../hooks/usePageTitle'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Returns white or dark text based on background luminance (WCAG contrast)
function getContrastText(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const toLinear = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  const luminance = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b)
  return luminance > 0.4 ? '#1f2937' : '#ffffff'
}

export default function ListsPage() {
  // Lists state
  const [lists, setLists] = useState([])
  const [isLoadingLists, setIsLoadingLists] = useState(true)
  const [selectedListId, setSelectedListId] = useState(() => {
    const saved = localStorage.getItem('selectedListId')
    return saved ? parseInt(saved) : null
  })

  // Tasks state
  const [tasks, setTasks] = useState([])
  const [isLoadingTasks, setIsLoadingTasks] = useState(false)
  const [error, setError] = useState(null)
  const [isOpen, setIsOpen] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Persist selected list to localStorage
  useEffect(() => {
    if (selectedListId) {
      localStorage.setItem('selectedListId', selectedListId.toString())
    }
  }, [selectedListId])

  // Load lists on mount
  useEffect(() => {
    loadLists()
  }, [])

  // Load tasks when selected list changes
  useEffect(() => {
    if (selectedListId) {
      loadTasks(selectedListId)
    }
  }, [selectedListId])

  // Calculate task counts per list
  const taskCounts = useMemo(() => {
    const counts = {}
    tasks.forEach(task => {
      counts[task.list_id] = (counts[task.list_id] || 0) + 1
    })
    return counts
  }, [tasks])

  // API: Load lists
  const loadLists = async () => {
    setIsLoadingLists(true)
    try {
      const response = await axios.get(`${API_BASE}/lists`)
      setLists(response.data)
      
      // Auto-select first list if none selected or selected list doesn't exist
      if (response.data.length > 0) {
        const savedId = localStorage.getItem('selectedListId')
        const savedIdExists = response.data.some(l => l.id === parseInt(savedId))
        
        if (!savedIdExists) {
          setSelectedListId(response.data[0].id)
        }
      }
    } catch (err) {
      console.error('Error loading lists:', err)
      setError(err.response?.data?.detail || 'Failed to load lists')
    } finally {
      setIsLoadingLists(false)
    }
  }

  // API: Create list
  const createList = async (data) => {
    try {
      const response = await axios.post(`${API_BASE}/lists`, data)
      setLists([...lists, response.data])
      setSelectedListId(response.data.id)
    } catch (err) {
      console.error('Error creating list:', err)
      setError(err.response?.data?.detail || 'Failed to create list')
    }
  }

  // API: Update list
  const updateList = async (id, data) => {
    try {
      const response = await axios.patch(`${API_BASE}/lists/${id}`, data)
      setLists(lists.map(l => l.id === id ? response.data : l))
    } catch (err) {
      console.error('Error updating list:', err)
      setError(err.response?.data?.detail || 'Failed to update list')
    }
  }

  // API: Delete list
  const deleteList = async (id) => {
    try {
      await axios.delete(`${API_BASE}/lists/${id}`)
      const newLists = lists.filter(l => l.id !== id)
      setLists(newLists)
      
      // Select another list if the deleted one was selected
      if (selectedListId === id && newLists.length > 0) {
        setSelectedListId(newLists[0].id)
      } else if (newLists.length === 0) {
        setSelectedListId(null)
        setTasks([])
      }
    } catch (err) {
      console.error('Error deleting list:', err)
      setError(err.response?.data?.detail || 'Failed to delete list')
    }
  }

  // API: Load tasks for a list
  const loadTasks = async (listId) => {
    setIsLoadingTasks(true)
    setError(null)

    try {
      const response = await axios.get(`${API_BASE}/tasks?list_id=${listId}`)
      setTasks(response.data)
    } catch (err) {
      console.error('Error loading tasks:', err)
      setError(err.response?.data?.detail || 'Failed to load tasks')
    } finally {
      setIsLoadingTasks(false)
    }
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
        const response = await axios.post(`${API_BASE}/tasks`, {
          ...data,
          list_id: selectedListId,
        })
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

  const selectedList = lists.find(l => l.id === selectedListId)

  // Update page title based on selected list
  usePageTitle(selectedList?.name || 'Lists')

  return (
    <div className="min-h-screen bg-gradient-to-br from-warm-cream to-warm-beige dark:from-gray-900 dark:to-gray-800 pb-24 sm:pb-20 sm:pl-20">
      <Sidebar />
      <Header />

      {/* Flex layout: sidebar + main content (desktop) */}
      <div className="sm:flex sm:h-[calc(100vh-0px)]">
        {/* List Panel (renders mobile drawer + desktop aside internally) */}
        <ListPanel
          lists={lists}
          selectedListId={selectedListId}
          onSelectList={setSelectedListId}
          onCreateList={createList}
          onUpdateList={updateList}
          onDeleteList={deleteList}
          isLoading={isLoadingLists}
          taskCounts={taskCounts}
        />

        {/* Main content area */}
        <main className="flex-1 sm:overflow-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
          <div className="w-full max-w-3xl">
            {/* Error display */}
            {error && (
              <div className="mb-4 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Title pill with list color */}
            <div className="mb-6">
              {selectedList ? (
                <span
                  className="inline-block px-4 py-1.5 rounded-full text-lg sm:text-xl font-semibold"
                  style={{
                    backgroundColor: selectedList.color || '#6B7280',
                    color: getContrastText(selectedList.color || '#6B7280'),
                  }}
                >
                  {selectedList.name}
                </span>
              ) : (
                <h1 className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  My Lists
                </h1>
              )}
            </div>

            {/* Task list or empty state */}
            {!selectedListId ? (
              <div className="text-center py-12">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {lists.length === 0
                    ? 'Create your first list to get started'
                    : 'Select a list to view tasks'
                  }
                </p>
              </div>
            ) : (
              <TaskListView
                tasks={tasks}
                isLoading={isLoadingTasks}
                onToggle={toggleComplete}
                onEdit={(task) => {
                  setEditingTask(task)
                  setIsOpen(true)
                }}
                onDelete={deleteTask}
                onAddTask={() => {
                  setEditingTask(null)
                  setIsOpen(true)
                }}
              />
            )}
          </div>
        </main>
      </div>

      {/* Floating Action Button - only show when a list is selected */}
      {selectedListId && (
        <AddButton onClick={() => {
          setEditingTask(null)
          setIsOpen(true)
        }} />
      )}

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
                    {editingTask ? 'Edit Task' : 'New Task'}
                  </Dialog.Title>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="text-text-muted dark:text-gray-500 hover:text-text-secondary dark:hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-warm-beige dark:hover:bg-gray-700"
                    aria-label="Close dialog"
                  >
                    <XMarkIcon className="h-5 w-5 sm:h-6 sm:w-6" />
                  </button>
                </div>

                <TodoForm
                  initial={editingTask}
                  listId={selectedListId}
                  onSubmit={handleTaskSubmit}
                  onCancel={() => setIsOpen(false)}
                />
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>
    </div>
  )
}
