/**
 * Tests for ReminderListSelector component.
 *
 * Tests:
 * - Renders all reminder lists with names
 * - Shows task counts
 * - Checkbox toggles selection
 * - Select All / Deselect All works
 * - Shows "Already synced" warning
 * - Shows "Select at least one list" hint when none selected
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ReminderListSelector from './ReminderListSelector'

const sampleLists = [
  { url: '/cal/list-1', name: 'Shopping', color: '#FF0000', task_count: 5, already_synced_by: null },
  { url: '/cal/list-2', name: 'Work', color: '#00FF00', task_count: 12, already_synced_by: null },
  { url: '/cal/list-3', name: 'Shared', color: '#0000FF', task_count: 3, already_synced_by: 'Alice' },
]

describe('ReminderListSelector', () => {
  const defaultProps = {
    reminderLists: sampleLists,
    selected: [],
    onChange: vi.fn(),
  }

  describe('rendering', () => {
    it('renders all reminder list names', () => {
      render(<ReminderListSelector {...defaultProps} />)

      expect(screen.getByText('Shopping')).toBeInTheDocument()
      expect(screen.getByText('Work')).toBeInTheDocument()
      expect(screen.getByText('Shared')).toBeInTheDocument()
    })

    it('shows task counts', () => {
      render(<ReminderListSelector {...defaultProps} />)

      expect(screen.getByText('5 tasks')).toBeInTheDocument()
      expect(screen.getByText('12 tasks')).toBeInTheDocument()
      expect(screen.getByText('3 tasks')).toBeInTheDocument()
    })

    it('shows singular "task" for count of 1', () => {
      const lists = [{ url: '/cal/single', name: 'Single', color: '#000', task_count: 1 }]
      render(<ReminderListSelector reminderLists={lists} selected={[]} onChange={vi.fn()} />)

      expect(screen.getByText('1 task')).toBeInTheDocument()
    })
  })

  describe('checkbox selection', () => {
    it('checks boxes for selected lists', () => {
      render(
        <ReminderListSelector
          {...defaultProps}
          selected={['/cal/list-1']}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes[0]).toBeChecked()
      expect(checkboxes[1]).not.toBeChecked()
      expect(checkboxes[2]).not.toBeChecked()
    })

    it('calls onChange when checkbox is toggled on', async () => {
      const onChange = vi.fn()
      const user = userEvent.setup()

      render(
        <ReminderListSelector
          {...defaultProps}
          selected={[]}
          onChange={onChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[0])

      expect(onChange).toHaveBeenCalledWith(['/cal/list-1'])
    })

    it('calls onChange when checkbox is toggled off', async () => {
      const onChange = vi.fn()
      const user = userEvent.setup()

      render(
        <ReminderListSelector
          {...defaultProps}
          selected={['/cal/list-1', '/cal/list-2']}
          onChange={onChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[0])

      expect(onChange).toHaveBeenCalledWith(['/cal/list-2'])
    })
  })

  describe('Select All / Deselect All', () => {
    it('shows Select All button when multiple lists and not all selected', () => {
      render(<ReminderListSelector {...defaultProps} />)

      expect(screen.getByText('Select All')).toBeInTheDocument()
    })

    it('shows Deselect All when all lists are selected', () => {
      render(
        <ReminderListSelector
          {...defaultProps}
          selected={['/cal/list-1', '/cal/list-2', '/cal/list-3']}
        />
      )

      expect(screen.getByText('Deselect All')).toBeInTheDocument()
    })

    it('selects all lists when Select All is clicked', async () => {
      const onChange = vi.fn()
      const user = userEvent.setup()

      render(
        <ReminderListSelector
          {...defaultProps}
          selected={[]}
          onChange={onChange}
        />
      )

      await user.click(screen.getByText('Select All'))

      expect(onChange).toHaveBeenCalledWith(['/cal/list-1', '/cal/list-2', '/cal/list-3'])
    })

    it('deselects all lists when Deselect All is clicked', async () => {
      const onChange = vi.fn()
      const user = userEvent.setup()

      render(
        <ReminderListSelector
          {...defaultProps}
          selected={['/cal/list-1', '/cal/list-2', '/cal/list-3']}
          onChange={onChange}
        />
      )

      await user.click(screen.getByText('Deselect All'))

      expect(onChange).toHaveBeenCalledWith([])
    })

    it('does not show Select All button for single list', () => {
      const singleList = [sampleLists[0]]
      render(
        <ReminderListSelector
          reminderLists={singleList}
          selected={[]}
          onChange={vi.fn()}
        />
      )

      expect(screen.queryByText('Select All')).not.toBeInTheDocument()
    })
  })

  describe('already synced warning', () => {
    it('shows already synced warning for shared lists', () => {
      render(<ReminderListSelector {...defaultProps} />)

      expect(screen.getByText("Already synced from Alice's account")).toBeInTheDocument()
    })

    it('does not show warning for non-synced lists', () => {
      const lists = [{ url: '/cal/x', name: 'Local', color: '#000', task_count: 2 }]
      render(<ReminderListSelector reminderLists={lists} selected={[]} onChange={vi.fn()} />)

      expect(screen.queryByText(/Already synced/)).not.toBeInTheDocument()
    })
  })

  describe('empty selection hint', () => {
    it('shows hint when no lists are selected', () => {
      render(<ReminderListSelector {...defaultProps} selected={[]} />)

      expect(screen.getByText('Select at least one list to sync.')).toBeInTheDocument()
    })

    it('does not show hint when at least one list is selected', () => {
      render(
        <ReminderListSelector
          {...defaultProps}
          selected={['/cal/list-1']}
        />
      )

      expect(screen.queryByText('Select at least one list to sync.')).not.toBeInTheDocument()
    })
  })
})
