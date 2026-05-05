import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  setRouter,
  redirectToAuthOnce,
  resetRedirectGuard,
  __resetRedirectModuleState,
} from './redirect'
import { tokenStore } from './tokenStore'

describe('redirect', () => {
  let router
  let originalLocation

  beforeEach(() => {
    __resetRedirectModuleState()
    tokenStore.setToken('initial')

    // Stub window.location to a protected route. jsdom keeps location
    // stable across tests, so the path needs explicit override per case.
    originalLocation = window.location
    delete window.location
    window.location = new URL('http://localhost:5173/calendar')

    router = { navigate: vi.fn() }
  })

  afterEach(() => {
    window.location = originalLocation
  })

  // SC #11 — five concurrent 401s produce exactly ONE router.navigate.
  it('coalesces concurrent calls into a single navigation', () => {
    setRouter(router)
    redirectToAuthOnce()
    redirectToAuthOnce()
    redirectToAuthOnce()
    redirectToAuthOnce()
    redirectToAuthOnce()
    expect(router.navigate).toHaveBeenCalledTimes(1)
  })

  it('navigates with an encoded return_to capturing the current path+search', () => {
    delete window.location
    window.location = new URL('http://localhost:5173/calendar?date=2025-12-01')
    setRouter(router)
    redirectToAuthOnce()
    expect(router.navigate).toHaveBeenCalledWith(
      `/auth?return_to=${encodeURIComponent('/calendar?date=2025-12-01')}`
    )
  })

  it('clears the in-memory token on redirect', () => {
    setRouter(router)
    expect(tokenStore.getSnapshot()).toBe('initial')
    redirectToAuthOnce()
    expect(tokenStore.getSnapshot()).toBeNull()
  })

  it('does not navigate when already on /auth', () => {
    delete window.location
    window.location = new URL('http://localhost:5173/auth?return_to=%2F')
    setRouter(router)
    redirectToAuthOnce()
    expect(router.navigate).not.toHaveBeenCalled()
  })

  // SC #35 — self-heal when _router is null. Verifies the
  // unit-test-pollution / pre-bootstrap-deadlock window is closed.
  describe('self-heal when router is null (SC #35)', () => {
    it('does not throw', () => {
      expect(() => redirectToAuthOnce()).not.toThrow()
    })

    it('clears the token even though navigation is impossible', () => {
      redirectToAuthOnce()
      expect(tokenStore.getSnapshot()).toBeNull()
    })

    it('keeps the redirecting guard false so subsequent calls (after setRouter) still navigate', () => {
      redirectToAuthOnce() // no router yet — clears token, no-op nav
      tokenStore.setToken('rebound')
      setRouter(router)
      redirectToAuthOnce()
      expect(router.navigate).toHaveBeenCalledTimes(1)
    })

    it('logs a DEV warning', () => {
      const spy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      redirectToAuthOnce()
      expect(spy).toHaveBeenCalled()
      spy.mockRestore()
    })
  })

  describe('resetRedirectGuard', () => {
    it('allows another navigation after the /auth route resets the guard', () => {
      setRouter(router)
      redirectToAuthOnce()
      expect(router.navigate).toHaveBeenCalledTimes(1)

      resetRedirectGuard()
      // Move off /auth to simulate the user logging in and the next 401 firing.
      delete window.location
      window.location = new URL('http://localhost:5173/calendar')
      redirectToAuthOnce()
      expect(router.navigate).toHaveBeenCalledTimes(2)
    })
  })
})
