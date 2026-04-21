/**
 * Regression tests for the single-delete invariant:
 * deleting ONE meal on the weekly grid removes EXACTLY ONE meal card from the grid.
 *
 * Filed 2026-04-19 after a user-reported bug ("deleting a mealboard item caused
 * two food items to disappear") that couldn't be reproduced. We lock in the
 * invariant so any future regression surfaces in CI instead of the next user
 * session.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import axios from 'axios'
import MealPlannerView from '../../../src/components/mealboard/MealPlannerView'

vi.mock('axios')
vi.mock('../../../src/components/mealboard/ItemDetailDrawer', () => ({
  default: () => null,
}))

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

function today() {
  return new Date()
}

function isoDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

const DINNER_SLOT = {
  id: 10,
  name: 'Dinner',
  color: '#E8927C',
  icon: '🍽',
  default_participants: [],
  is_active: true,
}

function bananaEntry(id) {
  return {
    id,
    date: isoDate(today()),
    meal_slot_type_id: DINNER_SLOT.id,
    item_id: 100 + id,
    item: {
      id: 100 + id,
      name: `Banana ${id}`,
      item_type: 'food_item',
      icon_emoji: '🍌',
      icon_url: null,
      tags: [],
      is_favorite: false,
      recipe_detail: null,
      food_item_detail: { category: 'fruit', shopping_quantity: 1, shopping_unit: 'each' },
    },
    custom_meal_name: null,
    was_cooked: false,
    participants: [],
    sort_order: id,
    created_at: '2026-04-18T00:00:00Z',
  }
}

const mockSettingsResponse = { data: { week_start_day: 'monday', slot_types: [] } }

function mockAxiosWithEntries(entries) {
  axios.get.mockImplementation((url) => {
    if (url.includes('app-settings')) return Promise.resolve(mockSettingsResponse)
    if (url.includes('meal-slot-types')) return Promise.resolve({ data: [DINNER_SLOT] })
    if (url.includes('family-members')) return Promise.resolve({ data: [] })
    if (url.includes('items')) return Promise.resolve({ data: [] })
    if (url.includes('meal-entries')) return Promise.resolve({ data: entries })
    return Promise.resolve({ data: [] })
  })
}

describe('MealPlannerView — single-delete invariant (regression)', () => {
  beforeEach(() => {
    localStorage.setItem('mealboard_welcome_dismissed', '1')
    // Run on desktop breakpoint so SwimlaneGrid renders (MobileDayView would
    // only show one day's slot at a time).
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1280 })
  })

  afterEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('deleting one meal removes exactly one from the grid (soft-delete + undo path)', async () => {
    const entries = [bananaEntry(1), bananaEntry(2), bananaEntry(3)]
    mockAxiosWithEntries(entries)
    // The soft-delete endpoint returns the undo token. With the undo flow, the
    // deleted entry's MealCard is replaced in-place by an UndoMealCard — the
    // underlying mealEntries state still contains the row, and only live
    // entries not in pendingDeletes should render as MealCards.
    axios.delete.mockResolvedValue({
      data: {
        entry: { ...entries[1], soft_hidden_at: '2026-04-18T00:00:05Z' },
        undo_token: 'tok-2',
        expires_at: '2026-04-18T00:00:10Z',
      },
    })

    await act(async () => {
      renderWithRouter(<MealPlannerView />)
    })

    // Sanity: all three Bananas render as live MealCards
    expect(screen.getByText('Banana 1')).toBeInTheDocument()
    expect(screen.getByText('Banana 2')).toBeInTheDocument()
    expect(screen.getByText('Banana 3')).toBeInTheDocument()

    // Delete the middle one
    const deleteButtons = screen.getAllByLabelText('Delete meal')
    expect(deleteButtons).toHaveLength(3)
    await act(async () => {
      deleteButtons[1].click()
    })

    // Banana 1 and Banana 3 still render as live MealCards.
    expect(screen.getByText('Banana 1')).toBeInTheDocument()
    expect(screen.getByText('Banana 3')).toBeInTheDocument()

    // Banana 2 now renders as an UndoMealCard in the same cell. The name
    // appears inside the UndoMealCard's aria-label; the struck-through name
    // is a sibling span.
    const undoCard = screen.getByRole('button', { name: /Undo deletion of Banana 2/ })
    expect(undoCard).toBeInTheDocument()

    // Exactly ONE undo card — not two, not three.
    expect(screen.getAllByRole('button', { name: /Undo deletion of/ })).toHaveLength(1)

    // The backend was hit for entry 2 only.
    expect(axios.delete).toHaveBeenCalledTimes(1)
    expect(axios.delete).toHaveBeenCalledWith(expect.stringContaining('/meal-entries/2'))
  })

  it('deleting one meal removes exactly one (mixed-version fallback: no undo_token)', async () => {
    const entries = [bananaEntry(1), bananaEntry(2)]
    mockAxiosWithEntries(entries)
    // Old backend shape — no undo_token. MealCard falls back to hard-delete UX:
    // the entry is removed from mealEntries immediately, no UndoMealCard.
    axios.delete.mockResolvedValue({ data: { ...entries[0] } })

    await act(async () => {
      renderWithRouter(<MealPlannerView />)
    })

    expect(screen.getByText('Banana 1')).toBeInTheDocument()
    expect(screen.getByText('Banana 2')).toBeInTheDocument()

    const deleteButtons = screen.getAllByLabelText('Delete meal')
    await act(async () => {
      deleteButtons[0].click()
    })

    // Banana 1 is gone, Banana 2 survives.
    expect(screen.queryByText('Banana 1')).not.toBeInTheDocument()
    expect(screen.getByText('Banana 2')).toBeInTheDocument()
    // No undo card in the fallback path.
    expect(screen.queryByRole('button', { name: /Undo deletion of/ })).not.toBeInTheDocument()
  })

  it('deleting two meals back-to-back shows BOTH undo cards (F3 regression)', async () => {
    const entries = [bananaEntry(1), bananaEntry(2), bananaEntry(3)]
    mockAxiosWithEntries(entries)

    let tokenCounter = 0
    axios.delete.mockImplementation(() => {
      tokenCounter += 1
      return Promise.resolve({
        data: {
          entry: entries[tokenCounter - 1],
          undo_token: `tok-${tokenCounter}`,
          expires_at: '2026-04-18T00:00:10Z',
        },
      })
    })

    await act(async () => {
      renderWithRouter(<MealPlannerView />)
    })

    const deleteButtons = screen.getAllByLabelText('Delete meal')
    // Fire two rapid deletes on Banana 1 and Banana 2.
    await act(async () => {
      deleteButtons[0].click()
      deleteButtons[1].click()
    })

    // Both undo cards present — pre-F3-fix, the first would have been
    // stuck because its 5s purge timer was cancelled by the second delete's
    // state update.
    expect(screen.getByRole('button', { name: /Undo deletion of Banana 1/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Undo deletion of Banana 2/ })).toBeInTheDocument()
    // Banana 3 is untouched.
    expect(screen.getByText('Banana 3')).toBeInTheDocument()
  })
})
