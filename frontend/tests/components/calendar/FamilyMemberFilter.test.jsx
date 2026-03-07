import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FamilyMemberFilter from '../../../src/components/calendar/FamilyMemberFilter'

const mockMembers = [
  { id: 1, name: 'Everyone', is_system: true, color: '#D97452' },
  { id: 2, name: 'Alice', is_system: false, color: '#3B82F6' },
  { id: 3, name: 'Bob', is_system: false, color: '#EF4444' },
]

describe('FamilyMemberFilter', () => {
  it('renders one button per non-system family member', () => {
    const activeMembers = new Set([1, 2, 3])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(2)
  })

  it('excludes system members from rendering', () => {
    const activeMembers = new Set([1, 2, 3])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    expect(screen.queryByTitle('Everyone')).not.toBeInTheDocument()
    expect(screen.getByTitle('Alice')).toBeInTheDocument()
    expect(screen.getByTitle('Bob')).toBeInTheDocument()
  })

  it('shows first-letter initials for non-system members', () => {
    const activeMembers = new Set([1, 2, 3])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
  })

  it('marks active members with aria-pressed=true', () => {
    const activeMembers = new Set([1, 2])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    expect(screen.getByLabelText(/Hide Alice/)).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByLabelText(/Show Bob/)).toHaveAttribute('aria-pressed', 'false')
  })

  it('inactive members have opacity-40 class', () => {
    const activeMembers = new Set([1])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    const bobBtn = screen.getByTitle('Bob')
    expect(bobBtn.className).toMatch(/opacity-40/)
  })

  it('active members have full opacity (no opacity-40)', () => {
    const activeMembers = new Set([2])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    const aliceBtn = screen.getByTitle('Alice')
    expect(aliceBtn.className).not.toMatch(/opacity-40/)
  })

  it('pill has card-bg background', () => {
    const activeMembers = new Set([2])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    const activePill = screen.getByText('Alice')
    const inactivePill = screen.getByText('Bob')
    expect(activePill.className).toMatch(/bg-card-bg/)
    expect(inactivePill.className).toMatch(/bg-card-bg/)
  })

  it('pill has right border stripe in member color', () => {
    const activeMembers = new Set([2])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    const pill = screen.getByText('Alice')
    expect(pill.style.borderRightWidth).toBe('4px')
    expect(pill.style.borderRightStyle).toBe('solid')
    expect(pill.style.borderRightColor).toBe('rgb(59, 130, 246)')
  })

  it('calls onToggle with memberId on click', async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()
    const activeMembers = new Set([1, 2, 3])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={onToggle}
      />
    )
    await user.click(screen.getByTitle('Alice'))
    expect(onToggle).toHaveBeenCalledWith(2)
  })

  it('returns null when familyMembers is empty', () => {
    const { container } = render(
      <FamilyMemberFilter
        familyMembers={[]}
        activeMembers={new Set()}
        onToggle={vi.fn()}
      />
    )
    expect(container.innerHTML).toBe('')
  })

  it('returns null when familyMembers is null', () => {
    const { container } = render(
      <FamilyMemberFilter
        familyMembers={null}
        activeMembers={new Set()}
        onToggle={vi.fn()}
      />
    )
    expect(container.innerHTML).toBe('')
  })

  it('returns null when only system members exist', () => {
    const systemOnly = [{ id: 1, name: 'Everyone', is_system: true, color: '#D97452' }]
    const { container } = render(
      <FamilyMemberFilter
        familyMembers={systemOnly}
        activeMembers={new Set([1])}
        onToggle={vi.fn()}
      />
    )
    expect(container.innerHTML).toBe('')
  })
})
