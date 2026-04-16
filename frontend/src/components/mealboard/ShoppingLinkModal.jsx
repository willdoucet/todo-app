import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * 2-step modal for linking a shopping list to the mealboard.
 * Step 1: select existing list OR create new list (in-modal) OR import from iCloud
 * Step 2: success confirmation with checkmark
 */
export default function ShoppingLinkModal({ isOpen, onClose, onLinked }) {
  const [step, setStep] = useState(1)
  const [lists, setLists] = useState([])
  const [selectedListId, setSelectedListId] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newListName, setNewListName] = useState('')
  const [linkedList, setLinkedList] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (isOpen) {
      setStep(1)
      setSelectedListId(null)
      setSearchQuery('')
      setCreating(false)
      setNewListName('')
      setLinkedList(null)
      setError(null)
      fetchLists()
    }
  }, [isOpen])

  const fetchLists = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API_BASE}/lists`)
      setLists(res.data)
    } catch {
      setError('Failed to load lists')
    } finally {
      setLoading(false)
    }
  }

  const handleLinkList = async (listId) => {
    try {
      const [settingsRes, listRes] = await Promise.all([
        axios.patch(`${API_BASE}/app-settings/`, { mealboard_shopping_list_id: listId }),
        axios.get(`${API_BASE}/lists/${listId}`),
      ])
      setLinkedList(listRes.data)
      setStep(2)
      // Notify parent after success animation
      setTimeout(() => onLinked(settingsRes.data), 1200)
    } catch {
      setError('Failed to link list')
    }
  }

  const handleCreateAndLink = async (e) => {
    e.preventDefault()
    if (!newListName.trim()) return
    try {
      const listRes = await axios.post(`${API_BASE}/lists`, {
        name: newListName.trim(),
        color: '#5E9E6B', // Sage default for shopping lists
        icon: 'shopping-cart',
      })
      await handleLinkList(listRes.data.id)
    } catch {
      setError('Failed to create list')
    }
  }

  const filteredLists = lists.filter((l) =>
    l.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

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
          <div className="fixed inset-0 bg-black/40 dark:bg-black/60" />
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
            <Dialog.Panel className="w-full max-w-md rounded-2xl bg-card-bg dark:bg-gray-800 shadow-2xl">
              {/* Step indicator + close */}
              <div className="flex items-center justify-between p-5 border-b border-card-border dark:border-gray-700">
                <div className="flex gap-1.5">
                  <div
                    className={`h-1.5 w-8 rounded-full ${
                      step >= 1 ? 'bg-terracotta-500 dark:bg-blue-500' : 'bg-card-border dark:bg-gray-700'
                    }`}
                  />
                  <div
                    className={`h-1.5 w-8 rounded-full ${
                      step >= 2 ? 'bg-terracotta-500 dark:bg-blue-500' : 'bg-card-border dark:bg-gray-700'
                    }`}
                  />
                </div>
                <button
                  onClick={onClose}
                  className="text-text-muted dark:text-gray-500 hover:text-text-secondary dark:hover:text-gray-300 p-1 rounded hover:bg-warm-beige dark:hover:bg-gray-700"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>

              {/* Step content */}
              <div className="p-5">
                {step === 1 && (
                  <>
                    <Dialog.Title className="text-lg font-bold text-text-primary dark:text-gray-100 mb-1">
                      Link a shopping list
                    </Dialog.Title>
                    <p className="text-sm text-text-muted dark:text-gray-400 mb-4">
                      Meal ingredients will auto-sync to this list.
                    </p>

                    {error && (
                      <div className="mb-3 p-2.5 rounded-lg text-sm bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300">
                        {error}
                      </div>
                    )}

                    {creating ? (
                      <form onSubmit={handleCreateAndLink} className="space-y-3">
                        <input
                          type="text"
                          value={newListName}
                          onChange={(e) => setNewListName(e.target.value)}
                          placeholder="e.g. Shopping, Groceries"
                          autoFocus
                          className="
                            w-full px-3 py-2 text-sm rounded-lg
                            border border-card-border dark:border-gray-600
                            bg-white dark:bg-gray-700
                            text-text-primary dark:text-gray-100
                            focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
                          "
                        />
                        <div className="flex gap-2">
                          <button
                            type="submit"
                            disabled={!newListName.trim()}
                            className="
                              flex-1 px-4 py-2 text-sm font-medium rounded-lg
                              bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700
                              text-white transition-colors disabled:opacity-50
                            "
                          >
                            Create &amp; Link
                          </button>
                          <button
                            type="button"
                            onClick={() => setCreating(false)}
                            className="
                              px-4 py-2 text-sm font-medium rounded-lg
                              text-text-secondary dark:text-gray-300
                              hover:bg-warm-beige dark:hover:bg-gray-700
                            "
                          >
                            Back
                          </button>
                        </div>
                      </form>
                    ) : (
                      <>
                        {loading ? (
                          <div className="py-6 text-center text-sm text-text-muted">Loading lists...</div>
                        ) : lists.length === 0 ? (
                          // Empty state (no lists exist)
                          <div className="py-4 text-center">
                            <p className="text-sm text-text-secondary dark:text-gray-300 mb-4">
                              You don't have any lists yet.
                            </p>
                            <button
                              type="button"
                              onClick={() => setCreating(true)}
                              className="
                                inline-block px-4 py-2 text-sm font-medium rounded-lg
                                bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700
                                text-white transition-colors
                              "
                            >
                              Create your first list
                            </button>
                          </div>
                        ) : (
                          <>
                            {/* Search bar */}
                            {lists.length > 3 && (
                              <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search lists..."
                                className="
                                  w-full mb-2 px-3 py-2 text-sm rounded-lg
                                  border border-card-border dark:border-gray-600
                                  bg-white dark:bg-gray-700
                                  text-text-primary dark:text-gray-100
                                  focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
                                "
                              />
                            )}

                            {/* List selection */}
                            <div className="space-y-1 mb-3 max-h-60 overflow-y-auto">
                              {filteredLists.map((list) => (
                                <button
                                  key={list.id}
                                  type="button"
                                  onClick={() => setSelectedListId(list.id)}
                                  className={`
                                    w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left
                                    border-2 transition-colors
                                    ${
                                      selectedListId === list.id
                                        ? 'border-terracotta-500 bg-terracotta-50 dark:border-blue-500 dark:bg-blue-900/20'
                                        : 'border-transparent hover:bg-warm-beige dark:hover:bg-gray-700'
                                    }
                                  `}
                                >
                                  <span
                                    className="w-3 h-3 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: list.color || '#9CA3AF' }}
                                  />
                                  <span className="flex-1 text-sm font-medium text-text-primary dark:text-gray-100">
                                    {list.name}
                                  </span>
                                  {selectedListId === list.id && (
                                    <span className="text-terracotta-500 dark:text-blue-400">✓</span>
                                  )}
                                </button>
                              ))}
                            </div>

                            {/* Create new list option */}
                            <button
                              type="button"
                              onClick={() => setCreating(true)}
                              className="
                                w-full px-3 py-2 text-sm text-text-muted dark:text-gray-400
                                hover:text-terracotta-500 dark:hover:text-blue-400
                                border border-dashed border-card-border dark:border-gray-600
                                hover:border-terracotta-500 dark:hover:border-blue-500
                                rounded-lg transition-colors
                              "
                            >
                              + Create new list
                            </button>
                          </>
                        )}
                      </>
                    )}
                  </>
                )}

                {step === 2 && linkedList && (
                  <div className="text-center py-6">
                    <div
                      className="
                        w-16 h-16 mx-auto mb-4 rounded-full
                        bg-gradient-to-br from-sage-500 to-sage-600
                        dark:from-green-500 dark:to-green-600
                        flex items-center justify-center
                      "
                      style={{ animation: 'bounce-in 0.5s ease-out both' }}
                    >
                      <svg className="w-9 h-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-bold text-text-primary dark:text-gray-100 mb-2">
                      Shopping list linked!
                    </h3>
                    <div
                      className="
                        inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                        bg-warm-beige dark:bg-gray-700
                        text-sm font-medium text-text-primary dark:text-gray-100
                      "
                    >
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: linkedList.color || '#9CA3AF' }}
                      />
                      {linkedList.name}
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              {step === 1 && !creating && selectedListId && (
                <div className="flex gap-2 p-4 border-t border-card-border dark:border-gray-700">
                  <button
                    onClick={onClose}
                    className="
                      px-4 py-2 text-sm font-medium rounded-lg
                      text-text-secondary dark:text-gray-300
                      hover:bg-warm-beige dark:hover:bg-gray-700
                    "
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleLinkList(selectedListId)}
                    className="
                      flex-1 px-4 py-2 text-sm font-medium rounded-lg
                      bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700
                      text-white transition-colors
                    "
                  >
                    Link List
                  </button>
                </div>
              )}
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  )
}
