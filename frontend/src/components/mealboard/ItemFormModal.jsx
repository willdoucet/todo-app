import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import UnitCombobox from './UnitCombobox'
import RecipeImageUpload from './RecipeImageUpload'
import FoodEmojiPicker from '../shared/FoodEmojiPicker'
import { suggestEmoji } from '../../constants/foodEmojis'

const INGREDIENT_CATEGORIES = ['Produce', 'Protein', 'Dairy', 'Pantry', 'Frozen', 'Bakery', 'Beverages', 'Other']
const FOOD_CATEGORIES = [
  { value: 'Other', label: 'No category' },
  { value: 'fruit', label: 'Fruit' },
  { value: 'vegetable', label: 'Vegetable' },
  { value: 'protein', label: 'Protein' },
  { value: 'dairy', label: 'Dairy' },
  { value: 'grain', label: 'Grain' },
]

const emptyIngredient = { name: '', quantity: '', unit: '', category: 'Pantry' }

/**
 * Unified form modal for the Item model. Replaces RecipeFormModal + FoodItemFormModal.
 *
 * The `type` prop is LOCKED at open time (plan §0.4 IA issue 1A). The modal renders
 * entirely different field sets for each type:
 *   - recipe: full form (name, description, ingredients, instructions, times, image, tags, favorite)
 *   - food_item: compact form (name, icon XOR with emoji/custom image tabs, category, favorite)
 *     — implements mockup `emoji-icon-xor-option-d.html` for the icon section
 *
 * Submits to the unified `/items` POST/PATCH API with the nested detail schema.
 */
export default function ItemFormModal({ isOpen, onClose, onSubmit, type, initialItem }) {
  const isEditing = !!initialItem
  // Defensive invariant: if the parent re-opens the modal with a different type,
  // the form state must reset. The useEffect below handles this by keying on `type`.
  const effectiveType = initialItem?.item_type || type || 'recipe'

  if (effectiveType === 'recipe') {
    return (
      <RecipeFormBody
        isOpen={isOpen}
        onClose={onClose}
        onSubmit={onSubmit}
        initialItem={initialItem}
        isEditing={isEditing}
      />
    )
  }
  return (
    <FoodItemFormBody
      isOpen={isOpen}
      onClose={onClose}
      onSubmit={onSubmit}
      initialItem={initialItem}
      isEditing={isEditing}
    />
  )
}

// ---------------------------------------------------------------------------
// Shared modal chrome
// ---------------------------------------------------------------------------

function ModalShell({ isOpen, onClose, maxWidth = 'max-w-md', startAligned = false, children }) {
  return (
    <Transition show={isOpen} as="div" appear>
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
        <div className={`fixed inset-0 flex ${startAligned ? 'items-start' : 'items-center'} justify-center p-4 overflow-y-auto`}>
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className={`w-full ${maxWidth} ${startAligned ? 'my-8' : ''} rounded-2xl bg-card-bg dark:bg-gray-800 shadow-2xl`}>
              {children}
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  )
}

// ---------------------------------------------------------------------------
// Recipe form body
// ---------------------------------------------------------------------------

function RecipeFormBody({ isOpen, onClose, onSubmit, initialItem, isEditing }) {
  const [formData, setFormData] = useState(initialRecipeState())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!isOpen) return
    if (initialItem) {
      const rd = initialItem.recipe_detail || {}
      // Normalize null → '' on every ingredient field so controlled inputs don't
      // warn about `value={null}`. The backend returns `quantity: null` for pantry
      // staples and `unit: null` for items with no unit — both would otherwise flow
      // straight into an input's value prop.
      const normalizedIngredients = rd.ingredients?.length > 0
        ? rd.ingredients.map((ing) => ({
            name: ing.name ?? '',
            quantity: ing.quantity ?? '',
            unit: ing.unit ?? '',
            category: ing.category ?? 'Pantry',
          }))
        : [{ ...emptyIngredient }]
      setFormData({
        name: initialItem.name || '',
        description: rd.description || '',
        ingredients: normalizedIngredients,
        instructions: rd.instructions || '',
        prep_time_minutes: rd.prep_time_minutes ?? '',
        cook_time_minutes: rd.cook_time_minutes ?? '',
        servings: rd.servings ?? 4,
        image_url: rd.image_url || '',
        is_favorite: initialItem.is_favorite || false,
        tags: (initialItem.tags || []).join(', '),
      })
    } else {
      setFormData(initialRecipeState())
    }
    setError(null)
  }, [initialItem, isOpen])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleIngredientChange = (index, field, value) => {
    const next = [...formData.ingredients]
    next[index] = { ...next[index], [field]: value }
    if (field === 'unit' && !value) next[index].quantity = ''
    setFormData((prev) => ({ ...prev, ingredients: next }))
  }

  const addIngredient = () =>
    setFormData((prev) => ({ ...prev, ingredients: [...prev.ingredients, { ...emptyIngredient }] }))

  const removeIngredient = (index) => {
    if (formData.ingredients.length <= 1) return
    setFormData((prev) => ({ ...prev, ingredients: prev.ingredients.filter((_, i) => i !== index) }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const payload = {
        name: formData.name.trim(),
        item_type: 'recipe',
        icon_emoji: null,
        icon_url: formData.image_url.trim() || null,
        tags: formData.tags.split(',').map((t) => t.trim()).filter(Boolean),
        is_favorite: formData.is_favorite,
        recipe_detail: {
          description: formData.description.trim() || null,
          ingredients: formData.ingredients
            .filter((ing) => ing.name.trim())
            .map((ing) => ({
              name: ing.name.trim(),
              quantity: ing.quantity ? parseFloat(ing.quantity) : null,
              unit: ing.unit || null,
              category: ing.category || 'Other',
            })),
          instructions: formData.instructions.trim() || null,
          prep_time_minutes: formData.prep_time_minutes ? parseInt(formData.prep_time_minutes) : null,
          cook_time_minutes: formData.cook_time_minutes ? parseInt(formData.cook_time_minutes) : null,
          servings: parseInt(formData.servings) || 4,
          image_url: formData.image_url.trim() || null,
        },
      }
      await onSubmit(payload)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to save recipe')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ModalShell isOpen={isOpen} onClose={onClose} maxWidth="max-w-2xl" startAligned>
      <form onSubmit={handleSubmit}>
        <div className="px-6 py-4 border-b border-card-border dark:border-gray-700">
          {isEditing && (
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted dark:text-gray-400 mb-0.5">
              Recipe
            </p>
          )}
          <Dialog.Title className="text-xl font-semibold text-text-primary dark:text-gray-100">
            {isEditing ? 'Edit Recipe' : 'New Recipe'}
          </Dialog.Title>
        </div>

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
              type="text" name="name" value={formData.name} onChange={handleChange} required
              className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
              placeholder="e.g., Honey Garlic Chicken"
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">Description</label>
            <textarea
              name="description" value={formData.description} onChange={handleChange} rows={2}
              className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 resize-none"
              placeholder="A brief description of the dish..."
            />
          </div>

          {/* Ingredients */}
          <div>
            <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-2">Ingredients</label>
            <div className="space-y-3">
              {formData.ingredients.map((ingredient, index) => (
                <div key={index} className="flex gap-2 items-start">
                  <div className="flex-1 grid grid-cols-12 gap-2">
                    <input
                      type="text" value={ingredient.name}
                      onChange={(e) => handleIngredientChange(index, 'name', e.target.value)}
                      className="col-span-5 px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                      placeholder="Ingredient"
                    />
                    <input
                      type="number" value={ingredient.quantity}
                      onChange={(e) => handleIngredientChange(index, 'quantity', e.target.value)}
                      disabled={!ingredient.unit}
                      className="col-span-2 px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 disabled:bg-warm-beige disabled:text-text-muted dark:disabled:bg-gray-800 dark:disabled:text-gray-500 disabled:cursor-not-allowed"
                      placeholder={ingredient.unit ? 'Qty' : '—'}
                      step="any" min="0"
                    />
                    <div className="col-span-2">
                      <UnitCombobox
                        value={ingredient.unit || null}
                        onChange={(unit) => handleIngredientChange(index, 'unit', unit || '')}
                      />
                    </div>
                    <select
                      value={ingredient.category}
                      onChange={(e) => handleIngredientChange(index, 'category', e.target.value)}
                      className="col-span-3 px-2 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                    >
                      {INGREDIENT_CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button" onClick={() => removeIngredient(index)}
                    disabled={formData.ingredients.length <= 1}
                    className="p-2 text-text-muted dark:text-gray-500 hover:text-red-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    aria-label="Remove ingredient"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
              <button
                type="button" onClick={addIngredient}
                className="w-full px-4 py-2 border-2 border-dashed border-card-border dark:border-gray-600 rounded-lg text-text-secondary dark:text-gray-400 hover:border-terracotta-500 dark:hover:border-blue-500 hover:text-terracotta-600 dark:hover:text-blue-400 transition-colors text-sm font-medium"
              >
                + Add Ingredient
              </button>
            </div>
          </div>

          {/* Instructions */}
          <div>
            <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">Instructions</label>
            <textarea
              name="instructions" value={formData.instructions} onChange={handleChange} rows={5}
              className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500 resize-none"
              placeholder="Step-by-step cooking instructions..."
            />
          </div>

          {/* Time + Servings */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { key: 'prep_time_minutes', label: 'Prep Time (min)', placeholder: '15' },
              { key: 'cook_time_minutes', label: 'Cook Time (min)', placeholder: '30' },
              { key: 'servings', label: 'Servings', placeholder: '4', min: 1 },
            ].map((f) => (
              <div key={f.key}>
                <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">{f.label}</label>
                <input
                  type="number" name={f.key} value={formData[f.key]} onChange={handleChange}
                  min={f.min ?? 0}
                  className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
                  placeholder={f.placeholder}
                />
              </div>
            ))}
          </div>

          {/* Image Upload */}
          <div>
            <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">Image</label>
            <RecipeImageUpload
              imageUrl={formData.image_url}
              onImageChange={(url) => setFormData((prev) => ({ ...prev, image_url: url || '' }))}
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-text-primary dark:text-gray-200 mb-1.5">Tags</label>
            <input
              type="text" name="tags" value={formData.tags} onChange={handleChange}
              className="w-full px-4 py-2.5 border border-card-border dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
              placeholder="quick, chicken, dinner (comma separated)"
            />
          </div>

          {/* Favorite */}
          <FavoriteToggle
            value={formData.is_favorite}
            onChange={(v) => setFormData((prev) => ({ ...prev, is_favorite: v }))}
          />
        </div>

        <ModalFooter onClose={onClose} loading={loading} isEditing={isEditing} createLabel="Add Recipe" updateLabel="Update Recipe" />
      </form>
    </ModalShell>
  )
}

function initialRecipeState() {
  return {
    name: '',
    description: '',
    ingredients: [{ ...emptyIngredient }],
    instructions: '',
    prep_time_minutes: '',
    cook_time_minutes: '',
    servings: 4,
    image_url: '',
    is_favorite: false,
    tags: '',
  }
}

// ---------------------------------------------------------------------------
// Food item form body — compact modal with icon XOR (mockup emoji-icon-xor-d)
// ---------------------------------------------------------------------------

const ICON_MODE_EMOJI = 'emoji'
const ICON_MODE_URL = 'url'

function FoodItemFormBody({ isOpen, onClose, onSubmit, initialItem, isEditing }) {
  const [name, setName] = useState('')
  const [iconMode, setIconMode] = useState(ICON_MODE_EMOJI)
  const [iconEmoji, setIconEmoji] = useState('')
  const [iconUrl, setIconUrl] = useState('')
  const [category, setCategory] = useState('Other')
  const [isFavorite, setIsFavorite] = useState(false)
  const [emojiManuallySet, setEmojiManuallySet] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!isOpen) return
    setName(initialItem?.name || '')
    const hasUrl = !!initialItem?.icon_url
    setIconMode(hasUrl ? ICON_MODE_URL : ICON_MODE_EMOJI)
    setIconEmoji(initialItem?.icon_emoji || '')
    setIconUrl(initialItem?.icon_url || '')
    setCategory(initialItem?.food_item_detail?.category || 'Other')
    setIsFavorite(initialItem?.is_favorite || false)
    setEmojiManuallySet(!!initialItem?.icon_emoji)
    setError(null)
  }, [isOpen, initialItem])

  // Auto-suggest emoji as user types the name (only if not manually set and no URL)
  useEffect(() => {
    if (iconMode !== ICON_MODE_EMOJI) return
    if (emojiManuallySet || !name) return
    const suggested = suggestEmoji(name)
    if (suggested) setIconEmoji(suggested)
  }, [name, emojiManuallySet, iconMode])

  const handlePickEmoji = (picked) => {
    setIconEmoji(picked || '')
    setEmojiManuallySet(true)
    // Selecting an emoji switches the mode and clears the URL (XOR)
    setIconMode(ICON_MODE_EMOJI)
    setIconUrl('')
  }

  const switchMode = (mode) => {
    if (mode === iconMode) return
    setIconMode(mode)
    // Per plan §0.4F: switching mode is intentional; clear the wrong-mode field
    if (mode === ICON_MODE_EMOJI) {
      setIconUrl('')
    } else {
      setIconEmoji('')
      setEmojiManuallySet(true) // prevent auto-suggest from re-populating
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setIsSubmitting(true)
    setError(null)
    try {
      const payload = {
        name: name.trim(),
        item_type: 'food_item',
        icon_emoji: iconMode === ICON_MODE_EMOJI ? (iconEmoji || null) : null,
        icon_url: iconMode === ICON_MODE_URL ? (iconUrl.trim() || null) : null,
        tags: [],
        is_favorite: isFavorite,
        food_item_detail: {
          category: category || 'Other',
          shopping_quantity: initialItem?.food_item_detail?.shopping_quantity ?? 1.0,
          shopping_unit: initialItem?.food_item_detail?.shopping_unit || 'each',
        },
      }
      await onSubmit(payload)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to save food item')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <ModalShell isOpen={isOpen} onClose={onClose} maxWidth="max-w-md">
      <div className="p-6">
        <div className="flex justify-between items-center mb-5">
          <div>
            {isEditing && (
              <p className="text-xs font-medium uppercase tracking-wide text-text-muted dark:text-gray-400 mb-0.5">
                Food item
              </p>
            )}
            <Dialog.Title className="text-lg font-semibold text-text-primary dark:text-gray-100">
              {isEditing ? 'Edit Food Item' : 'New Food Item'}
            </Dialog.Title>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted dark:text-gray-500 hover:text-text-secondary dark:hover:text-gray-300 p-1 rounded-lg hover:bg-warm-beige dark:hover:bg-gray-700"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg text-sm bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-xs font-medium text-text-secondary dark:text-gray-300 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Banana, Yogurt, Crackers"
              autoFocus
              required
              className="w-full px-3 py-2 text-sm rounded-lg border border-card-border dark:border-gray-600 bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 placeholder-text-muted dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
            />
          </div>

          {/* Icon XOR — implements mockup emoji-icon-xor-option-d.html */}
          <div>
            <label className="block text-xs font-medium text-text-secondary dark:text-gray-300 mb-1">Icon</label>
            <div className="flex items-center gap-2">
              {/* Icon square — 64×64, click opens picker (emoji mode) or file browser (url mode) */}
              <IconSquare
                mode={iconMode}
                iconEmoji={iconEmoji}
                iconUrl={iconUrl}
                onPickEmoji={handlePickEmoji}
              />

              {/* Tab switcher — compact 32px tall */}
              <div
                className="flex bg-warm-sand dark:bg-gray-700 rounded-lg p-0.5 gap-0.5 h-8 flex-1 min-w-0"
                role="tablist"
                aria-label="Icon source"
              >
                <TabButton
                  active={iconMode === ICON_MODE_EMOJI}
                  onClick={() => switchMode(ICON_MODE_EMOJI)}
                >
                  <span className="text-xs leading-none">😀</span>
                  Emoji
                </TabButton>
                <TabButton
                  active={iconMode === ICON_MODE_URL}
                  onClick={() => switchMode(ICON_MODE_URL)}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  Custom
                </TabButton>
              </div>
            </div>

            {/* URL input row (only in custom image mode) */}
            {iconMode === ICON_MODE_URL && (
              <div className="mt-2 pl-[4.5rem]">
                <div className="relative">
                  <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-text-muted pointer-events-none" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  <input
                    type="url"
                    value={iconUrl}
                    onChange={(e) => setIconUrl(e.target.value)}
                    placeholder="…or paste an image URL"
                    className="w-full pl-7 pr-2.5 py-1.5 text-xs rounded-md border border-card-border dark:border-gray-600 bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500"
                  />
                </div>
              </div>
            )}

            <p className="text-[0.6875rem] text-text-muted dark:text-gray-500 mt-1.5 pl-[4.5rem]">
              {iconMode === ICON_MODE_EMOJI
                ? 'Click the square to open the emoji picker.'
                : 'Paste an image URL above, or click the square to upload a file.'}
            </p>
          </div>

          {/* Category */}
          <div>
            <label className="block text-xs font-medium text-text-secondary dark:text-gray-300 mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full h-[42px] px-3 text-sm rounded-lg border border-card-border dark:border-gray-600 bg-white dark:bg-gray-700 text-text-primary dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
            >
              {FOOD_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </select>
          </div>

          {/* Favorite */}
          <FavoriteToggle value={isFavorite} onChange={setIsFavorite} compact />

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className="flex-1 px-4 py-2 text-sm font-medium rounded-lg bg-terracotta-500 dark:bg-blue-600 hover:bg-terracotta-600 dark:hover:bg-blue-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium rounded-lg text-text-secondary dark:text-gray-300 hover:bg-warm-beige dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </ModalShell>
  )
}

// ---------------------------------------------------------------------------
// Shared sub-components
// ---------------------------------------------------------------------------

function IconSquare({ mode, iconEmoji, iconUrl, onPickEmoji }) {
  // onPickFile reserved for future file-picker wiring — URL paste handles the write path today
  const dimensions = 'w-16 h-16'  // 64×64 per mockup
  const commonCls = 'rounded-[0.625rem] flex items-center justify-center flex-shrink-0 transition-colors'

  if (mode === ICON_MODE_EMOJI) {
    return (
      <FoodEmojiPicker selected={iconEmoji} onSelect={onPickEmoji}>
        <button
          type="button"
          className={`${dimensions} ${commonCls} bg-white dark:bg-gray-700 border border-card-border dark:border-gray-600 hover:border-terracotta-500 dark:hover:border-blue-500`}
          aria-label="Change emoji"
        >
          {iconEmoji ? (
            <span style={{ fontSize: '2.25rem', lineHeight: 1 }}>{iconEmoji}</span>
          ) : (
            <span className="text-[0.6875rem] text-text-muted">Pick</span>
          )}
        </button>
      </FoodEmojiPicker>
    )
  }

  // URL mode — show preview if set, otherwise show upload affordance.
  // File-picker integration is deferred to a follow-up — clicking here for now
  // is a visual affordance; the URL input field below the tabs is the real input.
  if (iconUrl) {
    return (
      <div className={`${dimensions} ${commonCls} bg-warm-sand dark:bg-gray-700 border border-card-border dark:border-gray-600 overflow-hidden`}>
        <img src={iconUrl} alt="" className="w-full h-full object-cover" />
      </div>
    )
  }
  return (
    <div
      className={`${dimensions} ${commonCls} border border-dashed border-card-border dark:border-gray-600 bg-warm-sand/35 dark:bg-gray-700/30 hover:bg-terracotta-50 dark:hover:bg-gray-700 text-text-muted dark:text-gray-500`}
      aria-hidden="true"
    >
      <div className="flex flex-col items-center gap-0.5">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span className="text-[0.625rem] leading-none">Upload</span>
      </div>
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`
        flex-1 flex items-center justify-center gap-1 px-2
        text-[0.6875rem] font-medium rounded-md whitespace-nowrap min-w-0
        transition-colors
        ${active
          ? 'bg-card-bg dark:bg-gray-800 text-text-primary dark:text-gray-100 shadow-sm'
          : 'text-text-secondary dark:text-gray-400 hover:text-text-primary dark:hover:text-gray-200'}
      `}
    >
      {children}
    </button>
  )
}

function FavoriteToggle({ value, onChange, compact = false }) {
  return (
    <div className={`flex items-center gap-3 ${compact ? '' : ''}`}>
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={`relative w-12 h-7 rounded-full transition-colors ${
          value ? 'bg-terracotta-500 dark:bg-blue-600' : 'bg-warm-sand dark:bg-gray-600'
        }`}
        aria-pressed={value}
        aria-label="Mark as favorite"
      >
        <span
          className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${value ? 'translate-x-5' : ''}`}
        />
      </button>
      <span className="text-sm text-text-primary dark:text-gray-200">Mark as favorite</span>
    </div>
  )
}

function ModalFooter({ onClose, loading, isEditing, createLabel, updateLabel }) {
  return (
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
        {loading ? 'Saving...' : isEditing ? updateLabel : createLabel}
      </button>
    </div>
  )
}
