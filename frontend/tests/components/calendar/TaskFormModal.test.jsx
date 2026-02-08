import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TaskFormModal from '../../../src/components/calendar/TaskFormModal'

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  onSaved: vi.fn(),
  defaultDate: new Date(2026, 1, 7), // Feb 7, 2026
  initialTask: null,
}

function renderModal(overrides = {}) {
  const props = { ...defaultProps, ...overrides }
  props.onClose.mockClear()
  props.onSaved.mockClear()
  return render(<TaskFormModal {...props} />)
}

describe('TaskFormModal', () => {
  describe('title', () => {
    it('shows "New Task" when creating', async () => {
      renderModal()
      await waitFor(() => {
        expect(screen.getByText('New Task')).toBeInTheDocument()
      })
    })

    it('shows "Edit Task" when editing', async () => {
      renderModal({
        initialTask: {
          id: 1,
          title: 'Buy groceries',
          description: 'Milk, eggs',
          due_date: '2026-02-07',
          completed: false,
          important: false,
          assigned_to: 1,
          list_id: 1,
        },
      })
      await waitFor(() => {
        expect(screen.getByText('Edit Task')).toBeInTheDocument()
      })
    })
  })

  describe('form pre-fill', () => {
    it('pre-fills title from initialTask', async () => {
      renderModal({
        initialTask: {
          id: 1,
          title: 'Buy groceries',
          description: '',
          due_date: '2026-02-07',
          completed: false,
          important: false,
          assigned_to: 1,
          list_id: 1,
        },
      })
      await waitFor(() => {
        expect(screen.getByDisplayValue('Buy groceries')).toBeInTheDocument()
      })
    })

    it('pre-fills due date from defaultDate in create mode', async () => {
      renderModal({ defaultDate: new Date(2026, 1, 15) })
      await waitFor(() => {
        expect(screen.getByDisplayValue('2026-02-15')).toBeInTheDocument()
      })
    })
  })

  describe('list selector', () => {
    it('shows available lists', async () => {
      renderModal()
      await waitFor(() => {
        expect(screen.getByText('Personal')).toBeInTheDocument()
        expect(screen.getByText('Work')).toBeInTheDocument()
      })
    })
  })

  describe('submit behavior', () => {
    it('shows "Add Task" button in create mode', async () => {
      renderModal()
      await waitFor(() => {
        expect(screen.getByText('Add Task')).toBeInTheDocument()
      })
    })

    it('shows "Save Changes" button in edit mode', async () => {
      renderModal({
        initialTask: {
          id: 1,
          title: 'Test task',
          description: '',
          due_date: '2026-02-07',
          completed: false,
          important: false,
          assigned_to: 1,
          list_id: 1,
        },
      })
      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument()
      })
    })

    it('calls onSaved and onClose on successful create', async () => {
      const user = userEvent.setup()
      const onSaved = vi.fn()
      const onClose = vi.fn()
      renderModal({ onSaved, onClose })

      await waitFor(() => {
        expect(screen.getByText('Add Task')).toBeInTheDocument()
      })

      const titleInput = screen.getByPlaceholderText('Enter task title')
      await user.type(titleInput, 'New task')
      await user.click(screen.getByText('Add Task'))

      await waitFor(() => {
        expect(onSaved).toHaveBeenCalled()
        expect(onClose).toHaveBeenCalled()
      })
    })

    it('calls onSaved and onClose on successful edit', async () => {
      const user = userEvent.setup()
      const onSaved = vi.fn()
      const onClose = vi.fn()
      renderModal({
        onSaved,
        onClose,
        initialTask: {
          id: 1,
          title: 'Existing task',
          description: '',
          due_date: '2026-02-07',
          completed: false,
          important: false,
          assigned_to: 1,
          list_id: 1,
        },
      })

      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Save Changes'))

      await waitFor(() => {
        expect(onSaved).toHaveBeenCalled()
        expect(onClose).toHaveBeenCalled()
      })
    })
  })

  describe('delete button', () => {
    it('shows Delete Task button in edit mode', async () => {
      renderModal({
        initialTask: {
          id: 1,
          title: 'Test task',
          description: '',
          due_date: '2026-02-07',
          completed: false,
          important: false,
          assigned_to: 1,
          list_id: 1,
        },
      })
      await waitFor(() => {
        expect(screen.getByText('Delete Task')).toBeInTheDocument()
      })
    })

    it('does not show Delete Task button in create mode', async () => {
      renderModal()
      await waitFor(() => {
        expect(screen.getByText('New Task')).toBeInTheDocument()
      })
      expect(screen.queryByText('Delete Task')).not.toBeInTheDocument()
    })

    it('calls onSaved and onClose on successful delete', async () => {
      const user = userEvent.setup()
      const onSaved = vi.fn()
      const onClose = vi.fn()
      renderModal({
        onSaved,
        onClose,
        initialTask: {
          id: 1,
          title: 'Task to delete',
          description: '',
          due_date: '2026-02-07',
          completed: false,
          important: false,
          assigned_to: 1,
          list_id: 1,
        },
      })

      await waitFor(() => {
        expect(screen.getByText('Delete Task')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Delete Task'))

      await waitFor(() => {
        expect(onSaved).toHaveBeenCalled()
        expect(onClose).toHaveBeenCalled()
      })
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
      expect(screen.queryByText('New Task')).not.toBeInTheDocument()
    })
  })
})
