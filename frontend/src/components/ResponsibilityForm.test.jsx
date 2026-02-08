/**
 * Tests for ResponsibilityForm component
 *
 * Tests:
 * - Renders all form fields
 * - Loads family members and stock icons
 * - Day selection (toggle, presets)
 * - Category selection
 * - Validation (title, frequency)
 * - Create vs edit mode behavior
 * - Form submission
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ResponsibilityForm from './ResponsibilityForm'

describe('ResponsibilityForm', () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
  }

  describe('form rendering', () => {
    it('renders title input for new responsibility', async () => {
      render(<ResponsibilityForm {...defaultProps} />)

      expect(screen.getByText(/title/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Enter responsibility title')).toBeInTheDocument()
    })

    it('renders description textarea', () => {
      render(<ResponsibilityForm {...defaultProps} />)

      expect(screen.getByPlaceholderText('Add details about this responsibility...')).toBeInTheDocument()
    })

    it('renders category buttons for all options', async () => {
      render(<ResponsibilityForm {...defaultProps} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      expect(screen.getByRole('button', { name: /morning/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /afternoon/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /evening/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /chore/i })).toBeInTheDocument()
    })

    it('renders day selector buttons', () => {
      render(<ResponsibilityForm {...defaultProps} />)

      expect(screen.getByRole('button', { name: 'Sun' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Mon' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Tue' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Wed' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Thu' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Fri' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sat' })).toBeInTheDocument()
    })

    it('renders day preset buttons', () => {
      render(<ResponsibilityForm {...defaultProps} />)

      expect(screen.getByRole('button', { name: 'Weekdays' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Weekends' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Daily' })).toBeInTheDocument()
    })

    it('renders submit and cancel buttons', () => {
      render(<ResponsibilityForm {...defaultProps} />)

      expect(screen.getByRole('button', { name: /add responsibility/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })
  })

  describe('data loading', () => {
    it('shows loading state initially', () => {
      render(<ResponsibilityForm {...defaultProps} />)

      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })

    it('loads and displays family members', async () => {
      render(<ResponsibilityForm {...defaultProps} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      expect(screen.getByRole('option', { name: 'Everyone' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Alice' })).toBeInTheDocument()
    })
  })

  describe('day selection', () => {
    it('has weekdays selected by default', () => {
      const { container } = render(<ResponsibilityForm {...defaultProps} />)

      // Mon-Fri should have selected styling (bg-terracotta-500)
      const monButton = screen.getByRole('button', { name: 'Mon' })
      const satButton = screen.getByRole('button', { name: 'Sat' })

      expect(monButton.className).toContain('bg-terracotta')
      expect(satButton.className).not.toContain('bg-terracotta')
    })

    it('toggles day selection when clicked', async () => {
      const user = userEvent.setup()
      render(<ResponsibilityForm {...defaultProps} />)

      const satButton = screen.getByRole('button', { name: 'Sat' })

      // Initially not selected
      expect(satButton.className).not.toContain('bg-terracotta')

      // Click to select
      await user.click(satButton)
      expect(satButton.className).toContain('bg-terracotta')

      // Click to deselect
      await user.click(satButton)
      expect(satButton.className).not.toContain('bg-terracotta')
    })

    it('selects weekdays when Weekdays preset clicked', async () => {
      const user = userEvent.setup()
      render(<ResponsibilityForm {...defaultProps} />)

      // First clear all by clicking Daily then toggling off each
      await user.click(screen.getByRole('button', { name: 'Weekends' }))

      // Sat and Sun should be selected, Mon-Fri should not
      expect(screen.getByRole('button', { name: 'Sat' }).className).toContain('bg-terracotta')
      expect(screen.getByRole('button', { name: 'Mon' }).className).not.toContain('bg-terracotta')

      // Now click Weekdays
      await user.click(screen.getByRole('button', { name: 'Weekdays' }))

      expect(screen.getByRole('button', { name: 'Mon' }).className).toContain('bg-terracotta')
      expect(screen.getByRole('button', { name: 'Tue' }).className).toContain('bg-terracotta')
      expect(screen.getByRole('button', { name: 'Wed' }).className).toContain('bg-terracotta')
      expect(screen.getByRole('button', { name: 'Thu' }).className).toContain('bg-terracotta')
      expect(screen.getByRole('button', { name: 'Fri' }).className).toContain('bg-terracotta')
      expect(screen.getByRole('button', { name: 'Sat' }).className).not.toContain('bg-terracotta')
    })

    it('selects all days when Daily preset clicked', async () => {
      const user = userEvent.setup()
      render(<ResponsibilityForm {...defaultProps} />)

      await user.click(screen.getByRole('button', { name: 'Daily' }))

      // All days should be selected
      ;['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(day => {
        expect(screen.getByRole('button', { name: day }).className).toContain('bg-terracotta')
      })
    })
  })

  describe('validation', () => {
    it('shows error when no days selected', async () => {
      const user = userEvent.setup()
      render(<ResponsibilityForm {...defaultProps} />)

      // Deselect all weekdays (default selection)
      const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
      for (const day of weekdays) {
        await user.click(screen.getByRole('button', { name: day }))
      }

      expect(screen.getByText('Please select at least one day')).toBeInTheDocument()
    })

    it('disables submit button when no days selected', async () => {
      const user = userEvent.setup()
      render(<ResponsibilityForm {...defaultProps} />)

      // Deselect all weekdays
      const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
      for (const day of weekdays) {
        await user.click(screen.getByRole('button', { name: day }))
      }

      const submitButton = screen.getByRole('button', { name: /add responsibility/i })
      expect(submitButton).toBeDisabled()
    })

    it('does not submit when title is empty', async () => {
      const onSubmit = vi.fn()
      const user = userEvent.setup()

      render(<ResponsibilityForm {...defaultProps} onSubmit={onSubmit} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Don't fill title, just submit
      await user.click(screen.getByRole('button', { name: /add responsibility/i }))

      expect(onSubmit).not.toHaveBeenCalled()
    })
  })

  describe('edit mode', () => {
    const existingResponsibility = {
      id: 1,
      title: 'Make bed',
      description: 'Every morning',
      categories: ['MORNING'],
      assigned_to: 2,
      frequency: ['Monday', 'Wednesday', 'Friday'],
      icon_url: null,
    }

    it('shows title as readonly text in edit mode', () => {
      render(<ResponsibilityForm {...defaultProps} initial={existingResponsibility} />)

      // Should show title as text, not input
      expect(screen.getByText('Make bed')).toBeInTheDocument()
      expect(screen.queryByPlaceholderText('Enter responsibility title')).not.toBeInTheDocument()
    })

    it('pre-fills description from initial data', () => {
      render(<ResponsibilityForm {...defaultProps} initial={existingResponsibility} />)

      expect(screen.getByDisplayValue('Every morning')).toBeInTheDocument()
    })

    it('pre-fills frequency from initial data', () => {
      render(<ResponsibilityForm {...defaultProps} initial={existingResponsibility} />)

      // Mon, Wed, Fri should be selected
      expect(screen.getByRole('button', { name: 'Mon' }).className).toContain('bg-terracotta')
      expect(screen.getByRole('button', { name: 'Wed' }).className).toContain('bg-terracotta')
      expect(screen.getByRole('button', { name: 'Fri' }).className).toContain('bg-terracotta')

      // Others should not
      expect(screen.getByRole('button', { name: 'Tue' }).className).not.toContain('bg-terracotta')
    })

    it('shows "Save Changes" button in edit mode', () => {
      render(<ResponsibilityForm {...defaultProps} initial={existingResponsibility} />)

      expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument()
    })

    it('excludes title from submission in edit mode', async () => {
      const onSubmit = vi.fn()
      const user = userEvent.setup()

      render(<ResponsibilityForm {...defaultProps} initial={existingResponsibility} onSubmit={onSubmit} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 1,
          categories: ['MORNING'],
          frequency: ['Monday', 'Wednesday', 'Friday'],
        })
      )
      // Should not include title in edit mode
      expect(onSubmit).toHaveBeenCalledWith(
        expect.not.objectContaining({ title: expect.anything() })
      )
    })

    it('includes icon_url and description in edit mode submission', async () => {
      const onSubmit = vi.fn()
      const user = userEvent.setup()

      // Start with no icon_url — simulates a responsibility created without an icon
      render(<ResponsibilityForm {...defaultProps} initial={existingResponsibility} onSubmit={onSubmit} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /save changes/i }))

      // icon_url and description should always be included in the submitted data
      const submittedData = onSubmit.mock.calls[0][0]
      expect(submittedData).toHaveProperty('icon_url')
      expect(submittedData).toHaveProperty('description')
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with form data when creating', async () => {
      const onSubmit = vi.fn()
      const user = userEvent.setup()

      render(<ResponsibilityForm {...defaultProps} onSubmit={onSubmit} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Fill the form
      await user.type(screen.getByPlaceholderText('Enter responsibility title'), 'Brush teeth')
      await user.type(screen.getByPlaceholderText('Add details about this responsibility...'), 'Morning and night')

      // Submit
      await user.click(screen.getByRole('button', { name: /add responsibility/i }))

      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Brush teeth',
          description: 'Morning and night',
          categories: ['MORNING'],
          assigned_to: 1,
          frequency: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        })
      )
    })

    it('calls onCancel when cancel button clicked', async () => {
      const onCancel = vi.fn()
      const user = userEvent.setup()

      render(<ResponsibilityForm {...defaultProps} onCancel={onCancel} />)

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      expect(onCancel).toHaveBeenCalledTimes(1)
    })
  })

  describe('custom icon upload', () => {
    it('shows upload option toggle', () => {
      render(<ResponsibilityForm {...defaultProps} />)

      expect(screen.getByRole('button', { name: /upload custom icon/i })).toBeInTheDocument()
    })

    it('toggles custom upload visibility', async () => {
      const user = userEvent.setup()
      render(<ResponsibilityForm {...defaultProps} />)

      // Initially hidden
      expect(screen.queryByText('Upload Icon')).not.toBeInTheDocument()

      // Click to show
      await user.click(screen.getByRole('button', { name: /upload custom icon/i }))

      // PhotoUpload component should appear
      expect(screen.getByText(/hide custom upload/i)).toBeInTheDocument()
    })
  })
})
