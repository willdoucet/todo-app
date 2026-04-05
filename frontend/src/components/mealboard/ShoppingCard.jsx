import { useState, useEffect } from 'react'
import axios from 'axios'
import { Link, useNavigate } from 'react-router-dom'
import ShoppingLinkModal from './ShoppingLinkModal'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Shopping list card in the top bar. 3 states:
 * 1. No list linked → "Add a shopping list" → opens link modal
 * 2. List linked, has items → "{N} items on shopping list" → navigates to list
 * 3. List linked, empty → "Shopping list empty" → navigates to list
 */
export default function ShoppingCard({ settings, onSettingsChange }) {
  const [itemCount, setItemCount] = useState(null)
  const [linkedListName, setLinkedListName] = useState(null)
  const [listExists, setListExists] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const navigate = useNavigate()

  const listId = settings?.mealboard_shopping_list_id

  // Fetch item count when linked list changes
  useEffect(() => {
    if (!listId) {
      setItemCount(null)
      setLinkedListName(null)
      return
    }
    refreshCount()
  }, [listId])

  const refreshCount = async () => {
    if (!listId) return
    try {
      const [listRes, tasksRes] = await Promise.all([
        axios.get(`${API_BASE}/lists/${listId}`),
        axios.get(`${API_BASE}/tasks?list_id=${listId}`),
      ])
      setLinkedListName(listRes.data.name)
      setItemCount(tasksRes.data.filter((t) => !t.completed).length)
      setListExists(true)
    } catch (err) {
      if (err.response?.status === 404) {
        // Linked list was deleted — clear the link
        setListExists(false)
        try {
          const res = await axios.patch(`${API_BASE}/app-settings/`, {
            mealboard_shopping_list_id: null,
          })
          onSettingsChange(res.data)
        } catch (e) {
          console.error('Failed to clear stale list link:', e)
        }
      } else {
        console.error('Failed to load shopping list:', err)
      }
    }
  }

  const handleClick = () => {
    if (!listId) {
      setModalOpen(true)
    } else {
      // Navigate to the linked list
      navigate(`/lists?listId=${listId}`)
    }
  }

  const handleListLinked = (updatedSettings) => {
    onSettingsChange(updatedSettings)
    setModalOpen(false)
  }

  // Determine display text
  let displayText = '🛒 Add a shopping list'
  if (listId) {
    if (itemCount === null) {
      displayText = '🛒 Loading...'
    } else if (itemCount === 0) {
      displayText = '🛒 Shopping list empty'
    } else {
      displayText = `🛒 ${itemCount} item${itemCount === 1 ? '' : 's'} on shopping list`
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        className={`
          px-3 py-2 rounded-xl
          bg-card-bg dark:bg-gray-800
          border border-card-border dark:border-gray-700
          hover:border-terracotta-500 dark:hover:border-blue-500
          text-sm font-medium text-text-secondary dark:text-gray-300
          hover:text-terracotta-600 dark:hover:text-blue-400
          whitespace-nowrap transition-all
          flex items-center gap-2
        `}
        title={listId ? `Open ${linkedListName}` : 'Link a shopping list to auto-sync meal ingredients'}
      >
        {displayText}
      </button>

      <ShoppingLinkModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onLinked={handleListLinked}
      />
    </>
  )
}
