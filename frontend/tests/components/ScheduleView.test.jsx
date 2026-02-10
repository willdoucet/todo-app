import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ScheduleView from '../../src/components/ScheduleView'

describe('ScheduleView', () => {
  // Wednesday so all responsibilities with weekday frequency show up
  const wednesday = new Date('2026-02-04T12:00:00')

  const familyMembers = [
    { id: 1, name: 'Alice', photo_url: null, is_system: false },
  ]

  const defaultProps = {
    familyMembers,
    responsibilities: [],
    completions: [],
    currentDate: wednesday,
    isLoading: false,
    onToggleCompletion: vi.fn(),
    onPreviousDay: vi.fn(),
    onNextDay: vi.fn(),
    everyoneID: 99,
  }

  // Helper: get the desktop view container (hidden on mobile via sm:flex)
  const getDesktopView = () => {
    // Desktop view is the div with class "hidden sm:flex..."
    return document.querySelector('.hidden.sm\\:flex')
  }

  describe('category filter', () => {
    const responsibilities = [
      {
        id: 1,
        title: 'Morning-only task',
        categories: ['MORNING'],
        assigned_to: 1,
        frequency: ['Wednesday'],
        icon_url: null,
      },
      {
        id: 2,
        title: 'Evening-only task',
        categories: ['EVENING'],
        assigned_to: 1,
        frequency: ['Wednesday'],
        icon_url: null,
      },
      {
        id: 3,
        title: 'Multi-category task',
        categories: ['MORNING', 'EVENING'],
        assigned_to: 1,
        frequency: ['Wednesday'],
        icon_url: null,
      },
    ]

    it('shows all categories when no filter is active', () => {
      render(<ScheduleView {...defaultProps} responsibilities={responsibilities} />)

      const desktop = getDesktopView()
      const view = within(desktop)

      expect(view.getByText('Morning-only task')).toBeInTheDocument()
      expect(view.getByText('Evening-only task')).toBeInTheDocument()
      // Multi-category task appears under both Morning and Evening headers
      expect(view.getAllByText('Multi-category task')).toHaveLength(2)
    })

    it('clicking Morning filter hides Evening-only items and shows multi-cat task once', async () => {
      const user = userEvent.setup()
      render(<ScheduleView {...defaultProps} responsibilities={responsibilities} />)

      // Click the Morning filter pill (inside the filter group)
      const filterGroup = screen.getByRole('group', { name: /filter by category/i })
      await user.click(within(filterGroup).getByRole('button', { name: /Morning/i }))

      const desktop = getDesktopView()
      const view = within(desktop)

      // Morning-only task should still be visible
      expect(view.getByText('Morning-only task')).toBeInTheDocument()

      // Evening-only task should be hidden
      expect(view.queryByText('Evening-only task')).not.toBeInTheDocument()

      // Multi-category task should appear exactly once (under Morning only, not Evening)
      expect(view.getAllByText('Multi-category task')).toHaveLength(1)
    })

    it('clicking Evening filter hides Morning-only items and shows multi-cat task once', async () => {
      const user = userEvent.setup()
      render(<ScheduleView {...defaultProps} responsibilities={responsibilities} />)

      const filterGroup = screen.getByRole('group', { name: /filter by category/i })
      await user.click(within(filterGroup).getByRole('button', { name: /Evening/i }))

      const desktop = getDesktopView()
      const view = within(desktop)

      // Evening-only task should be visible
      expect(view.getByText('Evening-only task')).toBeInTheDocument()

      // Morning-only task should be hidden
      expect(view.queryByText('Morning-only task')).not.toBeInTheDocument()

      // Multi-category task should appear exactly once (under Evening only)
      expect(view.getAllByText('Multi-category task')).toHaveLength(1)
    })

    it('toggling filter off returns to showing all categories', async () => {
      const user = userEvent.setup()
      render(<ScheduleView {...defaultProps} responsibilities={responsibilities} />)

      const filterGroup = screen.getByRole('group', { name: /filter by category/i })
      const desktop = getDesktopView()
      const view = within(desktop)

      // Click Morning to filter
      await user.click(within(filterGroup).getByRole('button', { name: /Morning/i }))
      expect(view.queryByText('Evening-only task')).not.toBeInTheDocument()

      // Click Morning again to toggle off (return to All)
      await user.click(within(filterGroup).getByRole('button', { name: /Morning/i }))
      expect(view.getByText('Evening-only task')).toBeInTheDocument()
      expect(view.getAllByText('Multi-category task')).toHaveLength(2)
    })
  })
})
