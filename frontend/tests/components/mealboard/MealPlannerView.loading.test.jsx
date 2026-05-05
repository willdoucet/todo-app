import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { api } from '../../../src/lib/api'
import MealPlannerView from '../../../src/components/mealboard/MealPlannerView'

vi.mock('../../../src/lib/api', () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() } }))

// Stub child components that aren't relevant to loading behavior
vi.mock('../../../src/components/mealboard/RecipeDetailDrawer', () => ({
  default: () => null,
}))

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

const mockSettingsResponse = {
  data: { week_start_day: 'monday', slot_types: [] },
}
const mockEmptyArray = { data: [] }

describe('MealPlannerView loading behavior', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.setItem('mealboard_welcome_dismissed', '1')
  })
  afterEach(() => {
    vi.useRealTimers()
    localStorage.clear()
  })

  it('renders content immediately without spinner on fast load', async () => {
    // API resolves instantly
    api.get.mockResolvedValue(mockEmptyArray)
    api.get.mockImplementation((url) => {
      if (url.includes('app-settings')) return Promise.resolve(mockSettingsResponse)
      return Promise.resolve(mockEmptyArray)
    })

    await act(async () => {
      renderWithRouter(<MealPlannerView />)
    })

    // No spinner should be visible — content renders from frame zero
    const spinners = document.querySelectorAll('.animate-spin')
    expect(spinners.length).toBe(0)
  })

  it('shows delayed spinner overlay after 200ms on slow load', async () => {
    // API never resolves — simulates slow network
    api.get.mockImplementation(() => new Promise(() => {}))

    await act(async () => {
      renderWithRouter(<MealPlannerView />)
    })

    // Initially no spinner (delay hasn't elapsed)
    expect(document.querySelectorAll('.animate-spin').length).toBe(0)

    // Advance past the 200ms delay
    await act(async () => {
      vi.advanceTimersByTime(200)
    })

    // Spinner overlay should now be visible
    expect(document.querySelectorAll('.animate-spin').length).toBe(1)
  })
})
