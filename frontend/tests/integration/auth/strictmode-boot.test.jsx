// SC #29 — StrictMode boot integration test. React 18's StrictMode
// double-invokes effects in dev; the data router's loader can also be
// double-fired during initial routing. performRefresh's single-flight
// guard must coalesce concurrent calls into ONE POST /auth/refresh.
//
// Verified at the performRefresh layer (the unit it actually defends):
// the layer-above behavior — the data router's interaction with StrictMode
// — relies on the same module-scope `inFlight` Promise that this test
// pins, so a single-flight regression here is the single-flight regression
// in the boot path too.

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'

import { server } from '../../mocks/server'
import { tokenStore } from '../../../src/lib/auth/tokenStore'
import { performRefresh } from '../../../src/lib/auth/refresh'

const API_BASE = 'http://localhost:8000'

beforeEach(() => {
  tokenStore.clear()
})

afterEach(() => {
  server.resetHandlers()
})

describe('StrictMode boot single-flight', () => {
  it('coalesces two concurrent boot-time refresh calls into ONE POST', async () => {
    let refreshCallCount = 0
    let resolveRefresh
    const refreshGate = new Promise((resolve) => {
      resolveRefresh = resolve
    })

    server.use(
      http.post(`${API_BASE}/auth/refresh`, async () => {
        refreshCallCount++
        await refreshGate
        return HttpResponse.json({ access_token: 'boot.token' })
      }),
    )

    // Simulate StrictMode double-mount of a loader that calls performRefresh.
    // Both calls happen synchronously during a single microtask, so the
    // module-scope `inFlight` Promise must coalesce them.
    const callA = performRefresh()
    const callB = performRefresh()
    resolveRefresh()
    await Promise.all([callA, callB])

    expect(refreshCallCount).toBe(1)
    expect(tokenStore.getSnapshot()).toBe('boot.token')
  })

  it('a second cold boot AFTER the first settles fires a fresh POST', async () => {
    let refreshCallCount = 0
    server.use(
      http.post(`${API_BASE}/auth/refresh`, () => {
        refreshCallCount++
        return HttpResponse.json({ access_token: `boot.token.${refreshCallCount}` })
      }),
    )

    await performRefresh()
    expect(refreshCallCount).toBe(1)
    expect(tokenStore.getSnapshot()).toBe('boot.token.1')

    // Simulate a logout-and-back-in scenario — the in-flight guard must
    // have been reset so a brand-new boot can refresh again.
    tokenStore.clear()
    await performRefresh()
    expect(refreshCallCount).toBe(2)
    expect(tokenStore.getSnapshot()).toBe('boot.token.2')
  })
})
