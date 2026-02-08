import { render, screen, fireEvent } from '@testing-library/react'
import TimeGrid from '../../../src/components/calendar/TimeGrid'

const mockFamilyMembers = [
  { id: 1, name: 'Everyone', is_system: true, color: '#D97452' },
  { id: 2, name: 'Alice', is_system: false, color: '#3B82F6' },
]

const mockTimedEvent = {
  id: 1,
  title: 'Team meeting',
  date: '2026-02-07',
  start_time: '09:00',
  end_time: '10:00',
  all_day: false,
  assigned_to: 2,
  family_member: mockFamilyMembers[1],
}

const mockAllDayEvent = {
  id: 2,
  title: 'School holiday',
  date: '2026-02-07',
  start_time: null,
  end_time: null,
  all_day: true,
  assigned_to: null,
  family_member: null,
}

describe('TimeGrid', () => {
  describe('hour labels', () => {
    it('renders hour labels from 6 AM to 10 PM', () => {
      render(
        <TimeGrid
          events={[]}
          familyMembers={mockFamilyMembers}
          showHourLabels={true}
        />
      )
      expect(screen.getByText('6 AM')).toBeInTheDocument()
      expect(screen.getByText('12 PM')).toBeInTheDocument()
      expect(screen.getByText('10 PM')).toBeInTheDocument()
    })

    it('hides hour labels when showHourLabels is false', () => {
      render(
        <TimeGrid
          events={[]}
          familyMembers={mockFamilyMembers}
          showHourLabels={false}
        />
      )
      expect(screen.queryByText('6 AM')).not.toBeInTheDocument()
    })
  })

  describe('event rendering', () => {
    it('renders timed events as positioned blocks', () => {
      render(
        <TimeGrid
          events={[mockTimedEvent]}
          familyMembers={mockFamilyMembers}
        />
      )
      expect(screen.getByText('Team meeting')).toBeInTheDocument()
      expect(screen.getByText('09:00–10:00')).toBeInTheDocument()
    })

    it('sets title attribute with event details', () => {
      render(
        <TimeGrid
          events={[mockTimedEvent]}
          familyMembers={mockFamilyMembers}
        />
      )
      expect(screen.getByTitle('Team meeting (09:00–10:00)')).toBeInTheDocument()
    })

    it('skips all-day events', () => {
      render(
        <TimeGrid
          events={[mockAllDayEvent]}
          familyMembers={mockFamilyMembers}
        />
      )
      expect(screen.queryByText('School holiday')).not.toBeInTheDocument()
    })

    it('renders multiple timed events', () => {
      const events = [
        mockTimedEvent,
        {
          id: 3,
          title: 'Lunch',
          date: '2026-02-07',
          start_time: '12:00',
          end_time: '13:00',
          all_day: false,
          assigned_to: null,
          family_member: null,
        },
      ]
      render(
        <TimeGrid events={events} familyMembers={mockFamilyMembers} />
      )
      expect(screen.getByText('Team meeting')).toBeInTheDocument()
      expect(screen.getByText('Lunch')).toBeInTheDocument()
    })
  })

  describe('slot click — quick-add choice', () => {
    it('shows "New Task" and "New Event" buttons on grid click', () => {
      const { container } = render(
        <TimeGrid
          events={[]}
          familyMembers={mockFamilyMembers}
          onQuickAddTask={vi.fn()}
          onQuickAddEvent={vi.fn()}
        />
      )
      const gridArea = container.querySelector('.cursor-pointer')
      const rect = { top: 0, left: 0, width: 500, height: 1020 }
      vi.spyOn(gridArea, 'getBoundingClientRect').mockReturnValue(rect)

      fireEvent.click(gridArea, { clientY: 0 })
      expect(screen.getByText('New Task')).toBeInTheDocument()
      expect(screen.getByText('New Event')).toBeInTheDocument()
    })

    it('calls onQuickAddTask with time string when "New Task" is clicked', async () => {
      const onQuickAddTask = vi.fn()
      const { container } = render(
        <TimeGrid
          events={[]}
          familyMembers={mockFamilyMembers}
          onQuickAddTask={onQuickAddTask}
          onQuickAddEvent={vi.fn()}
        />
      )
      const gridArea = container.querySelector('.cursor-pointer')
      const rect = { top: 0, left: 0, width: 500, height: 1020 }
      vi.spyOn(gridArea, 'getBoundingClientRect').mockReturnValue(rect)

      fireEvent.click(gridArea, { clientY: 0 })
      fireEvent.click(screen.getByText('New Task'))
      expect(onQuickAddTask).toHaveBeenCalledWith('06:00')
    })

    it('calls onQuickAddEvent with time string when "New Event" is clicked', async () => {
      const onQuickAddEvent = vi.fn()
      const { container } = render(
        <TimeGrid
          events={[]}
          familyMembers={mockFamilyMembers}
          onQuickAddTask={vi.fn()}
          onQuickAddEvent={onQuickAddEvent}
        />
      )
      const gridArea = container.querySelector('.cursor-pointer')
      const rect = { top: 0, left: 0, width: 500, height: 1020 }
      vi.spyOn(gridArea, 'getBoundingClientRect').mockReturnValue(rect)

      fireEvent.click(gridArea, { clientY: 0 })
      fireEvent.click(screen.getByText('New Event'))
      expect(onQuickAddEvent).toHaveBeenCalledWith('06:00')
    })

    it('does not show quick-add when callbacks are not provided', () => {
      const { container } = render(
        <TimeGrid events={[]} familyMembers={mockFamilyMembers} />
      )
      const gridArea = container.querySelector('.cursor-pointer')
      fireEvent.click(gridArea)
      expect(screen.queryByText('New Task')).not.toBeInTheDocument()
      expect(screen.queryByText('New Event')).not.toBeInTheDocument()
    })
  })

  describe('event click — edit', () => {
    it('calls onEditEvent when event block is clicked', () => {
      const onEditEvent = vi.fn()
      render(
        <TimeGrid
          events={[mockTimedEvent]}
          familyMembers={mockFamilyMembers}
          onEditEvent={onEditEvent}
        />
      )
      fireEvent.click(screen.getByText('Team meeting'))
      expect(onEditEvent).toHaveBeenCalledWith(mockTimedEvent)
    })

    it('stopPropagation: event click does not trigger quick-add', () => {
      const onEditEvent = vi.fn()
      const onQuickAddTask = vi.fn()
      const onQuickAddEvent = vi.fn()
      render(
        <TimeGrid
          events={[mockTimedEvent]}
          familyMembers={mockFamilyMembers}
          onEditEvent={onEditEvent}
          onQuickAddTask={onQuickAddTask}
          onQuickAddEvent={onQuickAddEvent}
        />
      )
      fireEvent.click(screen.getByText('Team meeting'))
      expect(onEditEvent).toHaveBeenCalled()
      // Quick-add popup should NOT appear
      expect(screen.queryByText('New Task')).not.toBeInTheDocument()
    })

    it('adds cursor-pointer to event blocks when onEditEvent is provided', () => {
      render(
        <TimeGrid
          events={[mockTimedEvent]}
          familyMembers={mockFamilyMembers}
          onEditEvent={vi.fn()}
        />
      )
      const block = screen.getByTitle('Team meeting (09:00–10:00)')
      expect(block).toHaveClass('cursor-pointer')
    })
  })

  describe('empty state', () => {
    it('renders the grid even with no events', () => {
      const { container } = render(
        <TimeGrid events={[]} familyMembers={mockFamilyMembers} />
      )
      expect(screen.getByText('6 AM')).toBeInTheDocument()
      // Grid area should still be present
      expect(container.querySelector('.cursor-pointer')).toBeInTheDocument()
    })
  })
})
