import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import EventFormModal from '../../../src/components/calendar/EventFormModal'

const mockFamilyMembers = [
  { id: 1, name: 'Everyone', is_system: true, color: '#D97452' },
  { id: 2, name: 'Alice', is_system: false, color: '#3B82F6' },
  { id: 3, name: 'Bob', is_system: false, color: '#EF4444' },
]

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  onSaved: vi.fn(),
  initialEvent: null,
  defaultDate: new Date(2026, 1, 7),
  defaultTime: null,
  familyMembers: mockFamilyMembers,
}

function renderModal(overrides = {}) {
  const props = { ...defaultProps, ...overrides }
  props.onClose.mockClear()
  props.onSaved.mockClear()
  return render(<EventFormModal {...props} />)
}

describe('EventFormModal', () => {
  describe('title', () => {
    it('shows "New Event" when creating', async () => {
      renderModal()
      await waitFor(() => {
        expect(screen.getByText('New Event')).toBeInTheDocument()
      })
    })

    it('shows "Edit Event" when editing', async () => {
      renderModal({
        initialEvent: {
          id: 1,
          title: 'Test Event',
          date: '2026-02-07',
          all_day: false,
          start_time: '09:00',
          end_time: '10:00',
          source: 'MANUAL',
          assigned_to: null,
        },
      })
      await waitFor(() => {
        expect(screen.getByText('Edit Event')).toBeInTheDocument()
      })
    })
  })

  describe('form pre-fill', () => {
    it('pre-fills date from defaultDate', async () => {
      renderModal({ defaultDate: new Date(2026, 1, 15) })
      await waitFor(() => {
        const dateInput = screen.getByDisplayValue('2026-02-15')
        expect(dateInput).toBeInTheDocument()
      })
    })

    it('pre-fills start/end time from defaultTime', async () => {
      renderModal({ defaultTime: '14:00' })
      await waitFor(() => {
        expect(screen.getByDisplayValue('14:00')).toBeInTheDocument()
        expect(screen.getByDisplayValue('15:00')).toBeInTheDocument() // +1 hour
      })
    })
  })

  describe('all-day toggle', () => {
    it('hides time inputs when All Day is on', async () => {
      const user = userEvent.setup()
      renderModal({ defaultTime: '09:00' })

      await waitFor(() => {
        expect(screen.getByText('Start Time')).toBeInTheDocument()
      })

      // Toggle All Day on
      const toggle = screen.getByRole('switch')
      await user.click(toggle)

      expect(screen.queryByText('Start Time')).not.toBeInTheDocument()
      expect(screen.queryByText('End Time')).not.toBeInTheDocument()
    })

    it('shows time inputs when All Day is off', async () => {
      renderModal()
      await waitFor(() => {
        expect(screen.getByText('Start Time')).toBeInTheDocument()
        expect(screen.getByText('End Time')).toBeInTheDocument()
      })
    })
  })

  describe('assigned to dropdown', () => {
    it('shows family members in dropdown', async () => {
      renderModal()
      await waitFor(() => {
        expect(screen.getByText('Unassigned')).toBeInTheDocument()
        expect(screen.getByText('Everyone')).toBeInTheDocument()
        expect(screen.getByText('Alice')).toBeInTheDocument()
        expect(screen.getByText('Bob')).toBeInTheDocument()
      })
    })
  })

  describe('submit behavior', () => {
    it('calls POST for new events', async () => {
      const user = userEvent.setup()
      const onSaved = vi.fn()
      const onClose = vi.fn()
      renderModal({ onSaved, onClose })

      await waitFor(() => {
        expect(screen.getByText('Create Event')).toBeInTheDocument()
      })

      // Fill in title
      const titleInput = screen.getByPlaceholderText('Event title')
      await user.type(titleInput, 'New event')

      // Submit
      await user.click(screen.getByText('Create Event'))

      await waitFor(() => {
        expect(onSaved).toHaveBeenCalled()
        expect(onClose).toHaveBeenCalled()
      })
    })

    it('shows "Save Changes" for editing', async () => {
      renderModal({
        initialEvent: {
          id: 1,
          title: 'Existing',
          date: '2026-02-07',
          all_day: false,
          start_time: '09:00',
          end_time: '10:00',
          source: 'MANUAL',
          assigned_to: null,
        },
      })
      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument()
      })
    })
  })

  describe('delete button', () => {
    it('shows Delete button for editable events in edit mode', async () => {
      renderModal({
        initialEvent: {
          id: 1,
          title: 'Manual event',
          date: '2026-02-07',
          all_day: false,
          start_time: '09:00',
          end_time: '10:00',
          source: 'MANUAL',
          assigned_to: null,
        },
      })
      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })
    })

    it('does not show Delete button for new events', async () => {
      renderModal()
      await waitFor(() => {
        expect(screen.getByText('Create Event')).toBeInTheDocument()
      })
      expect(screen.queryByText('Delete')).not.toBeInTheDocument()
    })

    it('does not show Delete button for synced events', async () => {
      renderModal({
        initialEvent: {
          id: 1,
          title: 'Synced event',
          date: '2026-02-07',
          all_day: true,
          source: 'ICLOUD',
          assigned_to: null,
        },
      })
      await waitFor(() => {
        expect(screen.getByText('Edit Event')).toBeInTheDocument()
      })
      expect(screen.queryByText('Delete')).not.toBeInTheDocument()
    })
  })

  describe('cancel', () => {
    it('calls onClose when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Cancel'))
      expect(onClose).toHaveBeenCalled()
    })
  })

  describe('closed state', () => {
    it('does not render content when isOpen is false', () => {
      renderModal({ isOpen: false })
      expect(screen.queryByText('New Event')).not.toBeInTheDocument()
    })
  })
})
