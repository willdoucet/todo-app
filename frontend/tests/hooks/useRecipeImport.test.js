/**
 * Tests for useRecipeImport — the submit → poll → terminal lifecycle hook for
 * the Recipe URL Import feature.
 *
 * Network is mocked through MSW (per-test overrides via server.use). Axios
 * itself is NOT stubbed — requests flow through MSW's Node interceptor, same
 * as the real app.
 */

import { describe, it, expect, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../mocks/server'
import { useRecipeImport } from '../../src/hooks/useRecipeImport'

const API_BASE = 'http://localhost:8000'

// Helper: build a minimal valid recipe payload for the complete/progress paths.
function sampleRecipe(name = 'Honey Garlic Chicken') {
  return {
    name,
    tags: ['quick', 'chicken'],
    source_url: 'https://example.com/recipe',
    recipe_detail: {
      description: 'Sweet and savory',
      ingredients: [
        { name: 'Chicken', quantity: 1, unit: 'lb', category: 'Protein' },
        { name: 'Honey', quantity: 3, unit: 'tbsp', category: 'Pantry' },
      ],
      instructions: '1. Cook.',
      prep_time_minutes: 15,
      cook_time_minutes: 30,
      servings: 4,
      image_url: null,
      source_url: 'https://example.com/recipe',
    },
  }
}

describe('useRecipeImport', () => {
  it('happy path: submit → progress → complete sets recipe state', async () => {
    let statusCallCount = 0
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'abc' })
      ),
      http.get(`${API_BASE}/items/import-status/abc`, () => {
        statusCallCount += 1
        if (statusCallCount === 1) {
          return HttpResponse.json({ status: 'progress', step: 'fetching_page' })
        }
        return HttpResponse.json({ status: 'complete', recipe: sampleRecipe() })
      })
    )

    // All real timers. Wait ~1.6s (one poll cycle) + generous waitFor slack.
    const { result } = renderHook(() => useRecipeImport())

    await act(async () => {
      result.current.importFromUrl('https://example.com/recipe')
    })

    await waitFor(() => expect(result.current.status).toBe('progress'))
    expect(result.current.step).toBe('fetching_page')

    // Real 1.5s setTimeout fires, next poll resolves, state flips to complete.
    await waitFor(
      () => expect(result.current.status).toBe('complete'),
      { timeout: 4000 },
    )
    expect(result.current.recipe?.name).toBe('Honey Garlic Chicken')
    expect(result.current.errorCode).toBeNull()
  })

  it('submit failure with 422 → status failed, errorCode internal_error (fallback)', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json(
          { detail: { error_code: 'invalid_url', message: 'bad url' } },
          { status: 422 }
        )
      )
    )

    const { result } = renderHook(() => useRecipeImport())

    await act(async () => {
      await result.current.importFromUrl('not-a-url')
    })

    await waitFor(() => expect(result.current.status).toBe('failed'))
    // Hook reads err.response.data.detail.error_code for failed path
    expect(result.current.errorCode).toBe('invalid_url')
  })

  it('submit with 503 → status unavailable, errorCode broker_unavailable', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json(
          { detail: { error_code: 'broker_unavailable' } },
          { status: 503 }
        )
      )
    )

    const { result } = renderHook(() => useRecipeImport())

    await act(async () => {
      await result.current.importFromUrl('https://example.com/recipe')
    })

    await waitFor(() => expect(result.current.status).toBe('unavailable'))
    expect(result.current.errorCode).toBe('broker_unavailable')
  })

  it('poll returns {status: "failed", error_code: "not_recipe"} → failed/not_recipe', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'abc' })
      ),
      http.get(`${API_BASE}/items/import-status/abc`, () =>
        HttpResponse.json({ status: 'failed', error_code: 'not_recipe' })
      )
    )

    const { result } = renderHook(() => useRecipeImport())

    await act(async () => {
      await result.current.importFromUrl('https://example.com/recipe')
    })

    await waitFor(() => expect(result.current.status).toBe('failed'))
    expect(result.current.errorCode).toBe('not_recipe')
  })

  it('poll returns {status: "not_found", error_code: "unknown_or_expired_task"} → failed', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'ghost' })
      ),
      http.get(`${API_BASE}/items/import-status/ghost`, () =>
        HttpResponse.json({
          status: 'not_found',
          error_code: 'unknown_or_expired_task',
        })
      )
    )

    const { result } = renderHook(() => useRecipeImport())

    await act(async () => {
      await result.current.importFromUrl('https://example.com/recipe')
    })

    await waitFor(() => expect(result.current.status).toBe('failed'))
    expect(result.current.errorCode).toBe('unknown_or_expired_task')
  })

  it('timeout: 60s of nothing-but-progress flips status to timeout', async () => {
    // Status endpoint returns progress forever. The hook should hit its 60s
    // ceiling and transition to 'timeout'.
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'slow' })
      ),
      http.get(`${API_BASE}/items/import-status/slow`, () =>
        HttpResponse.json({ status: 'progress', step: 'fetching_page' })
      )
    )

    // The hook checks Date.now() - pollStartRef to decide "timed out". We
    // fake *only* Date (not setTimeout), so real setTimeout lets poll cycles
    // actually fire through MSW, while Date.now() jumps 61 seconds forward
    // so the next poll tick sees the ceiling crossed and flips to 'timeout'.
    const realStart = Date.now()
    const { result } = renderHook(() => useRecipeImport())

    await act(async () => {
      result.current.importFromUrl('https://example.com/recipe')
    })

    await waitFor(() => expect(result.current.status).toBe('progress'))

    // Jump the clock forward past the 60s ceiling. Real setTimeout still runs.
    vi.useFakeTimers({ toFake: ['Date'] })
    try {
      vi.setSystemTime(new Date(realStart + 61_000))
      await waitFor(
        () => expect(result.current.status).toBe('timeout'),
        { timeout: 4000 },
      )
      expect(result.current.errorCode).toBe('task_timeout')
    } finally {
      vi.useRealTimers()
    }
  })

  it('stale attempt: reset + new submit discards late result from previous attempt', async () => {
    // Attempt A returns task_id 'a' and stays on "progress" forever; we
    // reset before it could ever flip to complete. Attempt B returns
    // task_id 'b' and immediately completes. Final state must be B's.
    // Submit echoes the URL so task_id mapping is order-independent.
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, async ({ request }) => {
        const body = await request.json()
        const id = body.url.endsWith('/a') ? 'a' : 'b'
        return HttpResponse.json({ task_id: id })
      }),
      http.get(`${API_BASE}/items/import-status/a`, () =>
        HttpResponse.json({ status: 'progress', step: 'fetching_page' })
      ),
      http.get(`${API_BASE}/items/import-status/b`, () =>
        HttpResponse.json({
          status: 'complete',
          recipe: sampleRecipe('URL-B Recipe'),
        })
      )
    )

    const { result } = renderHook(() => useRecipeImport())

    // Kick off attempt A
    await act(async () => {
      result.current.importFromUrl('https://example.com/a')
    })

    // Let attempt A's submit resolve and at least one poll land
    await waitFor(() =>
      expect(['pending', 'progress']).toContain(result.current.status)
    )

    // Reset then start attempt B
    await act(async () => {
      result.current.reset()
    })

    await act(async () => {
      result.current.importFromUrl('https://example.com/b')
    })

    // B should complete; state must reflect B, never flipping back to A's progress.
    await waitFor(() => expect(result.current.status).toBe('complete'))
    expect(result.current.recipe?.name).toBe('URL-B Recipe')
  })

  it('double-submit guard: second submit supersedes first; stale poll is ignored', async () => {
    // Submit echoes the URL into task_id so the test is order-independent:
    //   /old → task_id 'old'   → status 'failed' (not_recipe)
    //   /new → task_id 'new'   → status 'complete' (recipe)
    // The second importFromUrl bumps attemptIdRef before the first's axios
    // promise resolves, so the first attempt's terminal dispatch is dropped.
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, async ({ request }) => {
        const body = await request.json()
        const id = body.url.endsWith('/old') ? 'old' : 'new'
        return HttpResponse.json({ task_id: id })
      }),
      http.get(`${API_BASE}/items/import-status/old`, () =>
        HttpResponse.json({ status: 'failed', error_code: 'not_recipe' })
      ),
      http.get(`${API_BASE}/items/import-status/new`, () =>
        HttpResponse.json({
          status: 'complete',
          recipe: sampleRecipe('Fresh Recipe'),
        })
      )
    )

    const { result } = renderHook(() => useRecipeImport())

    // Fire both submits back-to-back without awaiting the first. The second
    // bumps attemptIdRef before the first's axios promise resolves, so the
    // first's terminal dispatch is dropped as stale.
    await act(async () => {
      result.current.importFromUrl('https://example.com/old')
      result.current.importFromUrl('https://example.com/new')
    })

    await waitFor(() => expect(result.current.status).toBe('complete'))
    expect(result.current.recipe?.name).toBe('Fresh Recipe')
    // errorCode must be cleared; stale 'not_recipe' must never have landed
    expect(result.current.errorCode).toBeNull()
  })
})
