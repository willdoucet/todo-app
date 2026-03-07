import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ColorPicker from '../../../src/components/shared/ColorPicker'
import { FAMILY_MEMBER_COLORS } from '../../../src/constants/familyColors'

describe('ColorPicker', () => {
  it('renders all 10 color circles', () => {
    render(<ColorPicker selectedColor="#D4695A" onSelect={() => {}} />)
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(10)
  })

  it('marks selected circle with aria-pressed', () => {
    render(<ColorPicker selectedColor="#D4695A" onSelect={() => {}} />)
    const selected = screen.getByLabelText('Soft Red')
    expect(selected).toHaveAttribute('aria-pressed', 'true')

    const notSelected = screen.getByLabelText('Teal')
    expect(notSelected).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onSelect with hex when clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<ColorPicker selectedColor="#D4695A" onSelect={onSelect} />)

    await user.click(screen.getByLabelText('Sage'))
    expect(onSelect).toHaveBeenCalledWith('#5E9E6B')
  })

  it('has accessible aria-labels for all colors', () => {
    render(<ColorPicker selectedColor="#D4695A" onSelect={() => {}} />)
    for (const { name } of FAMILY_MEMBER_COLORS) {
      expect(screen.getByLabelText(name)).toBeInTheDocument()
    }
  })

  it('renders disabled colors with disabled attribute and aria-disabled', () => {
    render(
      <ColorPicker
        selectedColor="#D4695A"
        onSelect={() => {}}
        disabledColors={['#5E9E6B', '#4A9E9E']}
      />
    )
    const sage = screen.getByLabelText('Sage')
    expect(sage).toBeDisabled()
    expect(sage).toHaveAttribute('aria-disabled', 'true')

    const teal = screen.getByLabelText('Teal')
    expect(teal).toBeDisabled()
    expect(teal).toHaveAttribute('aria-disabled', 'true')

    // Non-disabled color should not have aria-disabled
    const softRed = screen.getByLabelText('Soft Red')
    expect(softRed).not.toBeDisabled()
    expect(softRed).not.toHaveAttribute('aria-disabled')
  })

  it('does not call onSelect when clicking a disabled color', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(
      <ColorPicker
        selectedColor="#D4695A"
        onSelect={onSelect}
        disabledColors={['#5E9E6B']}
      />
    )

    await user.click(screen.getByLabelText('Sage'))
    expect(onSelect).not.toHaveBeenCalled()
  })
})
