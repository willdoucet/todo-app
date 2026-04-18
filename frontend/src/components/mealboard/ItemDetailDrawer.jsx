import { useState, useEffect, useCallback, useRef } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Side drawer for reading item details. Replaces RecipeDetailDrawer after the
 * item-model refactor. Food items currently skip the drawer and go directly
 * to the form modal on click (Chunk 4); this drawer is effectively recipe-only
 * for now but the variable naming + field paths are generic so a food-item
 * variant can be added later without a rewrite.
 *
 * Desktop: slides in from right, ~480px wide, full height.
 * Mobile (<768px): bottom sheet, ~85% viewport height.
 * Focus trapped inside (via Headless UI Dialog).
 */
export default function ItemDetailDrawer({ itemId, isOpen, onClose, onEditItem, onDeleteItem }) {
  const [item, setItem] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null) // null | '404' | 'network'
  const closeButtonRef = useRef(null)

  const fetchItem = useCallback(async () => {
    if (!itemId) return
    setLoading(true)
    setError(null)
    try {
      const res = await axios.get(`${API_BASE}/items/${itemId}`)
      setItem(res.data)
    } catch (err) {
      if (err.response?.status === 404) {
        setError('404')
      } else {
        setError('network')
      }
    } finally {
      setLoading(false)
    }
  }, [itemId])

  useEffect(() => {
    if (isOpen && itemId) {
      fetchItem()
    }
    if (!isOpen) {
      setItem(null)
      setError(null)
    }
  }, [isOpen, itemId, fetchItem])

  const handleEdit = () => {
    onClose()
    if (item && onEditItem) {
      onEditItem(item)
    }
  }

  const handleDelete = () => {
    // Close drawer, then hand the item up to the parent which owns the
    // ConfirmDialog + soft-delete + undo toast flow. Matches the same
    // delete path used by the card hover actions.
    onClose()
    if (item && onDeleteItem) {
      onDeleteItem(item)
    }
  }

  const handleToggleFavorite = async () => {
    if (!item) return
    const next = !item.is_favorite
    // Optimistic: flip locally so the button responds instantly.
    setItem({ ...item, is_favorite: next })
    try {
      await axios.patch(`${API_BASE}/items/${item.id}`, { is_favorite: next })
    } catch {
      // Roll back on failure
      setItem({ ...item, is_favorite: !next })
    }
  }

  const rd = item?.recipe_detail || {}
  const heroSrc = rd.image_url
    ? (rd.image_url.startsWith('http') ? rd.image_url : `${API_BASE}${rd.image_url}`)
    : null

  return (
    <Transition.Root show={isOpen} as={Fragment} appear>
      <Dialog onClose={onClose} className="relative z-50" initialFocus={closeButtonRef}>
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="transition-opacity duration-250 ease-out"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="transition-opacity duration-200 ease-in"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/20 dark:bg-black/40" aria-hidden="true" />
        </Transition.Child>

        {/* Drawer container */}
        <div className="fixed inset-0 flex justify-end">
          <Transition.Child
            as={Fragment}
            enter="transform transition-transform duration-250 ease-out"
            enterFrom="translate-x-full max-md:translate-y-full max-md:translate-x-0"
            enterTo="translate-x-0 max-md:translate-y-0"
            leave="transform transition-transform duration-200 ease-in"
            leaveFrom="translate-x-0 max-md:translate-y-0"
            leaveTo="translate-x-full max-md:translate-y-full max-md:translate-x-0"
          >
            <Dialog.Panel
              className="
                w-full md:w-[480px] md:max-w-[480px]
                max-md:mt-[15vh] max-md:rounded-t-2xl
                md:h-full
                bg-card-bg dark:bg-gray-800
                md:border-l border-card-border dark:border-gray-700
                shadow-xl
                flex flex-col overflow-hidden
              "
            >
              {/* Hero section */}
              <div className="relative flex-shrink-0">
                {loading ? (
                  <div className="h-44 bg-warm-sand dark:bg-gray-700 animate-pulse" />
                ) : heroSrc ? (
                  <img src={heroSrc} alt={item.name} className="w-full h-44 object-cover" />
                ) : (
                  <div className="h-44 bg-gradient-to-br from-terracotta-50 to-terracotta-100 dark:from-gray-700 dark:to-gray-600" />
                )}

                {/* Close button */}
                <button
                  ref={closeButtonRef}
                  type="button"
                  onClick={onClose}
                  aria-label="Close drawer"
                  className="
                    absolute top-3 right-3
                    w-9 h-9 flex items-center justify-center rounded-full
                    bg-card-bg/80 dark:bg-gray-800/80 backdrop-blur-sm
                    text-text-secondary dark:text-gray-300
                    hover:bg-card-bg dark:hover:bg-gray-800
                    transition-colors
                  "
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>

                {/* Name + metadata overlay */}
                {!loading && item && (
                  <div className="absolute bottom-0 left-0 right-0 px-5 pb-4 pt-12 bg-gradient-to-t from-card-bg via-card-bg/90 to-transparent dark:from-gray-800 dark:via-gray-800/90">
                    <h2 className="text-xl font-semibold text-text-primary dark:text-gray-100">{item.name}</h2>
                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      {rd.prep_time_minutes > 0 && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-warm-sand/80 dark:bg-gray-700 text-xs text-text-secondary dark:text-gray-300">
                          ⏲ {rd.prep_time_minutes}m prep
                        </span>
                      )}
                      {rd.cook_time_minutes > 0 && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-warm-sand/80 dark:bg-gray-700 text-xs text-text-secondary dark:text-gray-300">
                          ⏲ {rd.cook_time_minutes}m cook
                        </span>
                      )}
                      {rd.servings && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-warm-sand/80 dark:bg-gray-700 text-xs text-text-secondary dark:text-gray-300">
                          👥 {rd.servings}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto">
                {loading && <DrawerSkeleton />}

                {error === '404' && (
                  <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
                    <div className="w-12 h-12 text-text-muted dark:text-gray-500 mb-3">
                      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                      </svg>
                    </div>
                    <p className="text-base font-medium text-text-primary dark:text-gray-100">This item was deleted</p>
                    <button
                      type="button"
                      onClick={onClose}
                      className="mt-4 px-4 py-2 bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 rounded-lg hover:bg-warm-beige dark:hover:bg-gray-600 transition-colors"
                    >
                      Close
                    </button>
                  </div>
                )}

                {error === 'network' && (
                  <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
                    <div className="w-12 h-12 text-terracotta-600 dark:text-red-400 mb-3">
                      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
                      </svg>
                    </div>
                    <p className="text-base font-medium text-text-primary dark:text-gray-100">Couldn't load item</p>
                    <p className="text-sm text-text-secondary dark:text-gray-400 mt-1">Check your connection and try again.</p>
                    <button
                      type="button"
                      onClick={fetchItem}
                      className="mt-4 px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 text-white rounded-lg transition-colors"
                    >
                      Retry
                    </button>
                  </div>
                )}

                {!loading && !error && item && (
                  <div className="px-5 py-4 space-y-5" style={{ animation: 'view-crossfade 250ms ease both' }}>
                    {/* Action buttons — Edit (primary) | Favorite | Delete (ghost far-right)
                        Per plan §1667 (Design Review IA pass issue 5A): Delete lives in
                        the action row alongside Edit and Favorite, ghost-styled, no
                        border/background. The ConfirmDialog provides the safety net. */}
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleEdit}
                        className="flex-1 px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
                      >
                        Edit {item.item_type === 'food_item' ? 'food item' : 'recipe'}
                      </button>
                      <button
                        type="button"
                        onClick={handleToggleFavorite}
                        aria-pressed={item.is_favorite}
                        aria-label={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                        className={`px-4 py-2 rounded-lg border transition-colors text-sm font-medium ${
                          item.is_favorite
                            ? 'bg-terracotta-50 dark:bg-red-900/20 border-terracotta-200 dark:border-red-800 text-terracotta-600 dark:text-red-400'
                            : 'bg-warm-sand dark:bg-gray-700 border-card-border dark:border-gray-600 text-text-secondary dark:text-gray-300'
                        }`}
                      >
                        {item.is_favorite ? '❤ Favorite' : '♡ Favorite'}
                      </button>
                      <button
                        type="button"
                        onClick={handleDelete}
                        aria-label={`Delete ${item.name}`}
                        className="
                          px-3 py-2 min-h-[44px] text-sm font-medium
                          text-text-muted dark:text-gray-500
                          hover:text-red-600 dark:hover:text-red-400
                          hover:bg-red-50 dark:hover:bg-red-900/20
                          rounded-lg transition-colors
                          focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2
                        "
                      >
                        Delete
                      </button>
                    </div>

                    {/* Description */}
                    {rd.description && (
                      <div>
                        <p className="text-sm text-text-secondary dark:text-gray-300 leading-relaxed">{rd.description}</p>
                      </div>
                    )}

                    {/* View Original — only for recipes imported from a URL.
                        Defense in depth: only render the anchor if source_url
                        is an http(s) URL, otherwise `javascript:` stored in a
                        legacy row would execute on click. Backend schema also
                        enforces this, but the frontend defends itself. */}
                    {rd.source_url && /^https?:\/\//i.test(rd.source_url) && (
                      <div>
                        <a
                          href={rd.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-terracotta-600 dark:text-terracotta-400 hover:underline inline-flex items-center gap-1"
                        >
                          View original recipe ↗
                        </a>
                      </div>
                    )}

                    {/* Ingredients */}
                    {rd.ingredients && rd.ingredients.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold text-text-primary dark:text-gray-100 mb-2">Ingredients</h3>
                        <ul className="space-y-1.5">
                          {rd.ingredients.map((ing, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-text-secondary dark:text-gray-300">
                              <span className="text-terracotta-500 dark:text-blue-400 mt-0.5">•</span>
                              <span>
                                {ing.quantity && ing.quantity > 0 && <strong>{ing.quantity} {ing.unit || ''} </strong>}
                                {ing.name}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Instructions */}
                    {rd.instructions && (
                      <div>
                        <h3 className="text-sm font-semibold text-text-primary dark:text-gray-100 mb-2">Instructions</h3>
                        <div className="text-sm text-text-secondary dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                          {rd.instructions}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition.Root>
  )
}

function DrawerSkeleton() {
  return (
    <div className="px-5 py-4 space-y-4 animate-pulse">
      <div className="flex gap-2">
        <div className="flex-1 h-10 bg-warm-sand dark:bg-gray-700 rounded-lg" />
        <div className="w-28 h-10 bg-warm-sand dark:bg-gray-700 rounded-lg" />
      </div>
      <div className="space-y-2">
        <div className="h-4 bg-warm-sand dark:bg-gray-700 rounded w-full" />
        <div className="h-4 bg-warm-sand dark:bg-gray-700 rounded w-4/5" />
      </div>
      <div className="space-y-2">
        <div className="h-5 bg-warm-sand dark:bg-gray-700 rounded w-24" />
        {[90, 70, 85, 60, 80].map((w, i) => (
          <div key={i} className="h-4 bg-warm-sand dark:bg-gray-700 rounded" style={{ width: `${w}%` }} />
        ))}
      </div>
      <div className="space-y-2">
        <div className="h-5 bg-warm-sand dark:bg-gray-700 rounded w-24" />
        {[95, 88, 92, 70, 85, 78].map((w, i) => (
          <div key={i} className="h-4 bg-warm-sand dark:bg-gray-700 rounded" style={{ width: `${w}%` }} />
        ))}
      </div>
    </div>
  )
}
