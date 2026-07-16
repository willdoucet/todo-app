import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { API_BASE_URL, apiUrl } from './apiBase'

// SC #37: backend-uploaded media survives the API-client migration.
// apiUrl resolves relative `/uploads/...` paths against API_BASE_URL,
// passes already-absolute URLs through, and tolerates empty/nullish input.

describe('apiBase', () => {
  describe('API_BASE_URL', () => {
    it('exposes a non-empty string', () => {
      expect(typeof API_BASE_URL).toBe('string')
      expect(API_BASE_URL.length).toBeGreaterThan(0)
    })
  })

  // Protocol-upgrade guard — see apiBase.js _upgradeProtocolIfNeeded for
  // the rationale. We re-import the module under controlled `window.location`
  // and `import.meta.env` to exercise both branches.
  describe('protocol upgrade', () => {
    let originalLocation

    beforeEach(() => {
      originalLocation = window.location
      vi.resetModules()
    })

    afterEach(() => {
      Object.defineProperty(window, 'location', {
        value: originalLocation,
        writable: true,
        configurable: true,
      })
      vi.unstubAllEnvs()
      vi.resetModules()
    })

    function setProtocol(protocol) {
      Object.defineProperty(window, 'location', {
        value: { ...originalLocation, protocol },
        writable: true,
        configurable: true,
      })
    }

    it('upgrades http:// to https:// when the page is HTTPS', async () => {
      setProtocol('https:')
      vi.stubEnv('VITE_API_BASE_URL', 'http://api.mealy.dev')
      const mod = await import('./apiBase')
      expect(mod.API_BASE_URL).toBe('https://api.mealy.dev')
    })

    it('leaves http:// untouched when the page is HTTP (local dev)', async () => {
      setProtocol('http:')
      vi.stubEnv('VITE_API_BASE_URL', 'http://api.mealy.dev')
      const mod = await import('./apiBase')
      expect(mod.API_BASE_URL).toBe('http://api.mealy.dev')
    })

    it('exempts http://localhost:8000 even on an HTTPS page', async () => {
      setProtocol('https:')
      vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
      const mod = await import('./apiBase')
      expect(mod.API_BASE_URL).toBe('http://localhost:8000')
    })

    it('exempts http://127.0.0.1 even on an HTTPS page', async () => {
      setProtocol('https:')
      vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
      const mod = await import('./apiBase')
      expect(mod.API_BASE_URL).toBe('http://127.0.0.1:8000')
    })

    it('leaves https:// URLs untouched', async () => {
      setProtocol('https:')
      vi.stubEnv('VITE_API_BASE_URL', 'https://api.mealy.dev')
      const mod = await import('./apiBase')
      expect(mod.API_BASE_URL).toBe('https://api.mealy.dev')
    })
  })

  // M6 hardening — a production build with VITE_API_BASE_URL unset must fail
  // loud at module load rather than silently falling back to localhost:8000.
  // See apiBase.js. Dev/vitest (import.meta.env.PROD === false) keeps the
  // localhost fallback. These exercise the branch M6 added.
  describe('production build guard', () => {
    beforeEach(() => {
      vi.resetModules()
    })

    afterEach(() => {
      vi.unstubAllEnvs()
      vi.resetModules()
    })

    it('throws when VITE_API_BASE_URL is unset in a production build', async () => {
      vi.stubEnv('PROD', true)
      vi.stubEnv('VITE_API_BASE_URL', '')
      await expect(import('./apiBase')).rejects.toThrow(
        /VITE_API_BASE_URL is required in production/
      )
    })

    it('does not throw in a production build when VITE_API_BASE_URL is set', async () => {
      vi.stubEnv('PROD', true)
      vi.stubEnv('VITE_API_BASE_URL', 'https://api.mealy.dev')
      const mod = await import('./apiBase')
      expect(mod.API_BASE_URL).toBe('https://api.mealy.dev')
    })

    it('falls back to localhost in dev (non-prod) when unset', async () => {
      // vitest's default import.meta.env.PROD is false — exercise the dev path
      vi.stubEnv('VITE_API_BASE_URL', '')
      const mod = await import('./apiBase')
      expect(mod.API_BASE_URL).toBe('http://localhost:8000')
    })
  })

  describe('apiUrl', () => {
    it('prefixes relative paths with API_BASE_URL', () => {
      expect(apiUrl('/uploads/abc.png')).toBe(`${API_BASE_URL}/uploads/abc.png`)
    })

    it('inserts a leading slash when the path is missing one', () => {
      expect(apiUrl('uploads/abc.png')).toBe(`${API_BASE_URL}/uploads/abc.png`)
    })

    it('returns absolute http URLs unchanged', () => {
      const abs = 'http://example.com/img.png'
      expect(apiUrl(abs)).toBe(abs)
    })

    it('returns absolute https URLs unchanged', () => {
      const abs = 'https://cdn.example.com/img.png'
      expect(apiUrl(abs)).toBe(abs)
    })

    it('matches mixed-case scheme prefixes (HTTPS://)', () => {
      const abs = 'HTTPS://Example.com/x.png'
      expect(apiUrl(abs)).toBe(abs)
    })

    it('returns null/undefined unchanged so callers do not crash', () => {
      expect(apiUrl(null)).toBeNull()
      expect(apiUrl(undefined)).toBeUndefined()
      expect(apiUrl('')).toBe('')
    })
  })
})
