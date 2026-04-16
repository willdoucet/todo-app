import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { UndoToastProvider, useUndoToast } from '../../../src/components/shared/UndoToast'

// Stub ItemIcon which requires more context
vi.mock('../../../src/components/mealboard/ItemIcon', () => ({
  default: () => <span data-testid="item-icon" />,
}))

// Headless UI v2 uses getAnimations() to detect transition end — JSDOM has no
// real CSS engine so transitions never "finish" and elements stay mounted.
// Mock the Transition component to render children synchronously.
vi.mock('@headlessui/react', () => ({
  Transition: ({ show, children }) => (show ? <div>{children}</div> : null),
  Dialog: Object.assign(
    ({ children }) => <div>{children}</div>,
    { Title: ({ children }) => <h2>{children}</h2>, Panel: ({ children }) => <div>{children}</div> }
  ),
}))

const UNDO_WINDOW_MS = 15_000

const mockItem = { id: 1, name: 'Banana', item_type: 'food_item' }

function TestHarness({ onUndo, onExpire } = {}) {
  const { show, hide } = useUndoToast()
  return (
    <>
      <button
        data-testid="show-toast"
        onClick={() =>
          show({
            item: mockItem,
            undoToken: 'tok-1',
            onUndo: onUndo || vi.fn(),
            onExpire: onExpire || undefined,
          })
        }
      />
      <button data-testid="hide-toast" onClick={hide} />
    </>
  )
}

function renderWithProvider(props = {}) {
  return render(
    <UndoToastProvider>
      <TestHarness {...props} />
    </UndoToastProvider>
  )
}

describe('UndoToast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('auto-hides after 15s', async () => {
    renderWithProvider()

    await act(async () => {
      screen.getByTestId('show-toast').click()
    })

    expect(screen.getByText('Food item deleted')).toBeInTheDocument()

    // Advance past the 15s window
    await act(async () => {
      vi.advanceTimersByTime(UNDO_WINDOW_MS)
    })

    // With mocked Transition, element is removed immediately when show=false
    expect(screen.queryByText('Food item deleted')).not.toBeInTheDocument()
  })

  it('fires onExpire once on auto-hide', async () => {
    const onExpire = vi.fn()
    renderWithProvider({ onExpire })

    await act(async () => {
      screen.getByTestId('show-toast').click()
    })

    await act(async () => {
      vi.advanceTimersByTime(UNDO_WINDOW_MS)
    })

    expect(onExpire).toHaveBeenCalledTimes(1)
  })

  it('hide() before timer fires cancels the timer and does not call onExpire', async () => {
    const onExpire = vi.fn()
    renderWithProvider({ onExpire })

    await act(async () => {
      screen.getByTestId('show-toast').click()
    })

    // Hide manually at 5s
    await act(async () => {
      vi.advanceTimersByTime(5000)
    })
    await act(async () => {
      screen.getByTestId('hide-toast').click()
    })

    // Advance past what would have been the expiry
    await act(async () => {
      vi.advanceTimersByTime(UNDO_WINDOW_MS)
    })

    expect(onExpire).not.toHaveBeenCalled()
  })

  it('dismisses immediately when tab returns after expiry (visibilitychange catch-up)', async () => {
    const onExpire = vi.fn()
    renderWithProvider({ onExpire })

    await act(async () => {
      screen.getByTestId('show-toast').click()
    })

    expect(screen.getByText('Food item deleted')).toBeInTheDocument()

    // Simulate time passing beyond the window without advancing the timer queue
    const now = Date.now()
    vi.spyOn(Date, 'now').mockReturnValue(now + UNDO_WINDOW_MS + 1000)

    // Simulate tab becoming visible
    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      writable: true,
      configurable: true,
    })
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    expect(onExpire).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('Food item deleted')).not.toBeInTheDocument()

    vi.restoreAllMocks()
  })
})
