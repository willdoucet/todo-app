import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'

const MEAL_CATEGORIES = [
  { value: 'BREAKFAST', label: 'Breakfast' },
  { value: 'LUNCH', label: 'Lunch' },
  { value: 'DINNER', label: 'Dinner' }
]

export default function AddMealModal({
  isOpen,
  onClose,
  onSave,
  date,
  category,
  recipes,
  preselectedRecipe
}) {
  const [selectedCategory, setSelectedCategory] = useState(category || 'DINNER')
  const [mealType, setMealType] = useState('recipe')
  const [selectedRecipeId, setSelectedRecipeId] = useState(null)
  const [customMealName, setCustomMealName] = useState('')
  const [notes, setNotes] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setSelectedCategory(category || 'DINNER')
      setMealType(preselectedRecipe ? 'recipe' : 'recipe')
      setSelectedRecipeId(preselectedRecipe?.id || null)
      setCustomMealName('')
      setNotes('')
      setSearchQuery('')
    }
  }, [isOpen, category, preselectedRecipe])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const mealData = {
        date: date.toISOString().split('T')[0],
        category: selectedCategory,
        recipe_id: mealType === 'recipe' ? selectedRecipeId : null,
        custom_meal_name: mealType === 'custom' ? customMealName.trim() : null,
        notes: notes.trim() || null
      }

      await onSave(mealData)
    } finally {
      setLoading(false)
    }
  }

  const filteredRecipes = searchQuery
    ? recipes.filter(r => r.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : recipes

  const formatDate = () => {
    if (!date) return ''
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric'
    })
  }

  const isValid = mealType === 'recipe' ? selectedRecipeId : customMealName.trim()

  return (
    <Transition show={isOpen} as="div">
      <Dialog onClose={onClose} className="relative z-50">
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

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="w-full max-w-lg rounded-2xl bg-card-bg dark:bg-gray-800 shadow-2xl">
              <form onSubmit={handleSubmit}>
                {/* Header */}
                <div className="px-6 py-4 border-b border-card-border dark:border-gray-700">
                  <Dialog.Title className="text-xl font-semibold text-text-primary dark:text-gray-100">
                    Add Meal
                  </Dialog.Title>
                  <p className="text-sm text-text-secondary dark:text-gray-400 mt-1">
                    {formatDate()}
                  </p>
                </div>

                {/* Body */}
                <div className="px-6 py-4 space-y-5 max-h-[60vh] overflow-y-auto">
                  {/* Category Selection */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-2">
                      Meal Category
                    </label>
                    <div className="flex gap-2">
                      {MEAL_CATEGORIES.map(cat => (
                        <button
                          key={cat.value}
                          type="button"
                          onClick={() => setSelectedCategory(cat.value)}
                          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                            selectedCategory === cat.value
                              ? 'bg-terracotta-500 dark:bg-blue-600 text-white'
                              : 'bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-600'
                          }`}
                        >
                          {cat.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Meal Type Toggle */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-2">
                      Meal Type
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setMealType('recipe')}
                        className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          mealType === 'recipe'
                            ? 'bg-terracotta-100 dark:bg-blue-900/30 text-terracotta-600 dark:text-blue-400 border-2 border-terracotta-500 dark:border-blue-500'
                            : 'bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 border-2 border-transparent'
                        }`}
                      >
                        From Recipes
                      </button>
                      <button
                        type="button"
                        onClick={() => setMealType('custom')}
                        className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          mealType === 'custom'
                            ? 'bg-terracotta-100 dark:bg-blue-900/30 text-terracotta-600 dark:text-blue-400 border-2 border-terracotta-500 dark:border-blue-500'
                            : 'bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 border-2 border-transparent'
                        }`}
                      >
                        Custom Meal
                      </button>
                    </div>
                  </div>

                  {/* Recipe Selection */}
                  {mealType === 'recipe' && (
                    <div>
                      <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-2">
                        Select Recipe
                      </label>

                      {/* Search */}
                      <div className="relative mb-3">
                        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder="Search recipes..."
                          className="w-full pl-9 pr-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                        />
                      </div>

                      {/* Recipe List */}
                      <div className="max-h-48 overflow-y-auto border border-card-border dark:border-gray-600 rounded-xl">
                        {filteredRecipes.length > 0 ? (
                          filteredRecipes.map(recipe => (
                            <button
                              key={recipe.id}
                              type="button"
                              onClick={() => setSelectedRecipeId(recipe.id)}
                              className={`w-full flex items-center gap-3 p-3 text-left border-b border-card-border dark:border-gray-700 last:border-b-0 transition-colors ${
                                selectedRecipeId === recipe.id
                                  ? 'bg-terracotta-50 dark:bg-blue-900/20'
                                  : 'hover:bg-warm-beige dark:hover:bg-gray-700'
                              }`}
                            >
                              <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                                selectedRecipeId === recipe.id
                                  ? 'border-terracotta-500 dark:border-blue-500 bg-terracotta-500 dark:bg-blue-500'
                                  : 'border-card-border dark:border-gray-600'
                              }`}>
                                {selectedRecipeId === recipe.id && (
                                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                  </svg>
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-text-primary dark:text-gray-100 truncate">
                                  {recipe.name}
                                </p>
                                <p className="text-xs text-text-muted dark:text-gray-500">
                                  {recipe.cook_time_minutes ? `${recipe.cook_time_minutes} min` : 'No time set'}
                                  {recipe.is_favorite && ' · Favorite'}
                                </p>
                              </div>
                            </button>
                          ))
                        ) : (
                          <p className="p-4 text-center text-text-muted dark:text-gray-500 text-sm">
                            {searchQuery ? 'No recipes found' : 'No recipes available'}
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Custom Meal Name */}
                  {mealType === 'custom' && (
                    <div>
                      <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                        Meal Name
                      </label>
                      <input
                        type="text"
                        value={customMealName}
                        onChange={(e) => setCustomMealName(e.target.value)}
                        placeholder="e.g., Leftovers, Takeout, etc."
                        className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                      />
                    </div>
                  )}

                  {/* Notes */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Notes (optional)
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows={2}
                      placeholder="Any additional notes..."
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 resize-none"
                    />
                  </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-card-border dark:border-gray-700 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={loading}
                    className="px-4 py-2.5 text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-700 rounded-xl font-medium transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading || !isValid}
                    className="px-6 py-2.5 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Adding...' : 'Add Meal'}
                  </button>
                </div>
              </form>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  )
}
