import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'

const UNITS = ['cups', 'tbsp', 'tsp', 'oz', 'lb', 'g', 'kg', 'ml', 'L', 'pieces', 'cloves', 'slices', 'whole']
const INGREDIENT_CATEGORIES = ['Produce', 'Protein', 'Dairy', 'Pantry', 'Frozen', 'Bakery', 'Beverages', 'Other']

const emptyIngredient = { name: '', quantity: '', unit: '', category: 'Pantry' }

export default function RecipeFormModal({ isOpen, onClose, onSubmit, recipe }) {
  const isEditing = !!recipe

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    ingredients: [{ ...emptyIngredient }],
    instructions: '',
    prep_time_minutes: '',
    cook_time_minutes: '',
    servings: 4,
    image_url: '',
    is_favorite: false,
    tags: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (recipe) {
      setFormData({
        name: recipe.name || '',
        description: recipe.description || '',
        ingredients: recipe.ingredients?.length > 0
          ? recipe.ingredients
          : [{ ...emptyIngredient }],
        instructions: recipe.instructions || '',
        prep_time_minutes: recipe.prep_time_minutes || '',
        cook_time_minutes: recipe.cook_time_minutes || '',
        servings: recipe.servings || 4,
        image_url: recipe.image_url || '',
        is_favorite: recipe.is_favorite || false,
        tags: recipe.tags?.join(', ') || ''
      })
    } else {
      setFormData({
        name: '',
        description: '',
        ingredients: [{ ...emptyIngredient }],
        instructions: '',
        prep_time_minutes: '',
        cook_time_minutes: '',
        servings: 4,
        image_url: '',
        is_favorite: false,
        tags: ''
      })
    }
    setError(null)
  }, [recipe, isOpen])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleIngredientChange = (index, field, value) => {
    const newIngredients = [...formData.ingredients]
    newIngredients[index] = { ...newIngredients[index], [field]: value }
    setFormData(prev => ({ ...prev, ingredients: newIngredients }))
  }

  const addIngredient = () => {
    setFormData(prev => ({
      ...prev,
      ingredients: [...prev.ingredients, { ...emptyIngredient }]
    }))
  }

  const removeIngredient = (index) => {
    if (formData.ingredients.length <= 1) return
    setFormData(prev => ({
      ...prev,
      ingredients: prev.ingredients.filter((_, i) => i !== index)
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const submitData = {
        name: formData.name.trim(),
        description: formData.description.trim() || null,
        ingredients: formData.ingredients
          .filter(ing => ing.name.trim())
          .map(ing => ({
            name: ing.name.trim(),
            quantity: ing.quantity ? parseFloat(ing.quantity) : null,
            unit: ing.unit || null,
            category: ing.category || 'Other'
          })),
        instructions: formData.instructions.trim(),
        prep_time_minutes: formData.prep_time_minutes ? parseInt(formData.prep_time_minutes) : null,
        cook_time_minutes: formData.cook_time_minutes ? parseInt(formData.cook_time_minutes) : null,
        servings: parseInt(formData.servings) || 4,
        image_url: formData.image_url.trim() || null,
        is_favorite: formData.is_favorite,
        tags: formData.tags
          .split(',')
          .map(t => t.trim())
          .filter(t => t.length > 0)
      }

      await onSubmit(submitData)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save recipe')
    } finally {
      setLoading(false)
    }
  }

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

        <div className="fixed inset-0 flex items-start justify-center p-4 overflow-y-auto">
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="w-full max-w-2xl my-8 rounded-2xl bg-card-bg dark:bg-gray-800 shadow-2xl">
              <form onSubmit={handleSubmit}>
                {/* Header */}
                <div className="px-6 py-4 border-b border-card-border dark:border-gray-700">
                  <Dialog.Title className="text-xl font-semibold text-text-primary dark:text-gray-100">
                    {isEditing ? 'Edit Recipe' : 'Add New Recipe'}
                  </Dialog.Title>
                </div>

                {/* Body */}
                <div className="px-6 py-4 space-y-6 max-h-[60vh] overflow-y-auto">
                  {error && (
                    <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                      {error}
                    </div>
                  )}

                  {/* Name */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Recipe Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      required
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                      placeholder="e.g., Honey Garlic Chicken"
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Description
                    </label>
                    <textarea
                      name="description"
                      value={formData.description}
                      onChange={handleChange}
                      rows={2}
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 resize-none"
                      placeholder="A brief description of the dish..."
                    />
                  </div>

                  {/* Ingredients */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-2">
                      Ingredients
                    </label>
                    <div className="space-y-3">
                      {formData.ingredients.map((ingredient, index) => (
                        <div key={index} className="flex gap-2 items-start">
                          <div className="flex-1 grid grid-cols-12 gap-2">
                            <input
                              type="text"
                              value={ingredient.name}
                              onChange={(e) => handleIngredientChange(index, 'name', e.target.value)}
                              className="col-span-5 px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                              placeholder="Ingredient"
                            />
                            <input
                              type="number"
                              value={ingredient.quantity}
                              onChange={(e) => handleIngredientChange(index, 'quantity', e.target.value)}
                              className="col-span-2 px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                              placeholder="Qty"
                              step="0.1"
                              min="0"
                            />
                            <select
                              value={ingredient.unit}
                              onChange={(e) => handleIngredientChange(index, 'unit', e.target.value)}
                              className="col-span-2 px-2 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                            >
                              <option value="">Unit</option>
                              {UNITS.map(unit => (
                                <option key={unit} value={unit}>{unit}</option>
                              ))}
                            </select>
                            <select
                              value={ingredient.category}
                              onChange={(e) => handleIngredientChange(index, 'category', e.target.value)}
                              className="col-span-3 px-2 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                            >
                              {INGREDIENT_CATEGORIES.map(cat => (
                                <option key={cat} value={cat}>{cat}</option>
                              ))}
                            </select>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeIngredient(index)}
                            disabled={formData.ingredients.length <= 1}
                            className="p-2 text-text-muted dark:text-gray-500 hover:text-red-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                          >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={addIngredient}
                        className="w-full px-4 py-2 border-2 border-dashed border-card-border dark:border-gray-600 rounded-lg text-text-secondary dark:text-gray-400 hover:border-terracotta-500 dark:hover:border-blue-500 hover:text-terracotta-600 dark:hover:text-blue-400 transition-colors text-sm font-medium"
                      >
                        + Add Ingredient
                      </button>
                    </div>
                  </div>

                  {/* Instructions */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Instructions <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      name="instructions"
                      value={formData.instructions}
                      onChange={handleChange}
                      required
                      rows={5}
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 resize-none"
                      placeholder="Step-by-step cooking instructions..."
                    />
                  </div>

                  {/* Time and Servings */}
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                        Prep Time (min)
                      </label>
                      <input
                        type="number"
                        name="prep_time_minutes"
                        value={formData.prep_time_minutes}
                        onChange={handleChange}
                        min="0"
                        className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                        placeholder="15"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                        Cook Time (min)
                      </label>
                      <input
                        type="number"
                        name="cook_time_minutes"
                        value={formData.cook_time_minutes}
                        onChange={handleChange}
                        min="0"
                        className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                        placeholder="30"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                        Servings
                      </label>
                      <input
                        type="number"
                        name="servings"
                        value={formData.servings}
                        onChange={handleChange}
                        min="1"
                        className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                        placeholder="4"
                      />
                    </div>
                  </div>

                  {/* Image URL */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Image URL
                    </label>
                    <input
                      type="url"
                      name="image_url"
                      value={formData.image_url}
                      onChange={handleChange}
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                      placeholder="https://example.com/image.jpg"
                    />
                  </div>

                  {/* Tags */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">
                      Tags
                    </label>
                    <input
                      type="text"
                      name="tags"
                      value={formData.tags}
                      onChange={handleChange}
                      className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                      placeholder="quick, chicken, dinner (comma separated)"
                    />
                  </div>

                  {/* Favorite Toggle */}
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, is_favorite: !prev.is_favorite }))}
                      className={`relative w-12 h-7 rounded-full transition-colors ${
                        formData.is_favorite
                          ? 'bg-terracotta-500 dark:bg-blue-600'
                          : 'bg-warm-sand dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                          formData.is_favorite ? 'translate-x-5' : ''
                        }`}
                      />
                    </button>
                    <span className="text-sm text-text-primary dark:text-gray-200">
                      Mark as favorite
                    </span>
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
                    disabled={loading}
                    className="px-6 py-2.5 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50"
                  >
                    {loading ? 'Saving...' : isEditing ? 'Update Recipe' : 'Add Recipe'}
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
