/**
 * Tests for ResponsibilityCard component
 *
 * Tests:
 * - Renders title and description
 * - Icon display with URL handling
 * - Completed state styling
 * - Click interactions (toggle, edit, delete)
 * - Action button visibility based on props
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ResponsibilityCard from './ResponsibilityCard'

// Helper to create responsibility objects with defaults
function createResponsibility(overrides = {}) {
  return {
    id: 1,
    title: 'Make bed',
    description: null,
    icon_url: null,
    category: 'MORNING',
    frequency: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    ...overrides,
  }
}

describe('ResponsibilityCard', () => {
  const defaultProps = {
    responsibility: createResponsibility(),
    isCompleted: false,
    onToggle: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
  }

  describe('basic rendering', () => {
    it('renders responsibility title', () => {
      render(
        <ResponsibilityCard
          {...defaultProps}
          responsibility={createResponsibility({ title: 'Brush teeth' })}
        />
      )

      expect(screen.getByText('Brush teeth')).toBeInTheDocument()
    })

    it('renders description when provided', () => {
      render(
        <ResponsibilityCard
          {...defaultProps}
          responsibility={createResponsibility({ description: 'Use fluoride toothpaste' })}
        />
      )

      expect(screen.getByText('Use fluoride toothpaste')).toBeInTheDocument()
    })

    it('does not render description when not provided', () => {
      render(
        <ResponsibilityCard
          {...defaultProps}
          responsibility={createResponsibility({ description: null })}
        />
      )

      expect(screen.queryByText('Use fluoride toothpaste')).not.toBeInTheDocument()
    })
  })

  describe('icon display', () => {
    it('renders icon when icon_url is provided', () => {
      const { container } = render(
        <ResponsibilityCard
          {...defaultProps}
          responsibility={createResponsibility({ icon_url: '/uploads/brush.png' })}
        />
      )

      // Image has alt="" (decorative) so we query by tag
      const img = container.querySelector('img')
      expect(img).toBeInTheDocument()
      expect(img.src).toContain('/uploads/brush.png')
    })

    it('renders external URL directly', () => {
      const { container } = render(
        <ResponsibilityCard
          {...defaultProps}
          responsibility={createResponsibility({ icon_url: 'https://example.com/icon.png' })}
        />
      )

      const img = container.querySelector('img')
      expect(img.src).toBe('https://example.com/icon.png')
    })

    it('does not render icon when icon_url is null', () => {
      const { container } = render(
        <ResponsibilityCard
          {...defaultProps}
          responsibility={createResponsibility({ icon_url: null })}
        />
      )

      expect(container.querySelector('img')).not.toBeInTheDocument()
    })
  })

  describe('completed state', () => {
    it('applies line-through to title when completed', () => {
      render(<ResponsibilityCard {...defaultProps} isCompleted={true} />)

      const title = screen.getByText('Make bed')
      expect(title).toHaveClass('line-through')
    })

    it('does not apply line-through when not completed', () => {
      render(<ResponsibilityCard {...defaultProps} isCompleted={false} />)

      const title = screen.getByText('Make bed')
      expect(title).not.toHaveClass('line-through')
    })

    it('applies opacity to icon when completed', () => {
      const { container } = render(
        <ResponsibilityCard
          {...defaultProps}
          isCompleted={true}
          responsibility={createResponsibility({ icon_url: '/icon.png' })}
        />
      )

      const img = container.querySelector('img')
      expect(img).toHaveClass('opacity-60')
    })
  })

  describe('click interactions', () => {
    it('calls onToggle when card is clicked', async () => {
      const onToggle = vi.fn()
      const user = userEvent.setup()

      render(<ResponsibilityCard {...defaultProps} onToggle={onToggle} />)

      await user.click(screen.getByText('Make bed'))

      expect(onToggle).toHaveBeenCalledTimes(1)
    })

    it('calls onEdit with responsibility when edit button is clicked', async () => {
      const onEdit = vi.fn()
      const onToggle = vi.fn()
      const user = userEvent.setup()
      const responsibility = createResponsibility({ id: 42, title: 'Test' })

      render(
        <ResponsibilityCard
          {...defaultProps}
          responsibility={responsibility}
          onEdit={onEdit}
          onToggle={onToggle}
        />
      )

      await user.click(screen.getByLabelText(/^Edit responsibility:/))

      expect(onEdit).toHaveBeenCalledTimes(1)
      expect(onEdit).toHaveBeenCalledWith(responsibility)
      // Should NOT trigger toggle due to stopPropagation
      expect(onToggle).not.toHaveBeenCalled()
    })

    it('calls onDelete with id when delete button is clicked', async () => {
      const onDelete = vi.fn()
      const onToggle = vi.fn()
      const user = userEvent.setup()

      render(
        <ResponsibilityCard
          {...defaultProps}
          responsibility={createResponsibility({ id: 99 })}
          onDelete={onDelete}
          onToggle={onToggle}
        />
      )

      await user.click(screen.getByLabelText(/^Delete responsibility:/))

      expect(onDelete).toHaveBeenCalledTimes(1)
      expect(onDelete).toHaveBeenCalledWith(99)
      // Should NOT trigger toggle due to stopPropagation
      expect(onToggle).not.toHaveBeenCalled()
    })
  })

  describe('action button visibility', () => {
    it('shows edit button when onEdit is provided', () => {
      render(<ResponsibilityCard {...defaultProps} onEdit={vi.fn()} />)

      expect(screen.getByLabelText(/^Edit responsibility:/)).toBeInTheDocument()
    })

    it('does not show edit button when onEdit is not provided', () => {
      render(<ResponsibilityCard {...defaultProps} onEdit={undefined} />)

      expect(screen.queryByLabelText(/^Edit responsibility:/)).not.toBeInTheDocument()
    })

    it('shows delete button when onDelete is provided', () => {
      render(<ResponsibilityCard {...defaultProps} onDelete={vi.fn()} />)

      expect(screen.getByLabelText(/^Delete responsibility:/)).toBeInTheDocument()
    })

    it('does not show delete button when onDelete is not provided', () => {
      render(<ResponsibilityCard {...defaultProps} onDelete={undefined} />)

      expect(screen.queryByLabelText(/^Delete responsibility:/)).not.toBeInTheDocument()
    })

    it('does not show action buttons container when both handlers are missing', () => {
      const { container } = render(
        <ResponsibilityCard
          {...defaultProps}
          onEdit={undefined}
          onDelete={undefined}
        />
      )

      // No buttons should exist
      expect(screen.queryByLabelText(/^Edit responsibility:/)).not.toBeInTheDocument()
      expect(screen.queryByLabelText(/^Delete responsibility:/)).not.toBeInTheDocument()
    })
  })
})
