import { render, screen, fireEvent } from '@testing-library/react'
import CalendarItem from '../../../src/components/calendar/CalendarItem'

const mockTask = {
  id: 1,
  title: 'Buy groceries',
  completed: false,
  assigned_to: 2,
}

const mockCompletedTask = {
  id: 2,
  title: 'Done task',
  completed: true,
  assigned_to: 2,
}

const mockEvent = {
  id: 10,
  title: 'Team meeting',
  start_time: '09:00',
  end_time: '10:00',
  all_day: false,
  assigned_to: 2,
}

const mockMember = { id: 2, name: 'Alice', is_system: false, color: '#3B82F6' }

describe('CalendarItem', () => {
  describe('rendering', () => {
    it('renders task title', () => {
      render(<CalendarItem item={mockTask} type="task" member={mockMember} />)
      expect(screen.getByText('Buy groceries')).toBeInTheDocument()
    })

    it('renders event title with time', () => {
      render(<CalendarItem item={mockEvent} type="event" member={mockMember} />)
      expect(screen.getByText('Team meeting')).toBeInTheDocument()
      expect(screen.getByText('09:00–10:00')).toBeInTheDocument()
    })

    it('renders completed task with line-through style', () => {
      const { container } = render(
        <CalendarItem item={mockCompletedTask} type="task" member={mockMember} />
      )
      expect(container.firstChild).toHaveClass('line-through')
    })
  })

  describe('click handler', () => {
    it('calls onClick with item and type when row is clicked', () => {
      const onClick = vi.fn()
      render(
        <CalendarItem item={mockTask} type="task" member={mockMember} onClick={onClick} />
      )
      fireEvent.click(screen.getByText('Buy groceries'))
      expect(onClick).toHaveBeenCalledWith(mockTask, 'task')
    })

    it('calls onClick for events', () => {
      const onClick = vi.fn()
      render(
        <CalendarItem item={mockEvent} type="event" member={mockMember} onClick={onClick} />
      )
      fireEvent.click(screen.getByText('Team meeting'))
      expect(onClick).toHaveBeenCalledWith(mockEvent, 'event')
    })

    it('adds cursor-pointer class when onClick is provided', () => {
      const { container } = render(
        <CalendarItem item={mockTask} type="task" member={mockMember} onClick={vi.fn()} />
      )
      expect(container.firstChild).toHaveClass('cursor-pointer')
    })

    it('does not add cursor-pointer when onClick is not provided', () => {
      const { container } = render(
        <CalendarItem item={mockTask} type="task" member={mockMember} />
      )
      expect(container.firstChild).not.toHaveClass('cursor-pointer')
    })
  })

  describe('toggle complete', () => {
    it('calls onToggleComplete with task when checkbox is clicked', () => {
      const onToggleComplete = vi.fn()
      const onClick = vi.fn()
      render(
        <CalendarItem
          item={mockTask}
          type="task"
          member={mockMember}
          onClick={onClick}
          onToggleComplete={onToggleComplete}
        />
      )
      fireEvent.click(screen.getByLabelText('Mark complete'))
      expect(onToggleComplete).toHaveBeenCalledWith(mockTask)
    })

    it('stopPropagation: checkbox click does not trigger row onClick', () => {
      const onToggleComplete = vi.fn()
      const onClick = vi.fn()
      render(
        <CalendarItem
          item={mockTask}
          type="task"
          member={mockMember}
          onClick={onClick}
          onToggleComplete={onToggleComplete}
        />
      )
      fireEvent.click(screen.getByLabelText('Mark complete'))
      expect(onToggleComplete).toHaveBeenCalled()
      expect(onClick).not.toHaveBeenCalled()
    })

    it('shows "Mark incomplete" label for completed tasks', () => {
      render(
        <CalendarItem
          item={mockCompletedTask}
          type="task"
          member={mockMember}
          onToggleComplete={vi.fn()}
        />
      )
      expect(screen.getByLabelText('Mark incomplete')).toBeInTheDocument()
    })

    it('does not render checkbox button for events', () => {
      render(
        <CalendarItem
          item={mockEvent}
          type="event"
          member={mockMember}
          onToggleComplete={vi.fn()}
        />
      )
      expect(screen.queryByLabelText('Mark complete')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Mark incomplete')).not.toBeInTheDocument()
    })
  })
})
