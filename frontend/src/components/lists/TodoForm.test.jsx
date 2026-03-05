/**
 * Tests for TodoForm component
 *
 * Tests:
 * - Renders all form fields
 * - Loads and displays family members
 * - Pre-fills form when editing
 * - Validates title is required
 * - Submits form data correctly
 * - Cancel button works
 * - Important toggle works
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TodoForm from './TodoForm'

describe('TodoForm', () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
  }

  describe('form rendering', () => {
    it('renders title input', async () => {
      render(<TodoForm {...defaultProps} />)

      expect(screen.getByText(/title/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Enter task title')).toBeInTheDocument()
    })

    it('renders description textarea', () => {
      render(<TodoForm {...defaultProps} />)

      expect(screen.getByText(/description/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Add a description (optional)')).toBeInTheDocument()
    })

    it('renders due date input', () => {
      const { container } = render(<TodoForm {...defaultProps} />)

      expect(screen.getByText(/due date/i)).toBeInTheDocument()
      expect(container.querySelector('input[type="date"]')).toBeInTheDocument()
    })

    it('renders assigned to dropdown', async () => {
      render(<TodoForm {...defaultProps} />)

      expect(screen.getByText(/assigned to/i)).toBeInTheDocument()
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    it('renders important toggle', () => {
      render(<TodoForm {...defaultProps} />)

      expect(screen.getByText(/mark as important/i)).toBeInTheDocument()
      expect(screen.getByRole('switch')).toBeInTheDocument()
    })

    it('renders submit and cancel buttons', () => {
      render(<TodoForm {...defaultProps} />)

      expect(screen.getByRole('button', { name: /add task/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })
  })

  describe('family members loading', () => {
    it('shows loading state initially', () => {
      render(<TodoForm {...defaultProps} />)

      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })

    it('loads and displays family members in dropdown', async () => {
      render(<TodoForm {...defaultProps} />)

      // Wait for loading to finish and members to appear
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Check that family members from mock are displayed
      expect(screen.getByRole('option', { name: 'Everyone' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Alice' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Bob' })).toBeInTheDocument()
    })

    it('auto-selects first family member for new tasks', async () => {
      render(<TodoForm {...defaultProps} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // First member (Everyone) should be selected
      const select = screen.getByRole('combobox')
      expect(select.value).toBe('1') // Everyone's ID
    })
  })

  describe('editing existing task', () => {
    const existingTask = {
      id: 1,
      title: 'Existing Task',
      description: 'Task description',
      due_date: '2026-06-15T00:00:00Z',
      important: true,
      assigned_to: 2,
    }

    it('pre-fills title from initial data', () => {
      render(<TodoForm {...defaultProps} initial={existingTask} />)

      expect(screen.getByDisplayValue('Existing Task')).toBeInTheDocument()
    })

    it('pre-fills description from initial data', () => {
      render(<TodoForm {...defaultProps} initial={existingTask} />)

      expect(screen.getByDisplayValue('Task description')).toBeInTheDocument()
    })

    it('pre-fills due date from initial data', () => {
      render(<TodoForm {...defaultProps} initial={existingTask} />)

      expect(screen.getByDisplayValue('2026-06-15')).toBeInTheDocument()
    })

    it('pre-fills important toggle from initial data', () => {
      render(<TodoForm {...defaultProps} initial={existingTask} />)

      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveAttribute('aria-checked', 'true')
    })

    it('shows "Save Changes" button when editing', () => {
      render(<TodoForm {...defaultProps} initial={existingTask} />)

      expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument()
    })

    it('shows "Add Task" button when creating new', () => {
      render(<TodoForm {...defaultProps} />)

      expect(screen.getByRole('button', { name: /add task/i })).toBeInTheDocument()
    })
  })

  describe('form interactions', () => {
    it('updates title when user types', async () => {
      const user = userEvent.setup()
      render(<TodoForm {...defaultProps} />)

      const input = screen.getByPlaceholderText('Enter task title')
      await user.type(input, 'New Task')

      expect(input).toHaveValue('New Task')
    })

    it('toggles important when clicked', async () => {
      const user = userEvent.setup()
      render(<TodoForm {...defaultProps} />)

      const toggle = screen.getByRole('switch')
      expect(toggle).toHaveAttribute('aria-checked', 'false')

      await user.click(toggle)

      expect(toggle).toHaveAttribute('aria-checked', 'true')
    })

    it('calls onCancel when cancel button clicked', async () => {
      const onCancel = vi.fn()
      const user = userEvent.setup()

      render(<TodoForm {...defaultProps} onCancel={onCancel} />)

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      expect(onCancel).toHaveBeenCalledTimes(1)
    })
  })

  describe('form submission', () => {
    it('does not submit when title is empty', async () => {
      const onSubmit = vi.fn()
      const user = userEvent.setup()

      render(<TodoForm {...defaultProps} onSubmit={onSubmit} />)

      // Wait for family members to load
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /add task/i }))

      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('calls onSubmit with form data when submitted', async () => {
      const onSubmit = vi.fn()
      const user = userEvent.setup()

      render(<TodoForm {...defaultProps} onSubmit={onSubmit} listId={5} />)

      // Wait for family members to load
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Fill in the form
      await user.type(screen.getByPlaceholderText('Enter task title'), 'Test Task')
      await user.type(screen.getByPlaceholderText('Add a description (optional)'), 'Test description')
      await user.click(screen.getByRole('switch')) // Toggle important

      // Submit
      await user.click(screen.getByRole('button', { name: /add task/i }))

      expect(onSubmit).toHaveBeenCalledTimes(1)
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Test Task',
          description: 'Test description',
          important: true,
          assigned_to: 1, // First family member auto-selected
          list_id: 5,
        })
      )
    })

    it('does not include list_id when editing existing task', async () => {
      const onSubmit = vi.fn()
      const user = userEvent.setup()
      const existingTask = { id: 1, title: 'Edit Me', assigned_to: 1 }

      render(<TodoForm {...defaultProps} onSubmit={onSubmit} initial={existingTask} listId={5} />)

      // Wait for family members to load
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      expect(onSubmit).toHaveBeenCalledWith(
        expect.not.objectContaining({ list_id: 5 })
      )
    })
  })
})
