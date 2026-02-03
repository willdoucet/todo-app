import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function MealPlannerRightPanel({ recipes, onAddRecipeToDay }) {
  const [linkedListId, setLinkedListId] = useState(() => {
    return localStorage.getItem('mealboard_shopping_list_id') || null
  })
  const [shoppingItems, setShoppingItems] = useState([])
  const [linkedList, setLinkedList] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    if (linkedListId) {
      fetchShoppingItems()
    }
  }, [linkedListId])

  const fetchShoppingItems = async () => {
    try {
      const [listRes, tasksRes] = await Promise.all([
        axios.get(`${API_BASE}/lists/${linkedListId}`),
        axios.get(`${API_BASE}/tasks?list_id=${linkedListId}`)
      ])
      setLinkedList(listRes.data)
      setShoppingItems(tasksRes.data.filter(t => !t.completed).slice(0, 8))
    } catch (err) {
      console.error('Error fetching shopping items:', err)
    }
  }

  const handleToggleItem = async (item) => {
    try {
      await axios.patch(`${API_BASE}/tasks/${item.id}`, {
        completed: !item.completed
      })
      setShoppingItems(shoppingItems.filter(i => i.id !== item.id))
    } catch (err) {
      console.error('Error toggling item:', err)
    }
  }

  const filteredRecipes = searchQuery
    ? recipes.filter(r => r.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : recipes

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Shopping List Section */}
      <div className="p-4 border-b border-card-border dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-text-primary dark:text-gray-100">Shopping List</h3>
          <Link
            to="/mealboard/shopping"
            className="text-sm text-terracotta-600 dark:text-blue-400 hover:underline"
          >
            View all
          </Link>
        </div>

        {linkedListId ? (
          shoppingItems.length > 0 ? (
            <div className="space-y-2">
              {shoppingItems.map(item => (
                <label
                  key={item.id}
                  className="flex items-center gap-2 cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={item.completed}
                    onChange={() => handleToggleItem(item)}
                    className="w-4 h-4 rounded border-card-border dark:border-gray-600 text-terracotta-500 dark:text-blue-500 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                  />
                  <span className="text-sm text-text-secondary dark:text-gray-300 group-hover:text-text-primary dark:group-hover:text-gray-100">
                    {item.title}
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted dark:text-gray-500">
              No items in your shopping list.
            </p>
          )
        ) : (
          <Link
            to="/mealboard/shopping"
            className="block text-sm text-text-secondary dark:text-gray-400 hover:text-terracotta-600 dark:hover:text-blue-400"
          >
            Link a shopping list to see items here
          </Link>
        )}
      </div>

      {/* Quick Add Section */}
      <div className="flex-1 flex flex-col min-h-0 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-text-primary dark:text-gray-100">Quick Add</h3>
          <Link
            to="/mealboard/recipes"
            className="text-sm text-terracotta-600 dark:text-blue-400 hover:underline"
          >
            Browse
          </Link>
        </div>

        {/* Recipe List */}
        <div className="flex-1 overflow-y-auto space-y-2">
          {filteredRecipes.length > 0 ? (
            filteredRecipes.map(recipe => (
              <button
                key={recipe.id}
                onClick={() => onAddRecipeToDay(recipe)}
                className="w-full flex items-center gap-3 p-2 rounded-xl bg-warm-sand/50 dark:bg-gray-700/50 hover:bg-warm-sand dark:hover:bg-gray-700 transition-colors text-left"
              >
                {/* Image */}
                <div className="w-12 h-12 rounded-lg bg-warm-beige dark:bg-gray-600 flex-shrink-0 overflow-hidden">
                  {recipe.image_url ? (
                    <img
                      src={recipe.image_url.startsWith('http') ? recipe.image_url : `${API_BASE}${recipe.image_url}`}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <svg className="w-6 h-6 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-text-primary dark:text-gray-100 truncate">
                    {recipe.name}
                  </p>
                  <p className="text-xs text-text-muted dark:text-gray-500">
                    {recipe.cook_time_minutes ? `${recipe.cook_time_minutes} min` : 'Quick'}
                    {recipe.is_favorite && ' · Favorite'}
                  </p>
                </div>
              </button>
            ))
          ) : (
            <p className="text-sm text-text-muted dark:text-gray-500 text-center py-4">
              {searchQuery ? 'No recipes found' : 'No favorite recipes yet'}
            </p>
          )}
        </div>

        {/* Search */}
        <div className="mt-3 pt-3 border-t border-card-border dark:border-gray-700">
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Find a recipe"
              className="w-full pl-9 pr-4 py-2 bg-warm-sand dark:bg-gray-700 border border-transparent rounded-lg text-sm text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
