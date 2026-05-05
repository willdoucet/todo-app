import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import axios from 'axios'

// Mock axios at the module level so performRefresh's raw axios.post call
// is intercepted (and recursion through the wrapped api instance is moot).
vi.mock('axios')

import { performRefresh, setLoggingOut, waitForRefreshToSettle } from './refresh'
import { tokenStore } from './tokenStore'

describe('refresh', () => {
  beforeEach(() => {
    tokenStore.clear()
    setLoggingOut(false)
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('populates the token on a 200 with a string access_token', async () => {
    axios.post.mockResolvedValueOnce({ data: { access_token: 'a.b.c' } })
    await performRefresh()
    expect(tokenStore.getSnapshot()).toBe('a.b.c')
  })

  it('throws and leaves tokenStore null on a malformed response', async () => {
    axios.post.mockResolvedValueOnce({ data: { access_token: 42 } })
    await expect(performRefresh()).rejects.toThrow(/malformed/)
    expect(tokenStore.getSnapshot()).toBeNull()
  })

  it('throws and leaves tokenStore null when access_token is missing', async () => {
    axios.post.mockResolvedValueOnce({ data: {} })
    await expect(performRefresh()).rejects.toThrow(/malformed/)
    expect(tokenStore.getSnapshot()).toBeNull()
  })

  // SC #5 + Critical Path #4 — single-flight behavior under concurrent
  // callers. Five parallel performRefresh() calls during a 401 storm must
  // result in exactly one POST /auth/refresh.
  it('coalesces concurrent callers into a single POST /auth/refresh', async () => {
    let resolveCall
    axios.post.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCall = () => resolve({ data: { access_token: 'shared' } })
        })
    )
    const promises = [
      performRefresh(),
      performRefresh(),
      performRefresh(),
      performRefresh(),
      performRefresh(),
    ]
    resolveCall()
    await Promise.all(promises)
    expect(axios.post).toHaveBeenCalledTimes(1)
    expect(tokenStore.getSnapshot()).toBe('shared')
  })

  it('resets inFlight on rejection so the next call can try again', async () => {
    axios.post.mockRejectedValueOnce(new Error('first attempt failed'))
    await expect(performRefresh()).rejects.toThrow('first attempt failed')

    axios.post.mockResolvedValueOnce({ data: { access_token: 'second' } })
    await performRefresh()
    expect(tokenStore.getSnapshot()).toBe('second')
    expect(axios.post).toHaveBeenCalledTimes(2)
  })

  it('passes withCredentials and a 10s timeout to axios', async () => {
    axios.post.mockResolvedValueOnce({ data: { access_token: 'tok' } })
    await performRefresh()
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      null,
      expect.objectContaining({ withCredentials: true, timeout: 10_000 })
    )
  })

  // SC #15 — performRefresh has a 10s timeout. We can't deterministically
  // simulate axios's internal timer, but we can assert that a thrown axios
  // timeout error propagates without populating the token.
  it('rejects when axios reports a timeout', async () => {
    const timeoutError = Object.assign(new Error('timeout of 10000ms'), {
      code: 'ECONNABORTED',
    })
    axios.post.mockRejectedValueOnce(timeoutError)
    await expect(performRefresh()).rejects.toThrow(/timeout/)
    expect(tokenStore.getSnapshot()).toBeNull()
  })

  // The logout flow flips `loggingOut = true` while the post is in flight.
  // performRefresh's network call still runs (so concurrent awaiters do not
  // hang), but the resulting token must NOT land in tokenStore — otherwise a
  // post-click refresh resurrects auth state after the user has signed out.
  describe('setLoggingOut', () => {
    it('discards a fresh token when loggingOut is true', async () => {
      axios.post.mockResolvedValueOnce({ data: { access_token: 'late.token' } })
      setLoggingOut(true)
      await performRefresh()
      expect(tokenStore.getSnapshot()).toBeNull()
      setLoggingOut(false)
    })

    it('writes the token normally when loggingOut is false', async () => {
      axios.post.mockResolvedValueOnce({ data: { access_token: 'normal.token' } })
      await performRefresh()
      expect(tokenStore.getSnapshot()).toBe('normal.token')
    })
  })

  describe('waitForRefreshToSettle', () => {
    it('returns immediately when nothing is in flight (Eng review 3)', async () => {
      const start = Date.now()
      await expect(waitForRefreshToSettle()).resolves.toBeUndefined()
      expect(Date.now() - start).toBeLessThan(50)
    })

    // SC #38 — logout cannot resurrect auth state from an in-flight refresh.
    it('awaits an in-flight refresh and never throws', async () => {
      let resolveCall
      axios.post.mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveCall = () => resolve({ data: { access_token: 'late' } })
          })
      )
      const refreshPromise = performRefresh()
      const settlePromise = waitForRefreshToSettle()
      resolveCall()
      await Promise.all([refreshPromise, settlePromise])
      expect(tokenStore.getSnapshot()).toBe('late')
    })

    it('does not throw even when the in-flight refresh rejects', async () => {
      let rejectCall
      axios.post.mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            rejectCall = () => reject(new Error('boom'))
          })
      )
      const refreshPromise = performRefresh().catch(() => {})
      const settlePromise = waitForRefreshToSettle()
      rejectCall()
      await Promise.all([refreshPromise, settlePromise])
      // settlePromise resolved (did not throw).
      expect(tokenStore.getSnapshot()).toBeNull()
    })
  })
})
