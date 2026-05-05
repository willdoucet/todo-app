import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'
import { api } from '../../../src/lib/api'
import FoodItemsView from '../../../src/components/mealboard/FoodItemsView'
import { UndoToastProvider } from '../../../src/components/shared/UndoToast'

vi.mock('../../../src/lib/api', () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() } }))

function renderWithProviders(ui) {
  return render(<UndoToastProvider>{ui}</UndoToastProvider>)
}

describe('FoodItemsView loading behavior', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not render spinner when food items load within 200ms', async () => {
    // API resolves instantly
    api.get.mockResolvedValue({ data: [{ id: 1, name: 'Apple', category: 'fruit' }] })

    await act(async () => {
      renderWithProviders(<FoodItemsView />)
    })

    // Flush microtasks
    await act(async () => {
      await Promise.resolve()
    })

    // No spinner should be visible
    expect(document.querySelectorAll('.animate-spin').length).toBe(0)
  })

  it('shows spinner after 200ms on slow load', async () => {
    // API never resolves
    api.get.mockImplementation(() => new Promise(() => {}))

    await act(async () => {
      renderWithProviders(<FoodItemsView />)
    })

    // Initially no spinner
    expect(document.querySelectorAll('.animate-spin').length).toBe(0)

    // Advance past the 200ms delay
    await act(async () => {
      vi.advanceTimersByTime(200)
    })

    // Spinner should now be visible
    expect(document.querySelectorAll('.animate-spin').length).toBe(1)
  })
})
