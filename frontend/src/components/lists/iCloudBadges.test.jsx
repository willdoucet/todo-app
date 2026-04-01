/**
 * Tests for TaskItem iCloud sync badges.
 *
 * Tests:
 * - Shows cloud icon when task has external_id (non-null)
 * - Shows "Syncing..." text when sync_status === 'PENDING_PUSH'
 * - No cloud icon when external_id is null
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import TaskItem from './TaskItem'

// Same createTask helper pattern from TaskItem.test.jsx
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
    external_id: null,
    sync_status: null,
    ...overrides,
  }
}

const defaultProps = {
  onToggle: vi.fn(),
  onEdit: vi.fn(),
  onDelete: vi.fn(),
}

describe('TaskItem iCloud badges', () => {
  it('shows cloud icon when task has external_id', () => {
    render(
      <TaskItem
        {...defaultProps}
        task={createTask({ external_id: 'icloud-uid-123', sync_status: 'SYNCED' })}
      />
    )

    expect(screen.getByLabelText('Synced with iCloud')).toBeInTheDocument()
  })

  it('shows "Syncing..." when sync_status is PENDING_PUSH', () => {
    render(
      <TaskItem
        {...defaultProps}
        task={createTask({ external_id: 'icloud-uid-456', sync_status: 'PENDING_PUSH' })}
      />
    )

    expect(screen.getByText('Syncing...')).toBeInTheDocument()
    // Cloud SVG should NOT be rendered when syncing
    expect(screen.queryByLabelText('Synced with iCloud')).not.toBeInTheDocument()
  })

  it('does not show cloud icon when external_id is null', () => {
    render(
      <TaskItem
        {...defaultProps}
        task={createTask({ external_id: null, sync_status: null })}
      />
    )

    expect(screen.queryByLabelText('Synced with iCloud')).not.toBeInTheDocument()
    expect(screen.queryByText('Syncing...')).not.toBeInTheDocument()
  })
})
