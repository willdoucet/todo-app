/**
 * Vitest setup file - runs before each test file.
 *
 * This file:
 * 1. Adds jest-dom matchers (toBeInTheDocument, toHaveClass, etc.)
 * 2. Sets up MSW to intercept API calls
 * 3. Cleans up after each test
 */

import '@testing-library/jest-dom/vitest'
import { beforeAll, afterEach, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import { server } from './mocks/server'

// =============================================================================
// MSW Setup
// =============================================================================

// Start MSW server before all tests
beforeAll(() => {
  server.listen({
    // Warn about unhandled requests (helps catch missing handlers)
    onUnhandledRequest: 'warn',
  })
})

// Reset handlers after each test (removes any runtime handlers)
afterEach(() => {
  server.resetHandlers()
})

// Stop MSW server after all tests
afterAll(() => {
  server.close()
})

// =============================================================================
// React Testing Library Cleanup
// =============================================================================

// Cleanup DOM after each test (unmount components)
afterEach(() => {
  cleanup()
})

// =============================================================================
// Global Mocks
// =============================================================================

// Mock window.matchMedia (used by some UI libraries)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})

// Mock localStorage with actual storage functionality
const createLocalStorageMock = () => {
  let store = {}
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => {
      store[key] = String(value)
    },
    removeItem: (key) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
}
const localStorageMock = createLocalStorageMock()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })
