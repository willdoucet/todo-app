import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarHeader from '../../../src/components/calendar/CalendarHeader'

const defaultProps = {
  currentDate: new Date(2026, 1, 7), // Feb 7, 2026 (Saturday)
  viewMode: 'month',
  onPrev: vi.fn(),
  onNext: vi.fn(),
  onToday: vi.fn(),
  onViewChange: vi.fn(),
}

function renderHeader(overrides = {}) {
  const props = { ...defaultProps, ...overrides }
  // Reset mocks
  props.onPrev.mockClear()
  props.onNext.mockClear()
  props.onToday.mockClear()
  props.onViewChange.mockClear()
  return render(<CalendarHeader {...props} />)
}

describe('CalendarHeader', () => {
  describe('period label', () => {
    it('shows month and year for month view', () => {
      renderHeader({ viewMode: 'month' })
      expect(screen.getByText('February 2026')).toBeInTheDocument()
    })

    it('shows date range for week view', () => {
      renderHeader({ viewMode: 'week' })
      // Feb 7 is Saturday, week is Feb 1–7, 2026
      expect(screen.getByText(/Feb 1/)).toBeInTheDocument()
    })

    it('shows full date for day view', () => {
      renderHeader({ viewMode: 'day' })
      // Should include weekday, month, day, year
      expect(screen.getByText(/Sat.*February.*7.*2026/)).toBeInTheDocument()
    })
  })

  describe('navigation buttons', () => {
    it('calls onPrev when Previous button is clicked', async () => {
      const user = userEvent.setup()
      renderHeader()
      await user.click(screen.getByLabelText('Previous'))
      expect(defaultProps.onPrev).toHaveBeenCalledOnce()
    })

    it('calls onNext when Next button is clicked', async () => {
      const user = userEvent.setup()
      renderHeader()
      await user.click(screen.getByLabelText('Next'))
      expect(defaultProps.onNext).toHaveBeenCalledOnce()
    })

    it('calls onToday when Today button is clicked', async () => {
      const user = userEvent.setup()
      renderHeader()
      await user.click(screen.getByText('Today'))
      expect(defaultProps.onToday).toHaveBeenCalledOnce()
    })
  })

  describe('view mode toggle', () => {
    it('renders month, week, and day buttons', () => {
      renderHeader()
      expect(screen.getByText('month')).toBeInTheDocument()
      expect(screen.getByText('week')).toBeInTheDocument()
      expect(screen.getByText('day')).toBeInTheDocument()
    })

    it('calls onViewChange with mode when clicked', async () => {
      const user = userEvent.setup()
      renderHeader({ viewMode: 'month' })
      await user.click(screen.getByText('week'))
      expect(defaultProps.onViewChange).toHaveBeenCalledWith('week')
    })

    it('highlights the active view mode', () => {
      renderHeader({ viewMode: 'week' })
      const weekBtn = screen.getByText('week')
      expect(weekBtn.className).toMatch(/bg-terracotta-500/)
    })

    it('does not highlight inactive view modes', () => {
      renderHeader({ viewMode: 'week' })
      const monthBtn = screen.getByText('month')
      expect(monthBtn.className).not.toMatch(/bg-terracotta-500/)
    })
  })
})
