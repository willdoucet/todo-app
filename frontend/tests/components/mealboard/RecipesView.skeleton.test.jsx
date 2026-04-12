import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import axios from 'axios'

vi.mock('axios')

// Mock RecipeDetailDrawer to avoid unrelated rendering.
vi.mock('../../../src/components/mealboard/RecipeDetailDrawer', () => ({
  default: () => null,
}))

// Import after mocks are set up
const { default: RecipesView } = await import('../../../src/components/mealboard/RecipesView')

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('RecipesView skeleton behavior', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not render skeleton placeholders when recipes load within 200ms', async () => {
    // API resolves instantly
    axios.get.mockResolvedValue({ data: [{ id: 1, name: 'Test Recipe', tags: [], is_favorite: false }] })

    await act(async () => {
      renderWithRouter(<RecipesView />)
    })

    // Flush microtasks for the resolved promise
    await act(async () => {
      await Promise.resolve()
    })

    // No skeleton pulse elements should be visible
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBe(0)
  })

  it('renders exactly 5 grid skeleton cards after 200ms on slow load', async () => {
    // API never resolves
    axios.get.mockImplementation(() => new Promise(() => {}))

    await act(async () => {
      renderWithRouter(<RecipesView />)
    })

    // Initially no skeletons (delay hasn't elapsed)
    expect(document.querySelectorAll('.animate-pulse').length).toBe(0)

    // Advance past the 200ms delay
    await act(async () => {
      vi.advanceTimersByTime(200)
    })

    // Should show exactly 5 skeleton cards (one grid row)
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBe(5)
  })
})
