// Integration tests for the api 401 → refresh → retry pipeline.
//
// Coordinates two distinct HTTP layers in one test: the wrapped `api` axios
// instance (response interceptor owns 401 handling) and `refresh.js`'s raw
// axios.post('/auth/refresh') (lives outside the interceptor). MSW intercepts
// both at the network level so the same handler set drives every path.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { http, HttpResponse } from 'msw'

import { server } from '../../mocks/server'

// redirect.js is mocked because tests assert call counts; the real
// implementation needs a router bound, which the integration suite does
// not bootstrap.
vi.mock('../../../src/lib/auth/redirect', () => ({
  redirectToAuthOnce: vi.fn(),
  setRouter: vi.fn(),
  resetRedirectGuard: vi.fn(),
  __resetRedirectModuleState: vi.fn(),
}))

import { api } from '../../../src/lib/api'
import { tokenStore } from '../../../src/lib/auth/tokenStore'
import { redirectToAuthOnce } from '../../../src/lib/auth/redirect'

const API_BASE = 'http://localhost:8000'

beforeEach(() => {
  vi.clearAllMocks()
  tokenStore.clear()
})

afterEach(() => {
  server.resetHandlers()
})

describe('api 401 → refresh → retry pipeline', () => {
  it('retries the original request with a fresh token when refresh succeeds', async () => {
    let originalCallCount = 0
    let refreshCallCount = 0

    server.use(
      http.get(`${API_BASE}/items`, ({ request }) => {
        originalCallCount++
        const auth = request.headers.get('authorization')
        // First call: stale bearer (or no bearer) → 401. Second call:
        // bearer must be the refreshed token → 200.
        if (originalCallCount === 1) {
          return HttpResponse.json({ error: 'unauthorized' }, { status: 401 })
        }
        if (auth === 'Bearer refreshed.token') {
          return HttpResponse.json({ ok: true })
        }
        return HttpResponse.json({ error: 'wrong bearer' }, { status: 500 })
      }),
      http.post(`${API_BASE}/auth/refresh`, () => {
        refreshCallCount++
        return HttpResponse.json({ access_token: 'refreshed.token' })
      }),
    )

    const res = await api.get('/items')
    expect(res.data).toEqual({ ok: true })
    expect(originalCallCount).toBe(2)
    expect(refreshCallCount).toBe(1)
    expect(tokenStore.getSnapshot()).toBe('refreshed.token')
    expect(redirectToAuthOnce).not.toHaveBeenCalled()
  })

  it('redirects to /auth when the refresh itself returns 401', async () => {
    let originalCallCount = 0
    let refreshCallCount = 0

    server.use(
      http.get(`${API_BASE}/items`, () => {
        originalCallCount++
        return HttpResponse.json({ error: 'unauthorized' }, { status: 401 })
      }),
      http.post(`${API_BASE}/auth/refresh`, () => {
        refreshCallCount++
        return HttpResponse.json({ error: 'expired' }, { status: 401 })
      }),
    )

    await expect(api.get('/items')).rejects.toMatchObject({
      response: { status: 401 },
    })
    expect(originalCallCount).toBe(1) // refresh failed, no retry
    expect(refreshCallCount).toBe(1)
    expect(tokenStore.getSnapshot()).toBeNull()
    expect(redirectToAuthOnce).toHaveBeenCalledTimes(1)
  })

  it('does NOT redirect on a non-401 refresh failure (5xx); rethrows server error', async () => {
    let originalCallCount = 0
    let refreshCallCount = 0

    server.use(
      http.get(`${API_BASE}/items`, () => {
        originalCallCount++
        return HttpResponse.json({ error: 'unauthorized' }, { status: 401 })
      }),
      http.post(`${API_BASE}/auth/refresh`, () => {
        refreshCallCount++
        return HttpResponse.json({ error: 'down' }, { status: 503 })
      }),
    )

    await expect(api.get('/items')).rejects.toMatchObject({
      response: { status: 503 },
    })
    expect(originalCallCount).toBe(1)
    expect(refreshCallCount).toBe(1)
    expect(redirectToAuthOnce).not.toHaveBeenCalled()
  })

  // SC #41 — _retried guard prevents an infinite refresh loop when both the
  // original and the retry come back 401. The retry-401 looks like a
  // refresh-failure-401 to the interceptor's catch block, so the redirect
  // helper fires once and the rejection propagates to the caller.
  it('does not call performRefresh a second time when the retry also returns 401', async () => {
    let originalCallCount = 0
    let refreshCallCount = 0

    server.use(
      http.get(`${API_BASE}/items`, () => {
        originalCallCount++
        return HttpResponse.json({ error: 'unauthorized' }, { status: 401 })
      }),
      http.post(`${API_BASE}/auth/refresh`, () => {
        refreshCallCount++
        return HttpResponse.json({ access_token: 'refreshed.token' })
      }),
    )

    await expect(api.get('/items')).rejects.toMatchObject({
      response: { status: 401 },
    })
    // Original + one retry = 2 hits.
    expect(originalCallCount).toBe(2)
    // Exactly one refresh — _retried suppressed the second.
    expect(refreshCallCount).toBe(1)
    // Imperative caller path: the retry-401 must trigger a redirect even
    // when the caller is not a TanStack Query subscriber.
    expect(redirectToAuthOnce).toHaveBeenCalledTimes(1)
  })

  // SC #5 — five concurrent 401-failing requests share a single refresh.
  it('coalesces N concurrent 401s into ONE POST /auth/refresh', async () => {
    let originalCallCount = 0
    let refreshCallCount = 0
    let resolveRefresh
    const refreshGate = new Promise((resolve) => {
      resolveRefresh = resolve
    })

    server.use(
      http.get(`${API_BASE}/items`, ({ request }) => {
        originalCallCount++
        const auth = request.headers.get('authorization')
        if (auth === 'Bearer refreshed.token') {
          return HttpResponse.json({ ok: true })
        }
        return HttpResponse.json({ error: 'unauthorized' }, { status: 401 })
      }),
      http.post(`${API_BASE}/auth/refresh`, async () => {
        refreshCallCount++
        await refreshGate
        return HttpResponse.json({ access_token: 'refreshed.token' })
      }),
    )

    const promises = [
      api.get('/items'),
      api.get('/items'),
      api.get('/items'),
      api.get('/items'),
      api.get('/items'),
    ]
    // Let the 5 401s pile up before allowing the refresh to resolve.
    await new Promise((r) => setTimeout(r, 10))
    resolveRefresh()
    const results = await Promise.all(promises)
    results.forEach((r) => expect(r.data).toEqual({ ok: true }))
    // 5 originals + 5 retries = 10. Exactly ONE refresh.
    expect(originalCallCount).toBe(10)
    expect(refreshCallCount).toBe(1)
  })
})
