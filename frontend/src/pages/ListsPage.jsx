import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import axios from 'axios'
import TaskListView from '../components/lists/TaskListView'
import TodoForm from '../components/lists/TodoForm'
import ListPanel from '../components/lists/ListPanel'
import AddButton from '../components/layout/AddButton'
import Header from '../components/layout/Header'
import Sidebar from '../components/layout/Sidebar'
import usePageTitle from '../hooks/usePageTitle'
import useMediaQuery from '../hooks/useMediaQuery'
import { useToast } from '../components/shared/ToastProvider'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
  const [_isSubmitting, setIsSubmitting] = useState(false)
  const [addToSectionId, setAddToSectionId] = useState(null)

  // Inline editing state
  const [editingTaskId, setEditingTaskId] = useState(null)

  // Family members (loaded once, passed down)
  const [familyMembers, setFamilyMembers] = useState([])

  // Responsive
  const isDesktop = useMediaQuery('(min-width: 640px)')

  // Toast notifications
  const toast = useToast()

  // Refs for reconcile guards
  const selectedListIdRef = useRef(selectedListId)
  const reconcileTimerRef = useRef(null)

  // Keep ref in sync
  useEffect(() => { selectedListIdRef.current = selectedListId }, [selectedListId])

  // Persist selected list to localStorage
  useEffect(() => {
    if (selectedListId) {
      localStorage.setItem('selectedListId', selectedListId.toString())
    }
  }, [selectedListId])

  // Load lists on mount
  useEffect(() => {
    loadLists()
    loadFamilyMembers()
  }, [])

  // Load tasks when selected list changes + cancel pending reconcile
  useEffect(() => {
    clearTimeout(reconcileTimerRef.current)
    if (selectedListId) {
      loadTasks(selectedListId)
    }
    return () => clearTimeout(reconcileTimerRef.current)
  }, [selectedListId])

  // Auto-refetch while any task has PENDING_PUSH (iCloud sync in progress).
  // Mirrors useCalendarData.js polling pattern. Celery push runs ~30s after save;
  // poll every 10s until resolved.
  useEffect(() => {
    const hasPending = tasks.some(t => t.sync_status === 'PENDING_PUSH')
    if (!hasPending) return

    const timer = setTimeout(
      () => loadTasks(selectedListIdRef.current, { silent: true }),
      10000
    )
    return () => clearTimeout(timer)
  }, [tasks])

  // Calculate task counts per list
  const taskCounts = useMemo(() => {
    const counts = {}
    tasks.forEach(task => {
      counts[task.list_id] = (counts[task.list_id] || 0) + 1
    })
    return counts
  }, [tasks])

  // API: Load family members (once)
  const loadFamilyMembers = async () => {
    try {
      const response = await axios.get(`${API_BASE}/family-members`)
      setFamilyMembers(response.data)
    } catch (err) {
      console.error('Error loading family members:', err)
    }
  }

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

  // API: Load tasks for a list (with optional silent mode for reconcile)
  const loadTasks = async (listId, { silent = false } = {}) => {
    if (!silent) setIsLoadingTasks(true)
    if (!silent) setError(null)

    try {
      const response = await axios.get(`${API_BASE}/tasks?list_id=${listId}`)
      // Guard: ignore stale responses if user switched lists while in-flight
      if (listId !== selectedListIdRef.current) return
      setTasks(response.data)
    } catch (err) {
      if (!silent) {
        console.error('Error loading tasks:', err)
        setError(err.response?.data?.detail || 'Failed to load tasks')
      }
    } finally {
      if (!silent) setIsLoadingTasks(false)
    }
  }

  // API: Update a single task field (inline auto-save)
  // Uses field-level merge to prevent concurrent PATCH race conditions
  const onUpdateTask = useCallback(async (taskId, fieldData) => {
    // Optimistic update: apply immediately so UI doesn't flash stale data
    let prevTask
    setTasks(prev => prev.map(t => {
      if (t.id === taskId) { prevTask = t; return { ...t, ...fieldData } }
      return t
    }))
    try {
      const response = await axios.patch(`${API_BASE}/tasks/${taskId}`, fieldData)
      // Field-level merge: reconcile with server response
      setTasks(prev => prev.map(t =>
        t.id === taskId
          ? { ...t, ...Object.fromEntries(
              Object.keys(fieldData).map(k => [k, response.data[k]])
            )}
          : t
      ))
      // Schedule silent reconcile to pick up server-derived fields
      clearTimeout(reconcileTimerRef.current)
      reconcileTimerRef.current = setTimeout(
        () => loadTasks(selectedListIdRef.current, { silent: true }),
        1000
      )
    } catch (err) {
      // Revert optimistic update on error
      if (prevTask) setTasks(prev => prev.map(t => t.id === taskId ? prevTask : t))
      console.error('Error updating task:', err)
      const detail = err.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : 'Failed to save — try again'
      toast.error(msg)
    }
  }, [])

  // Task form submit handler (for modal flow — mobile + legacy)
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

  // Inline task creation (from AddTaskRow on desktop)
  const createTaskInline = useCallback(async (title, sectionId) => {
    try {
      const data = { title, list_id: selectedListId, assigned_to: familyMembers[0]?.id }
      if (sectionId) data.section_id = sectionId
      const response = await axios.post(`${API_BASE}/tasks`, data)
      setTasks(prev => [...prev, response.data])
    } catch (err) {
      console.error('Error creating task:', err)
      const detail = err.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : 'Failed to create task'
      toast.error(msg)
    }
  }, [selectedListId, familyMembers, toast])

  // Task handlers
  const deleteTask = useCallback(async (id) => {
    try {
      await axios.delete(`${API_BASE}/tasks/${id}`)
      setTasks(prev => prev.filter(t => t.id !== id))
      if (editingTaskId === id) setEditingTaskId(null)
    } catch (err) {
      console.error('Error deleting task:', err)
      setError(err.response?.data?.detail || 'Failed to delete task')
    }
  }, [editingTaskId])

  const toggleComplete = useCallback(async (id) => {
    const task = tasks.find(t => t.id === id)
    if (!task) return

    // Optimistic update
    setTasks(prev => prev.map(t => t.id === id ? { ...t, completed: !t.completed } : t))

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
  }, [tasks])

  // Inline edit management — one task at a time
  const handleStartEdit = useCallback((taskId) => {
    // If another task is being edited, auto-save is handled by TaskItem's blur
    setEditingTaskId(taskId)
  }, [])

  const handleStopEdit = useCallback(() => {
    setEditingTaskId(null)
  }, [])

  // Mobile modal open (for expand button on mobile)
  const handleOpenModal = useCallback((task) => {
    setEditingTask(task)
    setIsOpen(true)
  }, [])

  const selectedList = lists.find(l => l.id === selectedListId)
  const sections = selectedList?.sections || []

  // Section handlers
  const editSection = async (sectionId, data) => {
    try {
      await axios.patch(`${API_BASE}/sections/${sectionId}`, data)
      await loadLists()
    } catch (err) {
      console.error('Error updating section:', err)
      setError(err.response?.data?.detail || 'Failed to update section')
    }
  }

  const deleteSection = async (sectionId) => {
    try {
      await axios.delete(`${API_BASE}/sections/${sectionId}`)
      await loadLists()
    } catch (err) {
      console.error('Error deleting section:', err)
      setError(err.response?.data?.detail || 'Failed to delete section')
    }
  }

  // Add Section inline editor state
  const [isAddingSectionInline, setIsAddingSectionInline] = useState(false)
  const [newSectionName, setNewSectionName] = useState('')
  const sectionInputRef = useRef(null)

  const createSection = async (name) => {
    if (!selectedListId || !name?.trim()) return
    try {
      await axios.post(`${API_BASE}/lists/${selectedListId}/sections`, { name: name.trim() })
      await loadLists()
    } catch (err) {
      console.error('Error creating section:', err)
      setError(err.response?.data?.detail || 'Failed to create section')
    }
  }

  const handleAddSectionActivate = () => {
    setNewSectionName('')
    setIsAddingSectionInline(true)
    // Focus after render
    setTimeout(() => sectionInputRef.current?.focus(), 0)
  }

  const handleAddSectionSave = () => {
    const trimmed = newSectionName.trim()
    if (trimmed) {
      createSection(trimmed)
    }
    setIsAddingSectionInline(false)
    setNewSectionName('')
  }

  const handleAddSectionCancel = () => {
    setIsAddingSectionInline(false)
    setNewSectionName('')
  }

  const handleAddSectionKeyDown = (e) => {
    if (e.key === 'Enter') handleAddSectionSave()
    if (e.key === 'Escape') handleAddSectionCancel()
  }

  const handleAddSectionBlur = () => {
    if (newSectionName.trim()) {
      handleAddSectionSave()
    } else {
      handleAddSectionCancel()
    }
  }

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
          <div className="w-full">
            {/* Error display */}
            {error && (
              <div className="mb-4 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* List title with colored underline */}
            <div className="mb-6">
              {selectedList ? (
                <div>
                  <div className="flex items-baseline gap-2">
                    <h1 className="text-xl font-semibold text-text-primary dark:text-gray-100">
                      {selectedList.name}
                    </h1>
                    <span className="text-sm text-text-muted dark:text-gray-500">
                      ({tasks.length})
                    </span>
                  </div>
                  <div
                    className="w-[60px] h-1.5 rounded-full mt-1.5"
                    style={{ backgroundColor: selectedList.color || '#6B7280' }}
                  />
                </div>
              ) : (
                <h1 className="text-xl font-semibold text-text-primary dark:text-gray-100">
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
              <>
                <TaskListView
                  tasks={tasks}
                  sections={sections}
                  isLoading={isLoadingTasks}
                  onToggle={toggleComplete}
                  onDelete={deleteTask}
                  onUpdateTask={onUpdateTask}
                  onAddTask={(sectionId) => {
                    setEditingTask(null)
                    setAddToSectionId(sectionId || null)
                    setIsOpen(true)
                  }}
                  onCreateTask={createTaskInline}
                  onEditSection={editSection}
                  onDeleteSection={deleteSection}
                  editingTaskId={editingTaskId}
                  onStartEdit={handleStartEdit}
                  onStopEdit={handleStopEdit}
                  familyMembers={familyMembers}
                  isDesktop={isDesktop}
                  onOpenModal={handleOpenModal}
                />
                {selectedListId && !isLoadingTasks && (
                  isAddingSectionInline ? (
                    <div className="
                      w-full max-w-[960px] flex items-center gap-2 min-h-[48px] px-4
                      bg-warm-beige dark:bg-gray-800
                      border-t border-card-border dark:border-gray-700
                    ">
                      <span className="w-[22px] h-[22px] flex items-center justify-center bg-terracotta-500 dark:bg-blue-600 text-white rounded-[5px] text-[14px] font-bold flex-shrink-0">
                        +
                      </span>
                      <input
                        ref={sectionInputRef}
                        type="text"
                        value={newSectionName}
                        onChange={(e) => setNewSectionName(e.target.value)}
                        onKeyDown={handleAddSectionKeyDown}
                        onBlur={handleAddSectionBlur}
                        placeholder="Section name"
                        className="
                          flex-1 min-w-0 text-[12px] font-semibold uppercase tracking-wider
                          bg-transparent outline-none
                          text-text-primary dark:text-gray-100
                          border-b-2 border-terracotta-500 dark:border-blue-500 py-1
                          placeholder:text-text-muted dark:placeholder:text-gray-500
                        "
                        aria-label="New section name"
                      />
                    </div>
                  ) : (
                    <button
                      onClick={handleAddSectionActivate}
                      className="
                        w-full max-w-[960px] flex items-center gap-2 min-h-[48px] px-4
                        text-terracotta-500 dark:text-blue-400
                        bg-warm-beige dark:bg-gray-800
                        border-t border-card-border dark:border-gray-700
                        hover:bg-[#FDFCFA] dark:hover:bg-gray-800/50
                        transition-colors duration-150
                      "
                    >
                      <span className="w-[22px] h-[22px] flex items-center justify-center bg-terracotta-500 dark:bg-blue-600 text-white rounded-[5px] text-[14px] font-bold flex-shrink-0">
                        +
                      </span>
                      <span className="text-[12px] font-semibold uppercase tracking-wider text-text-muted dark:text-gray-500">
                        Add Section
                      </span>
                    </button>
                  )
                )}
              </>
            )}
          </div>
        </main>
      </div>

      {/* Floating Action Button - mobile only */}
      {selectedListId && !isDesktop && (
        <AddButton onClick={() => {
          setEditingTask(null)
          setAddToSectionId(null)
          setIsOpen(true)
        }} />
      )}

      {/* Create / Edit Modal — mobile only on desktop, always available on mobile */}
      <Transition show={isOpen} as="div" appear>
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
                  sectionId={addToSectionId}
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
