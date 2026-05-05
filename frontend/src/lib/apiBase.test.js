import { describe, it, expect } from 'vitest'
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
