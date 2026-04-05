import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import FoodEmojiPicker from '../shared/FoodEmojiPicker'
import { suggestEmoji } from '../../constants/foodEmojis'

const CATEGORIES = [
  { value: '', label: 'No category' },
  { value: 'fruit', label: 'Fruit' },
  { value: 'vegetable', label: 'Vegetable' },
  { value: 'protein', label: 'Protein' },
  { value: 'dairy', label: 'Dairy' },
  { value: 'grain', label: 'Grain' },
]

export default function FoodItemFormModal({ isOpen, onClose, onSubmit, initialItem }) {
  const [name, setName] = useState('')
  const [emoji, setEmoji] = useState('')
  const [category, setCategory] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)
  // Track whether user has manually set the emoji (prevents auto-suggest from overriding)
  const [emojiManuallySet, setEmojiManuallySet] = useState(false)

  // Reset form when modal opens/closes or initialItem changes
  useEffect(() => {
    if (isOpen) {
      setName(initialItem?.name || '')
      setEmoji(initialItem?.emoji || '')
      setCategory(initialItem?.category || '')
      setEmojiManuallySet(!!initialItem?.emoji)
      setError(null)
    }
  }, [isOpen, initialItem])

  // Auto-suggest emoji as user types name (only if they haven't manually set one)
  useEffect(() => {
    if (!emojiManuallySet && name) {
      const suggested = suggestEmoji(name)
      if (suggested) setEmoji(suggested)
    }
  }, [name, emojiManuallySet])

  const handlePickEmoji = (pickedEmoji) => {
    setEmoji(pickedEmoji || '')
    setEmojiManuallySet(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setIsSubmitting(true)
    setError(null)
    try {
      await onSubmit({
        name: name.trim(),
        emoji: emoji || null,
        category: category || null,
      })
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to save food item')
    } finally {
      setIsSubmitting(false)
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

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="
              w-full max-w-md rounded-2xl
              bg-card-bg dark:bg-gray-800 p-6 shadow-2xl
            ">
              <div className="flex justify-between items-center mb-5">
                <Dialog.Title className="text-lg font-semibold text-text-primary dark:text-gray-100">
                  {initialItem ? 'Edit Food Item' : 'New Food Item'}
                </Dialog.Title>
                <button
                  onClick={onClose}
                  className="text-text-muted dark:text-gray-500 hover:text-text-secondary dark:hover:text-gray-300 p-1 rounded-lg hover:bg-warm-beige dark:hover:bg-gray-700"
                >
                  <XMarkIcon className="h-5 w-5" />
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
                  <label className="block text-xs font-medium text-text-secondary dark:text-gray-300 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Banana, Yogurt, Crackers"
                    autoFocus
                    required
                    className="
                      w-full px-3 py-2 text-sm rounded-lg
                      border border-card-border dark:border-gray-600
                      bg-white dark:bg-gray-700
                      text-text-primary dark:text-gray-100
                      placeholder-text-muted dark:placeholder-gray-500
                      focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
                    "
                  />
                </div>

                {/* Emoji + Category row */}
                <div className="grid grid-cols-[auto_1fr] gap-3">
                  <div>
                    <label className="block text-xs font-medium text-text-secondary dark:text-gray-300 mb-1">
                      Emoji
                    </label>
                    <FoodEmojiPicker selected={emoji} onSelect={handlePickEmoji}>
                      <button
                        type="button"
                        className="
                          w-14 h-[42px] flex items-center justify-center
                          text-2xl rounded-lg border border-card-border dark:border-gray-600
                          bg-white dark:bg-gray-700
                          hover:border-terracotta-500 dark:hover:border-blue-500 transition-colors
                        "
                      >
                        {emoji || <span className="text-xs text-text-muted">Pick</span>}
                      </button>
                    </FoodEmojiPicker>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-text-secondary dark:text-gray-300 mb-1">
                      Category
                    </label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="
                        w-full h-[42px] px-3 text-sm rounded-lg
                        border border-card-border dark:border-gray-600
                        bg-white dark:bg-gray-700
                        text-text-primary dark:text-gray-100
                        focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
                      "
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={isSubmitting || !name.trim()}
                    className="
                      flex-1 px-4 py-2 text-sm font-medium rounded-lg
                      bg-terracotta-500 dark:bg-blue-600
                      hover:bg-terracotta-600 dark:hover:bg-blue-700
                      text-white transition-colors
                      disabled:opacity-50 disabled:cursor-not-allowed
                    "
                  >
                    {isSubmitting ? 'Saving...' : initialItem ? 'Save Changes' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={onClose}
                    className="
                      px-4 py-2 text-sm font-medium rounded-lg
                      text-text-secondary dark:text-gray-300
                      hover:bg-warm-beige dark:hover:bg-gray-700
                      transition-colors
                    "
                  >
                    Cancel
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
