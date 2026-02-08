import { render, screen, fireEvent } from '@testing-library/react'
import AllDaySection from '../../../src/components/calendar/AllDaySection'

const mockFamilyMembers = [
  { id: 1, name: 'Everyone', is_system: true, color: '#D97452' },
  { id: 2, name: 'Alice', is_system: false, color: '#3B82F6' },
]

const mockTasks = [
  { id: 1, title: 'Morning routine', completed: false, assigned_to: 2, family_member: mockFamilyMembers[1] },
  { id: 2, title: 'Done task', completed: true, assigned_to: 1, family_member: mockFamilyMembers[0] },
]

describe('AllDaySection', () => {
  describe('rendering', () => {
    it('renders task titles as bars', () => {
      render(<AllDaySection tasks={mockTasks} familyMembers={mockFamilyMembers} />)
      expect(screen.getByText('Morning routine')).toBeInTheDocument()
      expect(screen.getByText('Done task')).toBeInTheDocument()
    })

    it('returns null when no tasks', () => {
      const { container } = render(<AllDaySection tasks={[]} familyMembers={mockFamilyMembers} />)
      expect(container.innerHTML).toBe('')
    })

    it('renders completed tasks with line-through', () => {
      render(<AllDaySection tasks={mockTasks} familyMembers={mockFamilyMembers} />)
      const completedBar = screen.getByText('Done task').closest('div')
      expect(completedBar).toHaveClass('line-through')
    })
  })

  describe('click to edit', () => {
    it('calls onEditTask when bar is clicked', () => {
      const onEditTask = vi.fn()
      render(
        <AllDaySection
          tasks={mockTasks}
          familyMembers={mockFamilyMembers}
          onEditTask={onEditTask}
        />
      )
      fireEvent.click(screen.getByText('Morning routine'))
      expect(onEditTask).toHaveBeenCalledWith(mockTasks[0])
    })

    it('adds cursor-pointer when onEditTask is provided', () => {
      render(
        <AllDaySection
          tasks={mockTasks}
          familyMembers={mockFamilyMembers}
          onEditTask={vi.fn()}
        />
      )
      const bar = screen.getByText('Morning routine').closest('[class*="cursor-pointer"]')
      expect(bar).toBeInTheDocument()
    })
  })

  describe('toggle complete', () => {
    it('renders checkbox buttons when onToggleComplete is provided', () => {
      render(
        <AllDaySection
          tasks={mockTasks}
          familyMembers={mockFamilyMembers}
          onToggleComplete={vi.fn()}
        />
      )
      expect(screen.getByLabelText('Mark complete')).toBeInTheDocument()
      expect(screen.getByLabelText('Mark incomplete')).toBeInTheDocument()
    })

    it('does not render checkboxes when onToggleComplete is not provided', () => {
      render(<AllDaySection tasks={mockTasks} familyMembers={mockFamilyMembers} />)
      expect(screen.queryByLabelText('Mark complete')).not.toBeInTheDocument()
    })

    it('calls onToggleComplete when checkbox is clicked', () => {
      const onToggleComplete = vi.fn()
      render(
        <AllDaySection
          tasks={mockTasks}
          familyMembers={mockFamilyMembers}
          onToggleComplete={onToggleComplete}
        />
      )
      fireEvent.click(screen.getByLabelText('Mark complete'))
      expect(onToggleComplete).toHaveBeenCalledWith(mockTasks[0])
    })

    it('stopPropagation: checkbox click does not trigger onEditTask', () => {
      const onEditTask = vi.fn()
      const onToggleComplete = vi.fn()
      render(
        <AllDaySection
          tasks={mockTasks}
          familyMembers={mockFamilyMembers}
          onEditTask={onEditTask}
          onToggleComplete={onToggleComplete}
        />
      )
      fireEvent.click(screen.getByLabelText('Mark complete'))
      expect(onToggleComplete).toHaveBeenCalled()
      expect(onEditTask).not.toHaveBeenCalled()
    })
  })
})
