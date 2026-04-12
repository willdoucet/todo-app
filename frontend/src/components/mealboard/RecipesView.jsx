import { useState, useEffect, useMemo, useRef } from 'react'
import { useAutoAnimate } from '@formkit/auto-animate/react'
import axios from 'axios'
import MealboardNav from './MealboardNav'
import RecipeCard from './RecipeCard'
import RecipeRow from './RecipeRow'
import RecipeFormModal from './RecipeFormModal'
import RecipeDetailDrawer from './RecipeDetailDrawer'
import ConfirmDialog from '../shared/ConfirmDialog'
import FoodItemsView from './FoodItemsView'
import ToolbarCount from './ToolbarCount'
import useDelayedFlag from '../../hooks/useDelayedFlag'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const VIEW_PREF_KEY = 'recipe_view_preference'

export default function RecipesView() {
  const [activeTab, setActiveTab] = useState('recipes')

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Mobile Navigation */}
      <div className="xl:hidden px-4 py-3 border-b border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
        <MealboardNav variant="dropdown" />
      </div>

      {/* Segmented control tabs */}
      <div className="px-4 sm:px-6 lg:px-8 pt-4 pb-3">
        <div className="inline-flex rounded-full bg-warm-sand/60 dark:bg-gray-700/60 p-0.5" role="tablist">
          <button
            type="button"
            onClick={() => setActiveTab('recipes')}
            role="tab"
            aria-selected={activeTab === 'recipes'}
            className={`px-5 py-1.5 rounded-full text-sm font-semibold transition-colors duration-200 ${
              activeTab === 'recipes'
                ? 'bg-peach-100 dark:bg-blue-900/40 text-terracotta-600 dark:text-blue-400'
                : 'text-text-secondary dark:text-gray-400 hover:text-terracotta-600 dark:hover:text-blue-400'
            }`}
          >
            Recipes
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('food-items')}
            role="tab"
            aria-selected={activeTab === 'food-items'}
            className={`px-5 py-1.5 rounded-full text-sm font-semibold transition-colors duration-200 ${
              activeTab === 'food-items'
                ? 'bg-peach-100 dark:bg-blue-900/40 text-terracotta-600 dark:text-blue-400'
                : 'text-text-secondary dark:text-gray-400 hover:text-terracotta-600 dark:hover:text-blue-400'
            }`}
          >
            Food Items
          </button>
        </div>
      </div>

      {activeTab === 'recipes' ? <RecipesTab /> : <FoodItemsView />}
    </div>
  )
}

const SORT_OPTIONS = [
  { value: 'name_asc', label: 'A-Z' },
  { value: 'name_desc', label: 'Z-A' },
  { value: 'recent', label: 'Newest' },
  { value: 'cook_time', label: 'Cook Time' },
]

const FAVORITE_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'yes', label: 'Favorites' },
  { value: 'no', label: 'Non-Favorites' },
]

function RecipesTab() {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const showSkeleton = useDelayedFlag(loading, 200)

  // View, filter, search, sort state
  const [view, setView] = useState(() => localStorage.getItem(VIEW_PREF_KEY) || 'grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [filterFavorite, setFilterFavorite] = useState('all')
  const [selectedTags, setSelectedTags] = useState(new Set())
  const [sortBy, setSortBy] = useState('name_asc')
  const [sortOpen, setSortOpen] = useState(false)
  const sortRef = useRef(null)

  // Custom auto-animate: translate + opacity only, no scale (scale distorts card height)
  const gridAnimation = (el, action, oldCoords, newCoords) => {
    let keyframes
    if (action === 'add') {
      keyframes = [
        { opacity: 0, transform: 'translateY(8px)' },
        { opacity: 1, transform: 'translateY(0)' },
      ]
    } else if (action === 'remove') {
      keyframes = [
        { opacity: 1, transform: 'scale(1)' },
        { opacity: 0, transform: 'scale(0.95)' },
      ]
    } else {
      // 'remain' — slide from old position to new
      const dx = oldCoords.left - newCoords.left
      const dy = oldCoords.top - newCoords.top
      keyframes = [
        { transform: `translate(${dx}px, ${dy}px)` },
        { transform: 'translate(0, 0)' },
      ]
    }
    return new KeyframeEffect(el, keyframes, {
      duration: 250,
      easing: 'ease-out',
    })
  }
  const [gridAnimRef] = useAutoAnimate(gridAnimation)
  const [listAnimRef] = useAutoAnimate({ duration: 200, easing: 'ease-out' })

  // Modal/drawer state
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingRecipe, setEditingRecipe] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, recipe: null })
  const [drawerRecipeId, setDrawerRecipeId] = useState(null)

  useEffect(() => { fetchRecipes() }, [])

  // Close sort popover on click outside
  useEffect(() => {
    if (!sortOpen) return
    const handler = (e) => {
      if (sortRef.current && !sortRef.current.contains(e.target)) setSortOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [sortOpen])

  const fetchRecipes = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API_BASE}/recipes`)
      setRecipes(res.data)
      setError(null)
    } catch {
      setError('Failed to load recipes')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (data) => {
    const res = await axios.post(`${API_BASE}/recipes`, data)
    setRecipes([...recipes, res.data])
    setIsFormOpen(false)
  }

  const handleUpdate = async (data) => {
    const res = await axios.patch(`${API_BASE}/recipes/${editingRecipe.id}`, data)
    setRecipes(recipes.map(r => r.id === editingRecipe.id ? res.data : r))
    setEditingRecipe(null)
    setIsFormOpen(false)
  }

  const handleDelete = async () => {
    if (!deleteConfirm.recipe) return
    await axios.delete(`${API_BASE}/recipes/${deleteConfirm.recipe.id}`)
    setRecipes(recipes.filter(r => r.id !== deleteConfirm.recipe.id))
    setDeleteConfirm({ open: false, recipe: null })
  }

  const handleToggleFavorite = async (recipe) => {
    const res = await axios.patch(`${API_BASE}/recipes/${recipe.id}`, { is_favorite: !recipe.is_favorite })
    setRecipes(recipes.map(r => r.id === recipe.id ? res.data : r))
  }

  const handleEdit = (recipe) => { setEditingRecipe(recipe); setIsFormOpen(true) }
  const handleCloseForm = () => { setIsFormOpen(false); setEditingRecipe(null) }

  const handleViewToggle = (v) => {
    setView(v)
    localStorage.setItem(VIEW_PREF_KEY, v)
  }

  const handleTagToggle = (tag) => {
    setSelectedTags(prev => {
      const next = new Set(prev)
      if (next.has(tag)) next.delete(tag)
      else next.add(tag)
      return next
    })
  }

  // Extract unique tags
  const allTags = useMemo(() => {
    const tags = new Set()
    for (const r of recipes) {
      for (const t of (r.tags || [])) tags.add(t)
    }
    return [...tags].sort()
  }, [recipes])

  // Filter + search + sort
  const filteredRecipes = useMemo(() => {
    const q = searchQuery.toLowerCase()
    return recipes
      .filter(r => !q || r.name.toLowerCase().includes(q))
      .filter(r => filterFavorite === 'all' || (filterFavorite === 'yes' ? r.is_favorite : !r.is_favorite))
      .filter(r => selectedTags.size === 0 || r.tags?.some(t => selectedTags.has(t)))
      .sort((a, b) => {
        switch (sortBy) {
          case 'name_asc': return a.name.localeCompare(b.name)
          case 'name_desc': return b.name.localeCompare(a.name)
          case 'recent': return new Date(b.created_at) - new Date(a.created_at)
          case 'cook_time': return (a.cook_time_minutes || 0) - (b.cook_time_minutes || 0)
          default: return 0
        }
      })
  }, [recipes, searchQuery, filterFavorite, selectedTags, sortBy])

  const isFiltered = searchQuery || filterFavorite !== 'all' || selectedTags.size > 0

  const currentSortLabel = SORT_OPTIONS.find(o => o.value === sortBy)?.label || 'Sort'

  return (
    <>
      {/* Toolbar */}
      <div className="px-4 sm:px-6 lg:px-8 py-3 border-b border-card-border dark:border-gray-700">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-[160px] max-w-xs">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search recipes..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-card-border dark:border-gray-600 bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
            />
          </div>

          {/* Recipe count */}
          <ToolbarCount
            count={filteredRecipes.length}
            totalCount={isFiltered ? recipes.length : undefined}
            singular="recipe"
            plural="recipes"
          />

          {/* Grid/list toggle */}
          <div className="flex gap-1 p-1 rounded-lg bg-warm-beige dark:bg-gray-700">
            <button
              type="button"
              onClick={() => handleViewToggle('grid')}
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
              onClick={() => handleViewToggle('list')}
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

          {/* Sort pill popover */}
          <div className="relative" ref={sortRef}>
            <button
              type="button"
              onClick={() => setSortOpen(!sortOpen)}
              className="px-3 py-1.5 text-xs font-medium rounded-full border border-card-border dark:border-gray-600 bg-white dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:border-terracotta-500 dark:hover:border-blue-500 transition-colors"
            >
              {currentSortLabel} ▾
            </button>
            {sortOpen && (
              <div
                className="absolute top-full right-0 mt-1 z-50 min-w-[130px] bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-lg shadow-xl py-1 origin-top-right"
                style={{ animation: 'view-crossfade 150ms ease both, scale-pop 150ms ease both' }}
                role="listbox"
              >
                {SORT_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => { setSortBy(opt.value); setSortOpen(false) }}
                    onKeyDown={(e) => e.key === 'Escape' && setSortOpen(false)}
                    className={`w-full flex items-center gap-2 px-3 py-1.5 text-sm transition-colors text-left ${
                      sortBy === opt.value
                        ? 'text-terracotta-600 dark:text-blue-400 bg-terracotta-50 dark:bg-blue-900/20'
                        : 'text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-700'
                    }`}
                    role="option"
                    aria-selected={sortBy === opt.value}
                  >
                    <span className={`w-4 text-center ${sortBy === opt.value ? '' : 'opacity-0'}`}>✓</span>
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Add Recipe */}
          <button
            onClick={() => setIsFormOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Add Recipe
          </button>
        </div>

        {/* Filter rows */}
        <div className="mt-3 space-y-2">
          {/* Favorite pills */}
          <div className="flex flex-wrap gap-2">
            {FAVORITE_FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => setFilterFavorite(f.value)}
                className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                  filterFavorite === f.value
                    ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                    : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-sand dark:hover:bg-gray-600'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Tag chips — horizontal scroll */}
          {allTags.length > 0 && (
            <div className="relative">
              <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
                {allTags.map((tag, index) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => handleTagToggle(tag)}
                    className={`tag-pill-enter px-2.5 py-0.5 text-[11px] font-medium rounded-full whitespace-nowrap transition-colors flex-shrink-0 ${
                      selectedTags.has(tag)
                        ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                        : 'bg-warm-sand/60 dark:bg-gray-700/60 text-text-muted dark:text-gray-400 hover:bg-warm-sand dark:hover:bg-gray-600'
                    }`}
                    style={{ animationDelay: `${Math.min(index, 6) * 30}ms` }}
                  >
                    {tag}
                  </button>
                ))}
                {selectedTags.size > 0 && (
                  <button
                    type="button"
                    onClick={() => setSelectedTags(new Set())}
                    className="text-[11px] text-text-muted dark:text-gray-500 hover:text-text-secondary dark:hover:text-gray-300 underline whitespace-nowrap flex-shrink-0"
                  >
                    Clear all
                  </button>
                )}
              </div>
              {/* Fade hint for overflow */}
              <div className="absolute right-0 top-0 bottom-1 w-8 bg-gradient-to-l from-white dark:from-gray-900 to-transparent pointer-events-none" />
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-4">
        {showSkeleton ? (
          view === 'grid' ? <GridSkeleton /> : <ListSkeleton />
        ) : loading ? (
          null
        ) : error ? (
          <div className="text-center py-12">
            <p className="text-red-500 dark:text-red-400">{error}</p>
            <button onClick={fetchRecipes} className="mt-4 text-terracotta-600 dark:text-blue-400 hover:underline text-sm">Try again</button>
          </div>
        ) : filteredRecipes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <span className="text-3xl text-text-muted dark:text-gray-500 mb-3">🍳</span>
            <p className="text-lg font-medium text-text-primary dark:text-gray-100">
              {recipes.length === 0 ? 'No recipes yet' : 'No recipes match your filter'}
            </p>
            <p className="text-sm text-text-secondary dark:text-gray-400 mt-1">
              {recipes.length === 0
                ? 'Add your first recipe to get started with meal planning.'
                : 'Try a different search, filter, or tag.'}
            </p>
            {recipes.length === 0 && (
              <button
                onClick={() => setIsFormOpen(true)}
                className="mt-4 px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-colors"
              >
                + Add Recipe
              </button>
            )}
          </div>
        ) : view === 'grid' ? (
          <div
            ref={gridAnimRef}
            className="grid gap-3.5 mx-auto recipe-grid-responsive"
            style={{
              maxWidth: '1400px',
              gridTemplateColumns: 'repeat(5, 1fr)',
              animation: 'view-crossfade 150ms ease both',
            }}
          >
            {filteredRecipes.map((recipe, i) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                index={i}
                onClick={() => setDrawerRecipeId(recipe.id)}
                onEdit={() => handleEdit(recipe)}
                onDelete={() => setDeleteConfirm({ open: true, recipe })}
                onToggleFavorite={() => handleToggleFavorite(recipe)}
              />
            ))}
          </div>
        ) : (
          <div ref={listAnimRef} className="rounded-xl border border-card-border dark:border-gray-700 bg-card-bg dark:bg-gray-800 overflow-hidden max-w-[1400px] mx-auto">
            {filteredRecipes.map((recipe, i) => (
              <RecipeRow
                key={recipe.id}
                recipe={recipe}
                index={i}
                isLast={i === filteredRecipes.length - 1}
                onClick={() => setDrawerRecipeId(recipe.id)}
                onEdit={() => handleEdit(recipe)}
                onDelete={() => setDeleteConfirm({ open: true, recipe })}
                onToggleFavorite={() => handleToggleFavorite(recipe)}
              />
            ))}
          </div>
        )}
      </div>

      <RecipeFormModal
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        onSubmit={editingRecipe ? handleUpdate : handleCreate}
        recipe={editingRecipe}
      />

      <RecipeDetailDrawer
        recipeId={drawerRecipeId}
        isOpen={drawerRecipeId !== null}
        onClose={() => setDrawerRecipeId(null)}
        onEditRecipe={(recipe) => { setDrawerRecipeId(null); handleEdit(recipe) }}
      />

      <ConfirmDialog
        isOpen={deleteConfirm.open}
        onClose={() => setDeleteConfirm({ open: false, recipe: null })}
        onConfirm={handleDelete}
        title="Delete Recipe"
        message={`Are you sure you want to delete "${deleteConfirm.recipe?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
      />
    </>
  )
}

function GridSkeleton() {
  return (
    <div className="grid gap-3.5 mx-auto" style={{ maxWidth: '1400px', gridTemplateColumns: 'repeat(5, 1fr)' }}>
      {[...Array(5)].map((_, i) => (
        <div key={i} className="animate-pulse bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-xl overflow-hidden">
          <div className="aspect-video bg-warm-sand dark:bg-gray-700" />
          <div className="px-2 py-1.5 space-y-1.5">
            <div className="h-3 bg-warm-sand dark:bg-gray-700 rounded w-3/4" />
            <div className="h-2.5 bg-warm-sand dark:bg-gray-700 rounded w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

function ListSkeleton() {
  return (
    <div className="rounded-xl border border-card-border dark:border-gray-700 bg-card-bg dark:bg-gray-800 overflow-hidden max-w-[1400px] mx-auto">
      {[...Array(6)].map((_, i) => (
        <div key={i} className={`animate-pulse flex items-center gap-3 px-4 py-3 ${i < 5 ? 'border-b border-card-border dark:border-gray-700' : ''}`}>
          <div className="w-2 h-2 rounded-full bg-warm-sand dark:bg-gray-700" />
          <div className="flex-1 h-3.5 bg-warm-sand dark:bg-gray-700 rounded w-2/3" />
          <div className="h-3 bg-warm-sand dark:bg-gray-700 rounded w-24" />
        </div>
      ))}
    </div>
  )
}
