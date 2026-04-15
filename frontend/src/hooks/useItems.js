import { useCallback, useEffect, useRef, useState } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Canonical hook for the unified Item model (replaces useRecipes + useFoodItems).
 *
 * @param {Object} options
 * @param {'recipe'|'food_item'|undefined} options.type — filter by item_type; omit for all
 * @param {boolean} options.favoritesOnly — only return favorited items
 * @param {string} options.search — case-insensitive name search
 * @param {boolean} options.skip — skip the initial fetch (useful when the parent owns data)
 *
 * @returns {{
 *   items: Array,
 *   loading: boolean,
 *   error: string|null,
 *   refetch: () => Promise<void>,
 *   createItem: (payload) => Promise<Object>,
 *   updateItem: (id, patch) => Promise<Object>,
 *   deleteItem: (id) => Promise<{id, undo_token, expires_at}>,
 *   undoDeleteItem: (id, undoToken) => Promise<Object>,
 *   toggleFavorite: (item) => Promise<Object>,
 * }}
 */
export function useItems({ type, favoritesOnly = false, search = '', skip = false } = {}) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(!skip)
  const [error, setError] = useState(null)
  // Track the latest request so stale responses don't overwrite fresh state.
  const requestIdRef = useRef(0)

  const refetch = useCallback(async () => {
    const id = ++requestIdRef.current
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (type) params.type = type
      if (favoritesOnly) params.favorites_only = true
      if (search) params.search = search
      const res = await axios.get(`${API_BASE}/items/`, { params })
      if (id === requestIdRef.current) {
        setItems(res.data)
      }
    } catch (err) {
      if (id === requestIdRef.current) {
        setError(err.response?.data?.detail || 'Failed to load items')
      }
    } finally {
      if (id === requestIdRef.current) {
        setLoading(false)
      }
    }
  }, [type, favoritesOnly, search])

  useEffect(() => {
    if (skip) return
    refetch()
  }, [refetch, skip])

  const createItem = useCallback(async (payload) => {
    const res = await axios.post(`${API_BASE}/items/`, payload)
    setItems((prev) => [...prev, res.data])
    return res.data
  }, [])

  const updateItem = useCallback(async (id, patch) => {
    const res = await axios.patch(`${API_BASE}/items/${id}`, patch)
    setItems((prev) => prev.map((it) => (it.id === id ? res.data : it)))
    return res.data
  }, [])

  const deleteItem = useCallback(async (id) => {
    // Optimistic hide: remove from the local list immediately so the UI feels snappy.
    // On API error, the caller should call refetch() to restore.
    const removed = items.find((it) => it.id === id)
    setItems((prev) => prev.filter((it) => it.id !== id))
    try {
      const res = await axios.delete(`${API_BASE}/items/${id}`)
      return res.data  // { id, undo_token, expires_at }
    } catch (err) {
      // Rollback on failure
      if (removed) {
        setItems((prev) => [...prev, removed])
      }
      throw err
    }
  }, [items])

  const undoDeleteItem = useCallback(async (id, undoToken) => {
    const res = await axios.post(`${API_BASE}/items/${id}/undo`, { undo_token: undoToken })
    setItems((prev) => {
      // Insert the restored item if it's not already there (it shouldn't be, since deleteItem
      // optimistically removed it).
      if (prev.some((it) => it.id === id)) return prev
      return [...prev, res.data]
    })
    return res.data
  }, [])

  const toggleFavorite = useCallback(async (item) => {
    return updateItem(item.id, { is_favorite: !item.is_favorite })
  }, [updateItem])

  return {
    items,
    loading,
    error,
    refetch,
    createItem,
    updateItem,
    deleteItem,
    undoDeleteItem,
    toggleFavorite,
  }
}
