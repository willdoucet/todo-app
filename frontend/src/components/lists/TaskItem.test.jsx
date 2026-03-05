/**
 * Tests for TaskItem component
 *
 * Tests:
 * - Renders task title and description
 * - Completed task styling
 * - Due date display and overdue styling
 * - Important indicator
 * - Assigned member display
 * - Button interactions (toggle, edit, delete)
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TaskItem from './TaskItem'

// Helper to create task objects with defaults
function createTask(overrides = {}) {
  return {
    id: 1,
    title: 'Test Task',
    description: null,
    completed: false,
    important: false,
    due_date: null,
    family_member: null,
    ...overrides,
  }
}

describe('TaskItem', () => {
  const defaultProps = {
    task: createTask(),
    onToggle: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
  }

  describe('basic rendering', () => {
    it('renders task title', () => {
      render(<TaskItem {...defaultProps} task={createTask({ title: 'Buy groceries' })} />)

      expect(screen.getByText('Buy groceries')).toBeInTheDocument()
    })

    it('renders description when provided', () => {
      render(
        <TaskItem
          {...defaultProps}
          task={createTask({ description: 'Get milk and eggs' })}
        />
      )

      expect(screen.getByText('Get milk and eggs')).toBeInTheDocument()
    })

    it('does not render description when not provided', () => {
      render(<TaskItem {...defaultProps} task={createTask({ description: null })} />)

      // Only title should be in text content, no description paragraph
      expect(screen.queryByText('Get milk and eggs')).not.toBeInTheDocument()
    })

    it('renders checkbox in unchecked state for incomplete task', () => {
      render(<TaskItem {...defaultProps} task={createTask({ completed: false })} />)

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toHaveAttribute('aria-checked', 'false')
    })

    it('renders checkbox in checked state for completed task', () => {
      render(<TaskItem {...defaultProps} task={createTask({ completed: true })} />)

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toHaveAttribute('aria-checked', 'true')
    })
  })

  describe('completed task styling', () => {
    it('applies line-through styling to completed task title', () => {
      render(<TaskItem {...defaultProps} task={createTask({ completed: true })} />)

      const title = screen.getByText('Test Task')
      expect(title).toHaveClass('line-through')
    })

    it('does not apply line-through to incomplete task', () => {
      render(<TaskItem {...defaultProps} task={createTask({ completed: false })} />)

      const title = screen.getByText('Test Task')
      expect(title).not.toHaveClass('line-through')
    })
  })

  describe('due date display', () => {
    it('renders due date when provided', () => {
      // Use a future date in current year to avoid year being displayed
      const futureDate = new Date()
      futureDate.setMonth(futureDate.getMonth() + 1)
      const dateStr = futureDate.toISOString().split('T')[0]

      render(
        <TaskItem
          {...defaultProps}
          task={createTask({ due_date: dateStr })}
        />
      )

      // Should show formatted date (month abbreviation and day)
      expect(screen.getByText(/[A-Z][a-z]{2} \d{1,2}/)).toBeInTheDocument()
    })

    it('does not render due date section when not provided', () => {
      render(<TaskItem {...defaultProps} task={createTask({ due_date: null })} />)

      // Calendar icon shouldn't be present - check for date pattern
      expect(screen.queryByText(/[A-Z][a-z]{2} \d{1,2}/)).not.toBeInTheDocument()
    })

    it('applies overdue styling when due date is past and task not completed', () => {
      // Set due date to yesterday
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)
      const pastDate = yesterday.toISOString().split('T')[0]

      render(
        <TaskItem
          {...defaultProps}
          task={createTask({ due_date: pastDate, completed: false })}
        />
      )

      // The date text should have red styling
      const dateText = screen.getByText(/[A-Z][a-z]{2} \d{1,2}/)
      expect(dateText).toHaveClass('text-red-500')
    })

    it('does not apply overdue styling when task is completed', () => {
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)
      const pastDate = yesterday.toISOString().split('T')[0]

      render(
        <TaskItem
          {...defaultProps}
          task={createTask({ due_date: pastDate, completed: true })}
        />
      )

      const dateText = screen.getByText(/[A-Z][a-z]{2} \d{1,2}/)
      expect(dateText).not.toHaveClass('text-red-500')
    })
  })

  describe('important indicator', () => {
    it('shows star icon when task is important', () => {
      render(<TaskItem {...defaultProps} task={createTask({ important: true })} />)

      // Star has title="Important"
      expect(screen.getByTitle('Important')).toBeInTheDocument()
    })

    it('does not show star icon when task is not important', () => {
      render(<TaskItem {...defaultProps} task={createTask({ important: false })} />)

      expect(screen.queryByTitle('Important')).not.toBeInTheDocument()
    })
  })

  describe('assigned member display', () => {
    it('shows member initial for regular family member', () => {
      render(
        <TaskItem
          {...defaultProps}
          task={createTask({
            family_member: { id: 1, name: 'Alice', is_system: false },
          })}
        />
      )

      expect(screen.getByText('A')).toBeInTheDocument()
      expect(screen.getByTitle('Assigned to Alice')).toBeInTheDocument()
    })

    it('shows group icon for system member (Everyone)', () => {
      render(
        <TaskItem
          {...defaultProps}
          task={createTask({
            family_member: { id: 1, name: 'Everyone', is_system: true },
          })}
        />
      )

      expect(screen.getByTitle('Assigned to Everyone')).toBeInTheDocument()
    })

    it('does not show assigned icon when no family member', () => {
      render(<TaskItem {...defaultProps} task={createTask({ family_member: null })} />)

      expect(screen.queryByTitle(/Assigned to/)).not.toBeInTheDocument()
    })
  })

  describe('button interactions', () => {
    it('calls onToggle with task id when checkbox is clicked', async () => {
      const onToggle = vi.fn()
      const user = userEvent.setup()

      render(
        <TaskItem
          {...defaultProps}
          onToggle={onToggle}
          task={createTask({ id: 42 })}
        />
      )

      await user.click(screen.getByRole('checkbox'))

      expect(onToggle).toHaveBeenCalledTimes(1)
      expect(onToggle).toHaveBeenCalledWith(42)
    })

    it('calls onEdit when edit button is clicked', async () => {
      const onEdit = vi.fn()
      const user = userEvent.setup()

      render(<TaskItem {...defaultProps} onEdit={onEdit} />)

      await user.click(screen.getByLabelText(/^Edit task:/))

      expect(onEdit).toHaveBeenCalledTimes(1)
    })

    it('calls onDelete with task id when delete button is clicked', async () => {
      const onDelete = vi.fn()
      const user = userEvent.setup()

      render(
        <TaskItem
          {...defaultProps}
          onDelete={onDelete}
          task={createTask({ id: 99 })}
        />
      )

      await user.click(screen.getByLabelText(/^Delete task:/))

      expect(onDelete).toHaveBeenCalledTimes(1)
      expect(onDelete).toHaveBeenCalledWith(99)
    })
  })
})
