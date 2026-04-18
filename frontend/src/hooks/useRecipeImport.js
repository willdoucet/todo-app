import { useCallback, useEffect, useRef, useState } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Poll cadence: 1.5s × ~40 polls = 60s ceiling.
const POLL_INTERVAL_MS = 1500
const MAX_POLL_DURATION_MS = 60_000

const INITIAL = {
  status: 'idle',      // 'idle' | 'pending' | 'progress' | 'complete' | 'failed' | 'timeout' | 'unavailable'
  step: null,           // 'queued' | 'fetching_page' | 'cleaning_html' | 'extracting_recipe' | 'parsing_ingredients'
  recipe: null,         // { name, tags, source_url, recipe_detail } on complete
  errorCode: null,      // stable string when status === 'failed'
}

/**
 * Hook that owns the submit → poll → terminal lifecycle for URL imports.
 *
 * Returns:
 *   {
 *     status, step, recipe, errorCode,
 *     importFromUrl(url),
 *     reset(),
 *   }
 *
 * Stale-attempt guard: every submit bumps an `attemptId`; any poll result
 * that arrives after a reset or a new submit is ignored. This prevents a
 * late response from attempt A overwriting the preview/error of attempt B.
 */
export function useRecipeImport() {
  const [state, setState] = useState(INITIAL)

  // Tracks the currently-active attempt so late responses from prior attempts
  // can be discarded. Bumped on every submit + every reset.
  const attemptIdRef = useRef(0)
  const pollTimerRef = useRef(null)
  const pollStartRef = useRef(0)

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  const reset = useCallback(() => {
    attemptIdRef.current += 1  // invalidate any in-flight poll
    clearPollTimer()
    setState(INITIAL)
  }, [clearPollTimer])

  const importFromUrl = useCallback(async (url) => {
    const thisAttempt = ++attemptIdRef.current
    clearPollTimer()
    pollStartRef.current = Date.now()
    setState({ status: 'pending', step: 'queued', recipe: null, errorCode: null })

    let submitResponse
    try {
      submitResponse = await axios.post(`${API_BASE}/items/import-from-url`, { url })
    } catch (err) {
      if (thisAttempt !== attemptIdRef.current) return  // stale
      const httpStatus = err.response?.status
      // 404/501/503 from a stale-cached frontend against rolled-back backend:
      // surface as "unavailable" so the UI keeps the Manual tab usable.
      if (httpStatus === 404 || httpStatus === 501 || httpStatus === 503) {
        setState({
          status: 'unavailable',
          step: null,
          recipe: null,
          errorCode: err.response?.data?.detail?.error_code || 'broker_unavailable',
        })
        return
      }
      setState({
        status: 'failed',
        step: null,
        recipe: null,
        errorCode: err.response?.data?.detail?.error_code || 'internal_error',
      })
      return
    }

    // Stale check on the SUCCESS branch too — an earlier attempt's axios promise
    // can resolve after a reset()/new submit has already advanced attemptIdRef.
    // Without this, a stale success would overwrite a fresh pending/preview.
    if (thisAttempt !== attemptIdRef.current) return

    const taskId = submitResponse.data?.task_id
    if (!taskId) {
      setState({
        status: 'failed', step: null, recipe: null, errorCode: 'internal_error',
      })
      return
    }

    const pollOnce = async () => {
      if (thisAttempt !== attemptIdRef.current) return  // stale

      if (Date.now() - pollStartRef.current >= MAX_POLL_DURATION_MS) {
        setState({ status: 'timeout', step: null, recipe: null, errorCode: 'task_timeout' })
        return
      }

      let statusResponse
      try {
        statusResponse = await axios.get(`${API_BASE}/items/import-status/${taskId}`)
      } catch (err) {
        if (thisAttempt !== attemptIdRef.current) return
        const httpStatus = err.response?.status
        if (httpStatus === 404 || httpStatus === 501 || httpStatus === 503) {
          setState({
            status: 'unavailable',
            step: null,
            recipe: null,
            errorCode: err.response?.data?.detail?.error_code || 'broker_unavailable',
          })
          return
        }
        setState({
          status: 'failed', step: null, recipe: null, errorCode: 'internal_error',
        })
        return
      }

      if (thisAttempt !== attemptIdRef.current) return

      const body = statusResponse.data
      switch (body.status) {
        case 'pending':
          setState((prev) => ({ ...prev, status: 'pending', step: body.step || 'queued' }))
          pollTimerRef.current = setTimeout(pollOnce, POLL_INTERVAL_MS)
          return
        case 'progress':
          setState((prev) => ({ ...prev, status: 'progress', step: body.step || null }))
          pollTimerRef.current = setTimeout(pollOnce, POLL_INTERVAL_MS)
          return
        case 'complete':
          setState({
            status: 'complete',
            step: null,
            recipe: body.recipe,
            errorCode: null,
          })
          return
        case 'failed':
          setState({
            status: 'failed',
            step: null,
            recipe: null,
            errorCode: body.error_code || 'internal_error',
          })
          return
        case 'not_found':
          setState({
            status: 'failed',
            step: null,
            recipe: null,
            errorCode: body.error_code || 'unknown_or_expired_task',
          })
          return
        default:
          // Unknown status — keep polling until timeout.
          pollTimerRef.current = setTimeout(pollOnce, POLL_INTERVAL_MS)
      }
    }

    pollOnce()
  }, [clearPollTimer])

  // Cleanup on unmount: cancel any in-flight poll. The attempt counter bump
  // means any pending axios promise that resolves later is also ignored.
  useEffect(() => () => {
    attemptIdRef.current += 1
    clearPollTimer()
  }, [clearPollTimer])

  return {
    status: state.status,
    step: state.step,
    recipe: state.recipe,
    errorCode: state.errorCode,
    importFromUrl,
    reset,
  }
}
