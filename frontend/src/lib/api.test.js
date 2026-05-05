import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

vi.mock('./auth/redirect', () => ({
  redirectToAuthOnce: vi.fn(),
  setRouter: vi.fn(),
  resetRedirectGuard: vi.fn(),
  __resetRedirectModuleState: vi.fn(),
}))

import { api } from './api'
import { tokenStore } from './auth/tokenStore'
import { redirectToAuthOnce } from './auth/redirect'

// We don't use axios-mock-adapter to avoid an extra dep — test fully via
// axios's own request/response interceptor pipeline + manually-rejected
// adapter responses. Each test stubs `api.defaults.adapter` to control
// the network layer deterministically.

function makeAdapter(handler) {
  // axios adapter signature: (config) => Promise<{data, status, statusText, headers, config, request}>
  // Pass `config` through to error builders so the response interceptor's
  // `original.url?.startsWith('/auth/')` guard can see the real request path.
  return (config) =>
    Promise.resolve(handler(config)).then((res) =>
      res?.__error
        ? Promise.reject(
            Object.assign(new Error(`Request failed with status ${res.status}`), {
              isAxiosError: true,
              response: { status: res.status, data: res.data ?? {}, statusText: '', headers: {}, config },
              config,
            })
          )
        : { ...res, config }
    )
}

function ok(data = {}, status = 200) {
  return { data, status, statusText: 'OK', headers: {} }
}

function err(status, data = {}) {
  return { __error: true, status, data }
}

describe('api', () => {
  let originalAdapter

  beforeEach(() => {
    originalAdapter = api.defaults.adapter
    tokenStore.clear()
    vi.clearAllMocks()
    // axios.isAxiosError ships in real axios; jsdom's mocked module path
    // already preserves it. No spying needed.
  })

  afterEach(() => {
    api.defaults.adapter = originalAdapter
  })

  describe('request interceptor', () => {
    it('omits Authorization when no token is set', async () => {
      let captured
      api.defaults.adapter = makeAdapter((config) => {
        captured = config.headers
        return ok()
      })
      await api.get('/x')
      expect(captured.Authorization).toBeUndefined()
    })

    it('injects Bearer when a token is set', async () => {
      tokenStore.setToken('abc.def')
      let captured
      api.defaults.adapter = makeAdapter((config) => {
        captured = config.headers
        return ok()
      })
      await api.get('/x')
      expect(captured.Authorization).toBe('Bearer abc.def')
    })
  })

  describe('response interceptor — non-401 paths', () => {
    it('passes 200 responses through unchanged', async () => {
      api.defaults.adapter = makeAdapter(() => ok({ ok: true }))
      const res = await api.get('/x')
      expect(res.data).toEqual({ ok: true })
    })

    it('rethrows 500 errors without touching tokenStore or redirect', async () => {
      tokenStore.setToken('abc')
      let calls = 0
      api.defaults.adapter = makeAdapter(() => {
        calls++
        return err(500)
      })
      await expect(api.get('/x')).rejects.toMatchObject({
        response: { status: 500 },
      })
      expect(calls).toBe(1)
      expect(tokenStore.getSnapshot()).toBe('abc')
      expect(redirectToAuthOnce).not.toHaveBeenCalled()
    })

    // SC #28 — error.config undefined doesn't crash.
    it('rethrows when error.config is undefined (pre-flight failure)', async () => {
      api.defaults.adapter = () =>
        Promise.reject(
          Object.assign(new Error('Network Error'), {
            isAxiosError: true,
            // no config, no response
          })
        )
      await expect(api.get('/x')).rejects.toThrow(/Network Error/)
      expect(redirectToAuthOnce).not.toHaveBeenCalled()
    })
  })

  describe('response interceptor — /auth/* URL guard (SC #40)', () => {
    it('does NOT call performRefresh or redirect on /auth/login 401', async () => {
      // We stub the refresh module's behavior by ensuring the original 401
      // propagates and no second request is made.
      let calls = 0
      api.defaults.adapter = makeAdapter(() => {
        calls++
        return err(401, { error: 'invalid_credentials' })
      })
      await expect(api.post('/auth/login', { email: 'x', password: 'y' })).rejects.toMatchObject({
        response: { status: 401 },
      })
      expect(calls).toBe(1) // no retry
      expect(redirectToAuthOnce).not.toHaveBeenCalled()
    })

    it('does NOT call performRefresh on /auth/register 401', async () => {
      let calls = 0
      api.defaults.adapter = makeAdapter(() => {
        calls++
        return err(401)
      })
      await expect(
        api.post('/auth/register', { email: 'x', password: 'y', access_key: 'z' })
      ).rejects.toMatchObject({ response: { status: 401 } })
      expect(calls).toBe(1)
      expect(redirectToAuthOnce).not.toHaveBeenCalled()
    })

    it('does NOT call performRefresh on /auth/status non-200', async () => {
      let calls = 0
      api.defaults.adapter = makeAdapter(() => {
        calls++
        return err(401)
      })
      await expect(api.get('/auth/status')).rejects.toMatchObject({
        response: { status: 401 },
      })
      expect(calls).toBe(1)
    })
  })

  // Integration-style 401 → refresh → retry tests (including SC #41
  // `_retried` infinite-loop guard) live under
  // frontend/tests/integration/auth/api-401-flow.test.js — they need MSW
  // because the api response interceptor and refresh.js's raw axios call
  // resolve through different adapter chains.
})
