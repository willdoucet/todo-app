import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import axios from 'axios'
import MealPlannerView from '../../../src/components/mealboard/MealPlannerView'

vi.mock('axios')

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

function mockAxios() {
  axios.get.mockImplementation((url) => {
    if (url.includes('app-settings')) return Promise.resolve(mockSettingsResponse)
    return Promise.resolve(mockEmptyArray)
  })
}

describe('Jump to Current Week button', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.setItem('mealboard_welcome_dismissed', '1')
    mockAxios()
  })

  afterEach(() => {
    vi.useRealTimers()
    localStorage.clear()
  })

  it('is not rendered when the displayed week contains today', async () => {
    await act(async () => {
      renderWithRouter(<MealPlannerView />)
    })

    expect(screen.queryByText('Jump to Current Week')).not.toBeInTheDocument()
  })

  it('appears after navigating to a different week', async () => {
    await act(async () => {
      renderWithRouter(<MealPlannerView />)
    })

    // Navigate to previous week
    const prevButtons = screen.getAllByLabelText('Previous week')
    await act(async () => {
      prevButtons[0].click()
    })

    expect(screen.queryAllByText('Jump to Current Week').length).toBeGreaterThan(0)
  })

  it('disappears after clicking it to return to the current week', async () => {
    await act(async () => {
      renderWithRouter(<MealPlannerView />)
    })

    // Navigate away from the current week
    const prevButtons = screen.getAllByLabelText('Previous week')
    await act(async () => {
      prevButtons[0].click()
    })

    // The button should now be visible — click any instance to go back
    const jumpButtons = screen.getAllByText('Jump to Current Week')
    expect(jumpButtons.length).toBeGreaterThan(0)

    await act(async () => {
      jumpButtons[0].click()
    })

    // Should be hidden again
    expect(screen.queryByText('Jump to Current Week')).not.toBeInTheDocument()
  })
})
