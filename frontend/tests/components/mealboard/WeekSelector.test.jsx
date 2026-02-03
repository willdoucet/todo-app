import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import WeekSelector from '../../../src/components/mealboard/WeekSelector'

const createWeekDates = (startDate) => {
  const dates = []
  for (let i = 0; i < 7; i++) {
    const date = new Date(startDate)
    date.setDate(date.getDate() + i)
    dates.push(date)
  }
  return dates
}

describe('WeekSelector', () => {
  const mockOnPrevWeek = vi.fn()
  const mockOnNextWeek = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays the week range within same month', () => {
    const weekDates = createWeekDates(new Date(2025, 0, 20))
    render(
      <WeekSelector
        weekDates={weekDates}
        onPrevWeek={mockOnPrevWeek}
        onNextWeek={mockOnNextWeek}
      />
    )

    expect(screen.getByText('Jan 20 - 26')).toBeInTheDocument()
  })

  it('displays the week range spanning two months', () => {
    const weekDates = createWeekDates(new Date(2025, 0, 27))
    render(
      <WeekSelector
        weekDates={weekDates}
        onPrevWeek={mockOnPrevWeek}
        onNextWeek={mockOnNextWeek}
      />
    )

    expect(screen.getByText('Jan 27 - Feb 2')).toBeInTheDocument()
  })

  it('calls onPrevWeek when clicking previous button', async () => {
    const user = userEvent.setup()
    const weekDates = createWeekDates(new Date(2025, 0, 20))
    render(
      <WeekSelector
        weekDates={weekDates}
        onPrevWeek={mockOnPrevWeek}
        onNextWeek={mockOnNextWeek}
      />
    )

    await user.click(screen.getByLabelText('Previous week'))
    expect(mockOnPrevWeek).toHaveBeenCalledTimes(1)
  })

  it('calls onNextWeek when clicking next button', async () => {
    const user = userEvent.setup()
    const weekDates = createWeekDates(new Date(2025, 0, 20))
    render(
      <WeekSelector
        weekDates={weekDates}
        onPrevWeek={mockOnPrevWeek}
        onNextWeek={mockOnNextWeek}
      />
    )

    await user.click(screen.getByLabelText('Next week'))
    expect(mockOnNextWeek).toHaveBeenCalledTimes(1)
  })

  it('renders navigation buttons', () => {
    const weekDates = createWeekDates(new Date(2025, 0, 20))
    render(
      <WeekSelector
        weekDates={weekDates}
        onPrevWeek={mockOnPrevWeek}
        onNextWeek={mockOnNextWeek}
      />
    )

    expect(screen.getByLabelText('Previous week')).toBeInTheDocument()
    expect(screen.getByLabelText('Next week')).toBeInTheDocument()
  })
})
