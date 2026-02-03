/**
 * Smoke test to verify the test infrastructure works.
 *
 * This test verifies:
 * 1. Vitest runs correctly
 * 2. jsdom is working (document exists)
 * 3. MSW is intercepting requests
 * 4. jest-dom matchers are available
 */

import { describe, it, expect } from 'vitest'

describe('Test Infrastructure', () => {
  it('vitest is working', () => {
    expect(1 + 1).toBe(2)
  })

  it('jsdom provides document object', () => {
    expect(document).toBeDefined()
    expect(document.createElement).toBeDefined()
  })

  it('jest-dom matchers are available', () => {
    const div = document.createElement('div')
    div.textContent = 'Hello'
    document.body.appendChild(div)

    expect(div).toBeInTheDocument()
    expect(div).toHaveTextContent('Hello')

    document.body.removeChild(div)
  })

  it('MSW intercepts API requests', async () => {
    // This should be intercepted by our handler in handlers.js
    const response = await fetch('http://localhost:8000/family-members')
    const data = await response.json()

    expect(response.ok).toBe(true)
    expect(Array.isArray(data)).toBe(true)
    expect(data.length).toBeGreaterThan(0)
    expect(data[0]).toHaveProperty('name')
  })
})
