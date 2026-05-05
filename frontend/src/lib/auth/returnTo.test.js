import { describe, it, expect } from 'vitest'
import { isSafeReturnTo, safeReturnTo } from './returnTo'

// SC #22 + Critical Path #8 — open-redirect defense. The full malicious
// table is enumerated here; downstream callers (AuthPortalPage, loader)
// only need a single-line check.

describe('isSafeReturnTo', () => {
  describe('accepts', () => {
    it.each([
      ['/'],
      ['/calendar'],
      ['/lists'],
      ['/lists?filter=today'],
      ['/responsibilities/123'],
      ['/mealboard/2025-12-01'],
      // /authsomething is NOT /auth — must pass
      ['/authentic-route'],
    ])('returns true for %s', (input) => {
      expect(isSafeReturnTo(input)).toBe(true)
    })
  })

  describe('rejects', () => {
    it.each([
      // Empty / non-string
      [null, 'null'],
      [undefined, 'undefined'],
      ['', 'empty string'],
      [42, 'number'],
      [{}, 'object'],
      // Absolute URLs
      ['https://evil.com/', 'absolute https URL'],
      ['http://evil.com', 'absolute http URL'],
      ['HTTPS://Evil.com', 'mixed-case absolute URL'],
      // Protocol-relative (browser fills in the current scheme)
      ['//evil.com', 'protocol-relative'],
      ['//evil.com/path', 'protocol-relative with path'],
      // Other schemes
      ['javascript:alert(1)', 'javascript: scheme'],
      ['data:text/html,<script>', 'data: scheme'],
      ['file:///etc/passwd', 'file: scheme'],
      // Non-rooted paths
      ['relative/path', 'no leading slash'],
      ['../escape', 'parent-dir traversal'],
      // /auth loops
      ['/auth', 'bare /auth'],
      ['/auth/login', '/auth/login'],
      ['/auth?return_to=/calendar', '/auth with nested return_to'],
      // Control chars / header injection
      ['/calendar\r\nLocation:evil.com', 'CRLF injection'],
      ['/calendar\nx', 'LF injection'],
      ['/calendar\x00x', 'NUL byte'],
      ['/calendar\x7fx', 'DEL char'],
    ])('returns false for %s (%s)', (input) => {
      expect(isSafeReturnTo(input)).toBe(false)
    })
  })
})

describe('safeReturnTo', () => {
  it('returns the input when safe', () => {
    expect(safeReturnTo('/calendar')).toBe('/calendar')
  })

  it('returns null when unsafe', () => {
    expect(safeReturnTo('https://evil.com')).toBeNull()
    expect(safeReturnTo('/auth')).toBeNull()
    expect(safeReturnTo(undefined)).toBeNull()
  })
})
