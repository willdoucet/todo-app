import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import axios from 'axios'
import MealboardNav from './MealboardNav'
import RecipeCard from './RecipeCard'
import RecipeFormModal from './RecipeFormModal'
import ConfirmDialog from '../ConfirmDialog'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function RecipesView({ favoritesOnly = false }) {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filter and sort state
  const [filterFavorite, setFilterFavorite] = useState(favoritesOnly ? 'yes' : 'all')
  const [sortBy, setSortBy] = useState('name_asc')

  // Modal state
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingRecipe, setEditingRecipe] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, recipe: null })

  useEffect(() => {
    fetchRecipes()
  }, [])

  useEffect(() => {
    if (favoritesOnly) {
      setFilterFavorite('yes')
    }
  }, [favoritesOnly])

  const fetchRecipes = async () => {
    setLoading(true)
    try {
      const response = await axios.get(`${API_BASE}/recipes`)
      setRecipes(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to load recipes')
      console.error('Error fetching recipes:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateRecipe = async (recipeData) => {
    try {
      const response = await axios.post(`${API_BASE}/recipes`, recipeData)
      setRecipes([...recipes, response.data])
      setIsFormOpen(false)
    } catch (err) {
      console.error('Error creating recipe:', err)
      throw err
    }
  }

  const handleUpdateRecipe = async (recipeData) => {
    try {
      const response = await axios.patch(`${API_BASE}/recipes/${editingRecipe.id}`, recipeData)
      setRecipes(recipes.map(r => r.id === editingRecipe.id ? response.data : r))
      setEditingRecipe(null)
      setIsFormOpen(false)
    } catch (err) {
      console.error('Error updating recipe:', err)
      throw err
    }
  }

  const handleDeleteRecipe = async () => {
    if (!deleteConfirm.recipe) return
    try {
      await axios.delete(`${API_BASE}/recipes/${deleteConfirm.recipe.id}`)
      setRecipes(recipes.filter(r => r.id !== deleteConfirm.recipe.id))
      setDeleteConfirm({ open: false, recipe: null })
    } catch (err) {
      console.error('Error deleting recipe:', err)
    }
  }

  const handleToggleFavorite = async (recipe) => {
    try {
      const response = await axios.patch(`${API_BASE}/recipes/${recipe.id}`, {
        is_favorite: !recipe.is_favorite
      })
      setRecipes(recipes.map(r => r.id === recipe.id ? response.data : r))
    } catch (err) {
      console.error('Error toggling favorite:', err)
    }
  }

  const handleEdit = (recipe) => {
    setEditingRecipe(recipe)
    setIsFormOpen(true)
  }

  const handleCloseForm = () => {
    setIsFormOpen(false)
    setEditingRecipe(null)
  }

  // Filter and sort recipes
  const filteredRecipes = recipes
    .filter(recipe => {
      if (filterFavorite === 'yes') return recipe.is_favorite
      if (filterFavorite === 'no') return !recipe.is_favorite
      return true
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'name_asc':
          return a.name.localeCompare(b.name)
        case 'name_desc':
          return b.name.localeCompare(a.name)
        case 'recent':
          return new Date(b.created_at) - new Date(a.created_at)
        case 'cook_time':
          return (a.cook_time_minutes || 0) - (b.cook_time_minutes || 0)
        default:
          return 0
      }
    })

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Mobile Navigation */}
      <div className="xl:hidden px-4 py-3 border-b border-card-border dark:border-gray-700 bg-card-bg/50 dark:bg-gray-800/50">
        <MealboardNav variant="dropdown" />
      </div>

      {/* Header */}
      <div className="px-4 sm:px-6 lg:px-8 py-6 border-b border-card-border dark:border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h1 className="text-2xl font-bold text-text-primary dark:text-gray-100">
            {favoritesOnly ? 'Favorite Recipes' : 'Recipes'}
          </h1>
          <button
            onClick={() => setIsFormOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-xl font-medium transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Recipe
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mt-4">
          {!favoritesOnly && (
            <select
              value={filterFavorite}
              onChange={(e) => setFilterFavorite(e.target.value)}
              className="px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-card-bg dark:bg-gray-800 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
            >
              <option value="all">All Recipes</option>
              <option value="yes">Favorites Only</option>
              <option value="no">Non-Favorites</option>
            </select>
          )}

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-card-bg dark:bg-gray-800 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
          >
            <option value="name_asc">Name (A-Z)</option>
            <option value="name_desc">Name (Z-A)</option>
            <option value="recent">Recently Added</option>
            <option value="cook_time">Cook Time</option>
          </select>
        </div>
      </div>

      {/* Recipe Grid */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-terracotta-500 dark:border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <p className="text-red-500 dark:text-red-400">{error}</p>
            <button
              onClick={fetchRecipes}
              className="mt-4 text-terracotta-600 dark:text-blue-400 hover:underline"
            >
              Try again
            </button>
          </div>
        ) : filteredRecipes.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-warm-sand dark:bg-gray-700 flex items-center justify-center">
              <svg className="w-8 h-8 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <p className="text-text-muted dark:text-gray-500">
              {filterFavorite !== 'all' ? 'No recipes match your filter.' : 'No recipes yet. Add your first recipe!'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredRecipes.map(recipe => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                onEdit={() => handleEdit(recipe)}
                onDelete={() => setDeleteConfirm({ open: true, recipe })}
                onToggleFavorite={() => handleToggleFavorite(recipe)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Recipe Form Modal */}
      <RecipeFormModal
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        onSubmit={editingRecipe ? handleUpdateRecipe : handleCreateRecipe}
        recipe={editingRecipe}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={deleteConfirm.open}
        onClose={() => setDeleteConfirm({ open: false, recipe: null })}
        onConfirm={handleDeleteRecipe}
        title="Delete Recipe"
        message={`Are you sure you want to delete "${deleteConfirm.recipe?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        confirmVariant="danger"
      />
    </div>
  )
}
