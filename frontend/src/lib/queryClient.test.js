import { describe, it, expect, beforeEach, vi } from 'vitest'
import axios from 'axios'

vi.mock('./auth/redirect', () => ({
  redirectToAuthOnce: vi.fn(),
}))

import { redirectToAuthOnce } from './auth/redirect'
import { handle401, createQueryClient } from './queryClient'

describe('queryClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('handle401', () => {
    // SC #42 — handle401 type-and-status guard.
    it('redirects only on a real axios 401', () => {
      const err = Object.assign(new Error('401'), {
        isAxiosError: true,
        config: {},
        response: { status: 401 },
      })
      // axios.isAxiosError checks the prototype chain in real life; with
      // jsdom + mocked axios we simulate the brand symbol. Use the runtime
      // helper.
      vi.spyOn(axios, 'isAxiosError').mockImplementation(
        (e) => e?.isAxiosError === true
      )
      handle401(err)
      expect(redirectToAuthOnce).toHaveBeenCalledTimes(1)
    })

    it('does NOT redirect on a 500 axios error', () => {
      const err = Object.assign(new Error('500'), {
        isAxiosError: true,
        response: { status: 500 },
      })
      vi.spyOn(axios, 'isAxiosError').mockImplementation(
        (e) => e?.isAxiosError === true
      )
      handle401(err)
      expect(redirectToAuthOnce).not.toHaveBeenCalled()
    })

    it('does NOT redirect on a network failure (no response, no status)', () => {
      const err = Object.assign(new Error('Network Error'), {
        isAxiosError: true,
        // no response field
      })
      vi.spyOn(axios, 'isAxiosError').mockImplementation(
        (e) => e?.isAxiosError === true
      )
      handle401(err)
      expect(redirectToAuthOnce).not.toHaveBeenCalled()
    })

    it('does NOT redirect on a non-axios Error with status: 401 shape', () => {
      const err = Object.assign(new Error('fake'), {
        response: { status: 401 },
      })
      vi.spyOn(axios, 'isAxiosError').mockImplementation(
        (e) => e?.isAxiosError === true
      )
      handle401(err)
      expect(redirectToAuthOnce).not.toHaveBeenCalled()
    })

    it.each([null, undefined])('does NOT redirect on %s', (input) => {
      vi.spyOn(axios, 'isAxiosError').mockImplementation(
        (e) => e?.isAxiosError === true
      )
      handle401(input)
      expect(redirectToAuthOnce).not.toHaveBeenCalled()
    })
  })

  describe('createQueryClient', () => {
    it('returns a QueryClient with QueryCache and MutationCache wired', () => {
      const client = createQueryClient()
      expect(client.getQueryCache()).toBeDefined()
      expect(client.getMutationCache()).toBeDefined()
      // Default options include staleTime + retry: false.
      const defaults = client.getDefaultOptions()
      expect(defaults.queries?.staleTime).toBe(30_000)
      expect(defaults.queries?.retry).toBe(false)
      expect(defaults.mutations?.retry).toBe(false)
    })
  })
})
