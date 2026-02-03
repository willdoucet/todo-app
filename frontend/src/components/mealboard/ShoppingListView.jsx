import { useState, useEffect } from 'react'
import axios from 'axios'
import MealboardNav from './MealboardNav'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function ShoppingListView() {
  const [lists, setLists] = useState([])
  const [linkedListId, setLinkedListId] = useState(() => {
    return localStorage.getItem('mealboard_shopping_list_id') || null
  })
  const [linkedList, setLinkedList] = useState(null)
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [newItemTitle, setNewItemTitle] = useState('')

  useEffect(() => {
    fetchLists()
  }, [])

  useEffect(() => {
    if (linkedListId) {
      fetchLinkedListTasks()
    } else {
      setTasks([])
      setLinkedList(null)
      setLoading(false)
    }
  }, [linkedListId])

  const fetchLists = async () => {
    try {
      const response = await axios.get(`${API_BASE}/lists`)
      setLists(response.data)
    } catch (err) {
      console.error('Error fetching lists:', err)
    }
  }

  const fetchLinkedListTasks = async () => {
    setLoading(true)
    try {
      const [listResponse, tasksResponse] = await Promise.all([
        axios.get(`${API_BASE}/lists/${linkedListId}`),
        axios.get(`${API_BASE}/tasks?list_id=${linkedListId}`)
      ])
      setLinkedList(listResponse.data)
      setTasks(tasksResponse.data)
    } catch (err) {
      console.error('Error fetching linked list:', err)
      if (err.response?.status === 404) {
        handleUnlinkList()
      }
    } finally {
      setLoading(false)
    }
  }

  const handleLinkList = (listId) => {
    localStorage.setItem('mealboard_shopping_list_id', listId)
    setLinkedListId(listId)
  }

  const handleUnlinkList = () => {
    localStorage.removeItem('mealboard_shopping_list_id')
    setLinkedListId(null)
    setLinkedList(null)
    setTasks([])
  }

  const handleToggleTask = async (task) => {
    try {
      await axios.patch(`${API_BASE}/tasks/${task.id}`, {
        completed: !task.completed
      })
      setTasks(tasks.map(t =>
        t.id === task.id ? { ...t, completed: !t.completed } : t
      ))
    } catch (err) {
      console.error('Error toggling task:', err)
    }
  }

  const handleAddItem = async (e) => {
    e.preventDefault()
    if (!newItemTitle.trim() || !linkedListId) return

    try {
      const response = await axios.post(`${API_BASE}/tasks`, {
        title: newItemTitle.trim(),
        list_id: parseInt(linkedListId)
      })
      setTasks([...tasks, response.data])
      setNewItemTitle('')
    } catch (err) {
      console.error('Error adding item:', err)
    }
  }

  const handleDeleteTask = async (taskId) => {
    try {
      await axios.delete(`${API_BASE}/tasks/${taskId}`)
      setTasks(tasks.filter(t => t.id !== taskId))
    } catch (err) {
      console.error('Error deleting task:', err)
    }
  }

  const groupedTasks = tasks.reduce((acc, task) => {
    const completed = task.completed ? 'completed' : 'pending'
    if (!acc[completed]) acc[completed] = []
    acc[completed].push(task)
    return acc
  }, { pending: [], completed: [] })

  if (!linkedListId) {
    return (
      <div className="flex-1 flex flex-col">
        {/* Mobile Navigation */}
        <div className="xl:hidden px-4 py-3 border-b border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
          <MealboardNav variant="dropdown" />
        </div>

        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-md">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-warm-sand dark:bg-gray-700 flex items-center justify-center">
              <svg className="w-10 h-10 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-text-primary dark:text-gray-100 mb-3">
              Link a Shopping List
            </h2>
            <p className="text-text-secondary dark:text-gray-400 mb-6">
              Connect an existing list to use as your meal planning shopping list.
            </p>

            {lists.length > 0 ? (
              <div className="space-y-2">
                {lists.map(list => (
                  <button
                    key={list.id}
                    onClick={() => handleLinkList(list.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-xl hover:border-terracotta-200 dark:hover:border-blue-600 transition-colors text-left"
                  >
                    <span
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: list.color || '#D97452' }}
                    />
                    <span className="flex-1 text-text-primary dark:text-gray-100 font-medium">
                      {list.name}
                    </span>
                    <svg className="w-5 h-5 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-text-muted dark:text-gray-500 text-sm">
                No lists available. Create a list first in the Lists section.
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Mobile Navigation */}
      <div className="xl:hidden px-4 py-3 border-b border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
        <MealboardNav variant="dropdown" />
      </div>

      {/* Header */}
      <div className="px-4 sm:px-6 lg:px-8 py-6 border-b border-card-border dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {linkedList && (
              <span
                className="w-4 h-4 rounded-full flex-shrink-0"
                style={{ backgroundColor: linkedList.color || '#D97452' }}
              />
            )}
            <h1 className="text-2xl font-bold text-text-primary dark:text-gray-100">
              {linkedList?.name || 'Shopping List'}
            </h1>
          </div>
          <button
            onClick={handleUnlinkList}
            className="text-sm text-text-secondary dark:text-gray-400 hover:text-terracotta-600 dark:hover:text-blue-400 transition-colors"
          >
            Change List
          </button>
        </div>
      </div>

      {/* Add Item Form */}
      <form onSubmit={handleAddItem} className="px-4 sm:px-6 lg:px-8 py-4 border-b border-card-border dark:border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={newItemTitle}
            onChange={(e) => setNewItemTitle(e.target.value)}
            placeholder="Add an item..."
            className="flex-1 px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-card-bg dark:bg-gray-800 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={!newItemTitle.trim()}
            className="px-4 py-2.5 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Add
          </button>
        </div>
      </form>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-text-muted dark:text-gray-500">No items in this list yet.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Pending Items */}
            {groupedTasks.pending.length > 0 && (
              <div className="space-y-2">
                {groupedTasks.pending.map(task => (
                  <div
                    key={task.id}
                    className="flex items-center gap-3 px-4 py-3 bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-xl group"
                  >
                    <button
                      onClick={() => handleToggleTask(task)}
                      className="w-5 h-5 rounded-full border-2 border-card-border dark:border-gray-600 hover:border-terracotta-500 dark:hover:border-blue-500 transition-colors flex-shrink-0"
                    />
                    <span className="flex-1 text-text-primary dark:text-gray-100">
                      {task.title}
                    </span>
                    <button
                      onClick={() => handleDeleteTask(task.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-text-muted dark:text-gray-500 hover:text-red-500 transition-all"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Completed Items */}
            {groupedTasks.completed.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-text-muted dark:text-gray-500 mb-2 px-1">
                  Completed ({groupedTasks.completed.length})
                </h3>
                <div className="space-y-2">
                  {groupedTasks.completed.map(task => (
                    <div
                      key={task.id}
                      className="flex items-center gap-3 px-4 py-3 bg-card-bg/50 dark:bg-gray-800/50 border border-card-border dark:border-gray-700 rounded-xl group opacity-60"
                    >
                      <button
                        onClick={() => handleToggleTask(task)}
                        className="w-5 h-5 rounded-full bg-sage-500 dark:bg-blue-600 flex items-center justify-center flex-shrink-0"
                      >
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </button>
                      <span className="flex-1 text-text-secondary dark:text-gray-400 line-through">
                        {task.title}
                      </span>
                      <button
                        onClick={() => handleDeleteTask(task.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-text-muted dark:text-gray-500 hover:text-red-500 transition-all"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
