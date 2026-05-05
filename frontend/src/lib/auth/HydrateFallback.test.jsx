import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import HydrateFallback from './HydrateFallback'

// SC #17 — HydrateFallback respects dark-mode preference without provider
// access. We test localStorage='true', localStorage='false', and the
// no-preference fallback through prefers-color-scheme.

describe('HydrateFallback', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders a status role for screen readers', () => {
    const { getByRole } = render(<HydrateFallback />)
    expect(getByRole('status')).toBeInTheDocument()
  })

  it('uses the dark wrapper when localStorage darkMode=true', () => {
    localStorage.setItem('darkMode', 'true')
    const { getByRole } = render(<HydrateFallback />)
    expect(getByRole('status').className).toMatch(/bg-gray-900/)
  })

  it('uses the light wrapper when localStorage darkMode=false', () => {
    localStorage.setItem('darkMode', 'false')
    const { getByRole } = render(<HydrateFallback />)
    expect(getByRole('status').className).toMatch(/bg-warm-cream/)
  })

  it('falls back to prefers-color-scheme when localStorage is unset', () => {
    // jsdom default: matchMedia returns false. We override.
    const original = window.matchMedia
    window.matchMedia = (q) =>
      q === '(prefers-color-scheme: dark)'
        ? { matches: true, media: q, addListener: () => {}, removeListener: () => {} }
        : { matches: false, media: q, addListener: () => {}, removeListener: () => {} }
    const { getByRole } = render(<HydrateFallback />)
    expect(getByRole('status').className).toMatch(/bg-gray-900/)
    window.matchMedia = original
  })
})
