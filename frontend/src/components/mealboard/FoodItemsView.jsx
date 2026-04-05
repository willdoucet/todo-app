import { useState, useEffect } from 'react'
import axios from 'axios'
import FoodItemCard from './FoodItemCard'
import FoodItemRow from './FoodItemRow'
import FoodItemFormModal from './FoodItemFormModal'
import ConfirmDialog from '../shared/ConfirmDialog'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const CATEGORIES = [
  { value: 'all', label: 'All' },
  { value: 'fruit', label: 'Fruit' },
  { value: 'vegetable', label: 'Vegetable' },
  { value: 'protein', label: 'Protein' },
  { value: 'dairy', label: 'Dairy' },
  { value: 'grain', label: 'Grain' },
]

export default function FoodItemsView() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // View + filter state
  const [view, setView] = useState('grid') // 'grid' or 'list'
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')

  // Modal state
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, item: null })

  useEffect(() => {
    fetchItems()
  }, [])

  const fetchItems = async () => {
    setLoading(true)
    try {
      const response = await axios.get(`${API_BASE}/food-items/`)
      setItems(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to load food items')
      console.error('Error fetching food items:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (data) => {
    const response = await axios.post(`${API_BASE}/food-items/`, data)
    setItems([...items, response.data])
    setIsFormOpen(false)
  }

  const handleUpdate = async (data) => {
    const response = await axios.patch(`${API_BASE}/food-items/${editingItem.id}`, data)
    setItems(items.map((i) => (i.id === editingItem.id ? response.data : i)))
    setEditingItem(null)
    setIsFormOpen(false)
  }

  const handleDelete = async () => {
    if (!deleteConfirm.item) return
    try {
      await axios.delete(`${API_BASE}/food-items/${deleteConfirm.item.id}`)
      setItems(items.filter((i) => i.id !== deleteConfirm.item.id))
      setDeleteConfirm({ open: false, item: null })
    } catch (err) {
      console.error('Error deleting food item:', err)
    }
  }

  const handleToggleFavorite = async (item) => {
    try {
      const response = await axios.patch(`${API_BASE}/food-items/${item.id}`, {
        is_favorite: !item.is_favorite,
      })
      setItems(items.map((i) => (i.id === item.id ? response.data : i)))
    } catch (err) {
      console.error('Error toggling favorite:', err)
    }
  }

  const handleEdit = (item) => {
    setEditingItem(item)
    setIsFormOpen(true)
  }

  const handleCloseForm = () => {
    setIsFormOpen(false)
    setEditingItem(null)
  }

  // Filter items
  const filteredItems = items
    .filter((item) => {
      if (category !== 'all' && item.category !== category) return false
      if (search && !item.name.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
    .sort((a, b) => a.name.localeCompare(b.name))

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="px-4 sm:px-6 lg:px-8 py-4 border-b border-card-border dark:border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted dark:text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search food items..."
              className="
                w-full pl-9 pr-3 py-2 text-sm rounded-lg
                border border-card-border dark:border-gray-600
                bg-white dark:bg-gray-700
                text-text-primary dark:text-gray-100
                placeholder-text-muted dark:placeholder-gray-500
                focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
              "
            />
          </div>

          {/* View toggle */}
          <div className="flex gap-1 p-1 rounded-lg bg-warm-beige dark:bg-gray-700">
            <button
              type="button"
              onClick={() => setView('grid')}
              title="Grid view"
              aria-label="Grid view"
              className={`p-1.5 rounded-md transition-colors ${
                view === 'grid'
                  ? 'bg-white dark:bg-gray-800 text-terracotta-600 dark:text-blue-400 shadow-sm'
                  : 'text-text-muted dark:text-gray-400 hover:text-text-secondary dark:hover:text-gray-300'
              }`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
              </svg>
            </button>
            <button
              type="button"
              onClick={() => setView('list')}
              title="List view"
              aria-label="List view"
              className={`p-1.5 rounded-md transition-colors ${
                view === 'list'
                  ? 'bg-white dark:bg-gray-800 text-terracotta-600 dark:text-blue-400 shadow-sm'
                  : 'text-text-muted dark:text-gray-400 hover:text-text-secondary dark:hover:text-gray-300'
              }`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <line x1="3" y1="6" x2="21" y2="6" strokeLinecap="round" />
                <line x1="3" y1="12" x2="21" y2="12" strokeLinecap="round" />
                <line x1="3" y1="18" x2="21" y2="18" strokeLinecap="round" />
              </svg>
            </button>
          </div>

          {/* Add button */}
          <button
            onClick={() => setIsFormOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Add Item
          </button>
        </div>

        {/* Category filter pills */}
        <div className="flex flex-wrap gap-2 mt-3">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setCategory(cat.value)}
              className={`
                px-3 py-1 text-xs font-medium rounded-full transition-colors
                ${
                  category === cat.value
                    ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                    : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-sand dark:hover:bg-gray-600'
                }
              `}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-12 text-red-500 dark:text-red-400">
            {error}
            <button onClick={fetchItems} className="block mx-auto mt-3 underline">Retry</button>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-4xl mb-3">🍎</div>
            <h3 className="text-lg font-semibold text-text-primary dark:text-gray-100 mb-2">
              {items.length === 0 ? 'No food items yet' : 'No items match your filters'}
            </h3>
            <p className="text-sm text-text-muted dark:text-gray-400 mb-4">
              {items.length === 0
                ? 'Add simple items like bananas, yogurt, or crackers'
                : 'Try a different search or category'}
            </p>
            {items.length === 0 && (
              <button
                onClick={() => setIsFormOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-colors"
              >
                Add your first food item
              </button>
            )}
          </div>
        ) : view === 'grid' ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {filteredItems.map((item) => (
              <FoodItemCard
                key={item.id}
                item={item}
                onEdit={() => handleEdit(item)}
                onDelete={() => setDeleteConfirm({ open: true, item })}
                onToggleFavorite={() => handleToggleFavorite(item)}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-card-border dark:border-gray-700 bg-card-bg dark:bg-gray-800 overflow-hidden">
            {filteredItems.map((item, idx) => (
              <FoodItemRow
                key={item.id}
                item={item}
                isLast={idx === filteredItems.length - 1}
                onEdit={() => handleEdit(item)}
                onDelete={() => setDeleteConfirm({ open: true, item })}
                onToggleFavorite={() => handleToggleFavorite(item)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      <FoodItemFormModal
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        onSubmit={editingItem ? handleUpdate : handleCreate}
        initialItem={editingItem}
      />

      {/* Delete confirmation */}
      <ConfirmDialog
        isOpen={deleteConfirm.open}
        onClose={() => setDeleteConfirm({ open: false, item: null })}
        onConfirm={handleDelete}
        title="Delete food item?"
        message={`"${deleteConfirm.item?.name}" will be removed. Meal entries that used it will keep their data.`}
        confirmLabel="Delete"
        variant="danger"
      />
    </div>
  )
}
