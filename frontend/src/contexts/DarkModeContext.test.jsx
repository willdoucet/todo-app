/**
 * Tests for DarkModeContext
 *
 * Tests:
 * - Default state (light mode)
 * - Toggle functionality
 * - localStorage persistence
 * - Document class updates
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DarkModeProvider, useDarkMode } from './DarkModeContext'

// Test component that uses the hook
function TestComponent() {
  const { isDark, toggleDarkMode } = useDarkMode()
  return (
    <div>
      <span data-testid="mode">{isDark ? 'dark' : 'light'}</span>
      <button onClick={toggleDarkMode}>Toggle</button>
    </div>
  )
}

describe('DarkModeContext', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    // Reset document class
    document.documentElement.classList.remove('dark')
  })

  describe('initial state', () => {
    it('defaults to light mode when no localStorage value', () => {
      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      expect(screen.getByTestId('mode')).toHaveTextContent('light')
    })

    it('uses dark mode when localStorage has darkMode=true', () => {
      localStorage.setItem('darkMode', 'true')

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      expect(screen.getByTestId('mode')).toHaveTextContent('dark')
    })

    it('uses light mode when localStorage has darkMode=false', () => {
      localStorage.setItem('darkMode', 'false')

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      expect(screen.getByTestId('mode')).toHaveTextContent('light')
    })
  })

  describe('toggle functionality', () => {
    it('toggles from light to dark mode', async () => {
      const user = userEvent.setup()

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      expect(screen.getByTestId('mode')).toHaveTextContent('light')

      await user.click(screen.getByRole('button', { name: 'Toggle' }))

      expect(screen.getByTestId('mode')).toHaveTextContent('dark')
    })

    it('toggles from dark to light mode', async () => {
      localStorage.setItem('darkMode', 'true')
      const user = userEvent.setup()

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      expect(screen.getByTestId('mode')).toHaveTextContent('dark')

      await user.click(screen.getByRole('button', { name: 'Toggle' }))

      expect(screen.getByTestId('mode')).toHaveTextContent('light')
    })

    it('can toggle multiple times', async () => {
      const user = userEvent.setup()

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      const button = screen.getByRole('button', { name: 'Toggle' })

      expect(screen.getByTestId('mode')).toHaveTextContent('light')

      await user.click(button)
      expect(screen.getByTestId('mode')).toHaveTextContent('dark')

      await user.click(button)
      expect(screen.getByTestId('mode')).toHaveTextContent('light')

      await user.click(button)
      expect(screen.getByTestId('mode')).toHaveTextContent('dark')
    })
  })

  describe('localStorage persistence', () => {
    it('saves dark mode to localStorage when toggled on', async () => {
      const user = userEvent.setup()

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      await user.click(screen.getByRole('button', { name: 'Toggle' }))

      expect(localStorage.getItem('darkMode')).toBe('true')
    })

    it('saves light mode to localStorage when toggled off', async () => {
      localStorage.setItem('darkMode', 'true')
      const user = userEvent.setup()

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      await user.click(screen.getByRole('button', { name: 'Toggle' }))

      expect(localStorage.getItem('darkMode')).toBe('false')
    })
  })

  describe('document class updates', () => {
    it('adds dark class to document when dark mode is enabled', async () => {
      const user = userEvent.setup()

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      await user.click(screen.getByRole('button', { name: 'Toggle' }))

      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    it('removes dark class from document when dark mode is disabled', async () => {
      localStorage.setItem('darkMode', 'true')
      const user = userEvent.setup()

      render(
        <DarkModeProvider>
          <TestComponent />
        </DarkModeProvider>
      )

      // Should have dark class initially
      expect(document.documentElement.classList.contains('dark')).toBe(true)

      await user.click(screen.getByRole('button', { name: 'Toggle' }))

      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })
  })

  describe('useDarkMode hook', () => {
    it('throws error when used outside provider', () => {
      // Suppress console.error for this test
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => {
        render(<TestComponent />)
      }).toThrow('useDarkMode must be used within a DarkModeProvider')

      spy.mockRestore()
    })
  })
})
