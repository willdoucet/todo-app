import { useState, useMemo } from 'react'
import ItemCard from './ItemCard'
import ItemRow from './ItemRow'
import ItemFormModal from './ItemFormModal'
import ItemIcon from './ItemIcon'
import ConfirmDialog from '../shared/ConfirmDialog'
import { buildDeleteDescription } from './itemDeleteCopy'
import ToolbarCount from './ToolbarCount'
import useDelayedFlag from '../../hooks/useDelayedFlag'
import { useItems } from '../../hooks/useItems'
import { useUndoToast } from '../shared/UndoToast'

const CATEGORIES = [
  { value: 'all', label: 'All' },
  { value: 'fruit', label: 'Fruit' },
  { value: 'vegetable', label: 'Vegetable' },
  { value: 'protein', label: 'Protein' },
  { value: 'dairy', label: 'Dairy' },
  { value: 'grain', label: 'Grain' },
]

export default function FoodItemsView() {
  const { items, loading, error, refetch, createItem, updateItem, deleteItem, undoDeleteItem, toggleFavorite } =
    useItems({ type: 'food_item' })
  const { show: showUndoToast } = useUndoToast()
  const showSpinner = useDelayedFlag(loading, 200)

  const [view, setView] = useState('grid')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')

  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, item: null })

  const handleCreate = async (payload) => {
    await createItem(payload)
    setIsFormOpen(false)
  }

  const handleUpdate = async (payload) => {
    await updateItem(editingItem.id, payload)
    setEditingItem(null)
    setIsFormOpen(false)
  }

  const handleDelete = async () => {
    const doomed = deleteConfirm.item
    if (!doomed) return
    setDeleteConfirm({ open: false, item: null })
    try {
      const { undo_token } = await deleteItem(doomed.id)
      showUndoToast({
        item: doomed,
        undoToken: undo_token,
        onUndo: (token) => undoDeleteItem(doomed.id, token),
      })
    } catch (err) {
      console.error('Delete failed:', err)
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

  const filteredItems = useMemo(() => {
    return items
      .filter((it) => {
        const cat = it.food_item_detail?.category || 'Other'
        if (category !== 'all' && cat !== category) return false
        if (search && !it.name.toLowerCase().includes(search.toLowerCase())) return false
        return true
      })
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [items, search, category])

  const isFiltered = search || category !== 'all'

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="px-4 sm:px-6 lg:px-8 py-4 border-b border-card-border dark:border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search food items..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-card-border dark:border-gray-600 bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
            />
          </div>

          <ToolbarCount
            count={filteredItems.length}
            totalCount={isFiltered ? items.length : undefined}
            singular="food item"
            plural="food items"
          />

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
        {showSpinner ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin motion-safe:transition-opacity motion-safe:duration-150" />
          </div>
        ) : loading ? (
          null
        ) : error ? (
          <div className="text-center py-12 text-red-500 dark:text-red-400">
            {error}
            <button onClick={refetch} className="block mx-auto mt-3 underline">Retry</button>
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
          // Grid = food-item cards with auto-fit columns (plan 20260415 Chunk 3).
          // Column count adjusts to viewport: ~3 at 1300px, ~4 at 1600px, 2 at 800px, 1 at mobile.
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            {filteredItems.map((item, i) => (
              <ItemCard
                key={item.id}
                item={item}
                index={i}
                onClick={() => handleEdit(item)}
                onEdit={() => handleEdit(item)}
                onToggleFavorite={() => toggleFavorite(item)}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-card-border dark:border-gray-700 bg-card-bg dark:bg-gray-800 overflow-hidden max-w-5xl mx-auto">
            {filteredItems.map((item, idx) => (
              <ItemRow
                key={item.id}
                item={item}
                isLast={idx === filteredItems.length - 1}
                onClick={() => handleEdit(item)}
                onEdit={() => handleEdit(item)}
                onDelete={() => setDeleteConfirm({ open: true, item })}
                onToggleFavorite={() => toggleFavorite(item)}
              />
            ))}
          </div>
        )}
      </div>

      <ItemFormModal
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        onSubmit={editingItem ? handleUpdate : handleCreate}
        onDelete={(item) => {
          // Close the form first, then open the ConfirmDialog — same flow
          // as the pre-Chunk-4 hover delete path.
          setIsFormOpen(false)
          setEditingItem(null)
          setDeleteConfirm({ open: true, item })
        }}
        type="food_item"
        initialItem={editingItem}
      />

      <ConfirmDialog
        isOpen={deleteConfirm.open}
        onClose={() => setDeleteConfirm({ open: false, item: null })}
        onConfirm={handleDelete}
        title={deleteConfirm.item ? `Delete "${deleteConfirm.item.name}"?` : 'Delete food item?'}
        titleIcon={deleteConfirm.item ? <ItemIcon item={deleteConfirm.item} size={40} /> : null}
        description={buildDeleteDescription(deleteConfirm.item)}
        confirmLabel="Delete"
        variant="danger"
      />
    </div>
  )
}
