import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'

// Mock DarkModeContext
vi.mock('../../../src/contexts/DarkModeContext', () => ({
  useDarkMode: () => ({ isDark: false }),
}))

// Mock emoji-mart modules to avoid loading real data in tests
vi.mock('emoji-mart', () => {
  class FakePicker {
    constructor(opts) {
      this.opts = opts
      // Create a real DOM element to act as the web component
      const el = document.createElement('div')
      el.setAttribute('data-testid', 'emoji-mart-picker')
      el.textContent = 'Emoji Picker'

      // Simulate clicking an emoji after mount
      el.addEventListener('click', () => {
        if (this.opts.onEmojiSelect) {
          this.opts.onEmojiSelect({ native: '🍎', id: 'apple' })
        }
      })

      // Return the element (Picker extends HTMLElement, so `new Picker()` IS the element)
      return el
    }
  }
  return { Picker: FakePicker }
})

vi.mock('@emoji-mart/data', () => ({ default: {} }))

describe('EmojiPicker', () => {
  let EmojiPicker

  beforeEach(async () => {
    // Import fresh for each test to reset lazy state
    const mod = await import('../../../src/components/shared/EmojiPicker')
    EmojiPicker = mod.default
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('opens the picker on trigger click and mounts the lazy-loaded picker', async () => {
    const onSelect = vi.fn()
    render(
      <EmojiPicker onSelect={onSelect}>
        <button>Pick Emoji</button>
      </EmojiPicker>
    )

    // Picker should not be visible initially
    expect(screen.queryByText('Clear')).not.toBeInTheDocument()

    // Click trigger to open
    await act(async () => {
      screen.getByText('Pick Emoji').click()
    })

    // Clear button should be visible
    expect(screen.getByText('Clear')).toBeInTheDocument()
  })

  it('clicking Clear fires onSelect(null) and closes the picker', async () => {
    const onSelect = vi.fn()
    render(
      <EmojiPicker onSelect={onSelect}>
        <button>Pick Emoji</button>
      </EmojiPicker>
    )

    // Open
    await act(async () => {
      screen.getByText('Pick Emoji').click()
    })

    // Click Clear
    await act(async () => {
      screen.getByText('Clear').click()
    })

    expect(onSelect).toHaveBeenCalledWith(null)
    // Picker should be closed
    expect(screen.queryByText('Clear')).not.toBeInTheDocument()
  })

  it('Escape closes the picker without propagating to parent', async () => {
    const onSelect = vi.fn()
    const parentHandler = vi.fn()
    document.addEventListener('keydown', parentHandler)

    render(
      <EmojiPicker onSelect={onSelect}>
        <button>Pick Emoji</button>
      </EmojiPicker>
    )

    // Open
    await act(async () => {
      screen.getByText('Pick Emoji').click()
    })

    expect(screen.getByText('Clear')).toBeInTheDocument()

    // Press Escape
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    })

    // Picker should be closed
    expect(screen.queryByText('Clear')).not.toBeInTheDocument()

    // Parent handler should NOT have received the event (stopPropagation in capture)
    // Note: since we dispatch on document and listen on document, the capture handler
    // runs first and stops propagation — the bubble-phase listener doesn't fire.
    expect(parentHandler).not.toHaveBeenCalled()

    document.removeEventListener('keydown', parentHandler)
  })
})
