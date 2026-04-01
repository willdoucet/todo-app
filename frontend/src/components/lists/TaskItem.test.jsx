/**
 * Tests for TaskItem component
 *
 * Tests:
 * - Renders task title
 * - Completed task styling
 * - Due date display and overdue styling
 * - Important indicator
 * - Assignee color stripe (right border)
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
    priority: 0,
    due_date: null,
    family_member: null,
    children: [],
    parent_id: null,
    section_id: null,
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

    it('does not render description in task rows', () => {
      render(
        <TaskItem
          {...defaultProps}
          task={createTask({ description: 'Get milk and eggs' })}
        />
      )

      // Description is intentionally hidden from task rows (Option B design)
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

      // The date chip should have red styling
      const dateChip = screen.getByText(/[A-Z][a-z]{2} \d{1,2}/)
      expect(dateChip).toHaveClass('text-red-600')
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
      expect(dateText).not.toHaveClass('text-red-600')
    })
  })

  describe('priority indicator', () => {
    it('shows red flag for high priority (1)', () => {
      render(<TaskItem {...defaultProps} task={createTask({ priority: 1 })} />)

      expect(screen.getByLabelText('High priority')).toBeInTheDocument()
    })

    it('shows amber flag for medium priority (5)', () => {
      render(<TaskItem {...defaultProps} task={createTask({ priority: 5 })} />)

      expect(screen.getByLabelText('Medium priority')).toBeInTheDocument()
    })

    it('shows gray flag for low priority (9)', () => {
      render(<TaskItem {...defaultProps} task={createTask({ priority: 9 })} />)

      expect(screen.getByLabelText('Low priority')).toBeInTheDocument()
    })

    it('does not show flag when priority is none (0)', () => {
      render(<TaskItem {...defaultProps} task={createTask({ priority: 0 })} />)

      expect(screen.queryByLabelText(/priority/)).not.toBeInTheDocument()
    })
  })

  describe('subtask expand/collapse', () => {
    it('shows expand chevron when task has children', () => {
      const taskWithChildren = createTask({
        children: [createTask({ id: 2, title: 'Subtask' })],
      })
      render(<TaskItem {...defaultProps} task={taskWithChildren} />)

      expect(screen.getByLabelText('Expand subtasks')).toBeInTheDocument()
    })

    it('does not show chevron when task has no children', () => {
      render(<TaskItem {...defaultProps} task={createTask()} />)

      expect(screen.queryByLabelText(/subtasks/)).not.toBeInTheDocument()
    })
  })

  describe('assignee color stripe', () => {
    it('shows colored right border for regular family member', () => {
      const { container } = render(
        <TaskItem
          {...defaultProps}
          task={createTask({
            family_member: { id: 1, name: 'Alice', is_system: false, color: '#D4695A' },
          })}
        />
      )

      const row = container.querySelector('[title="Assigned to Alice"]')
      expect(row).toBeInTheDocument()
      expect(row).toHaveStyle({ borderRightColor: '#D4695A' })
    })

    it('shows transparent right border for system member (Everyone)', () => {
      const { container } = render(
        <TaskItem
          {...defaultProps}
          task={createTask({
            family_member: { id: 1, name: 'Everyone', is_system: true },
          })}
        />
      )

      // No title attribute for system members, transparent border
      expect(screen.queryByTitle(/Assigned to/)).not.toBeInTheDocument()
    })

    it('shows transparent right border when no family member', () => {
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
