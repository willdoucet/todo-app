import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FamilyMemberFilter from '../../../src/components/calendar/FamilyMemberFilter'

const mockMembers = [
  { id: 1, name: 'Everyone', is_system: true, color: '#D97452' },
  { id: 2, name: 'Alice', is_system: false, color: '#3B82F6' },
  { id: 3, name: 'Bob', is_system: false, color: '#EF4444' },
]

describe('FamilyMemberFilter', () => {
  it('renders one button per family member', () => {
    const activeMembers = new Set([1, 2, 3])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(3)
  })

  it('shows first-letter initials', () => {
    const activeMembers = new Set([1, 2, 3])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    expect(screen.getByText('E')).toBeInTheDocument()
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
  })

  it('shows member name in title attribute', () => {
    const activeMembers = new Set([1, 2, 3])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    expect(screen.getByTitle('Alice')).toBeInTheDocument()
    expect(screen.getByTitle('Bob')).toBeInTheDocument()
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
    expect(screen.getByLabelText(/Hide Everyone/)).toHaveAttribute('aria-pressed', 'true')
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

  it('active members have ring styling', () => {
    const activeMembers = new Set([2])
    render(
      <FamilyMemberFilter
        familyMembers={mockMembers}
        activeMembers={activeMembers}
        onToggle={vi.fn()}
      />
    )
    const aliceBtn = screen.getByTitle('Alice')
    expect(aliceBtn.className).toMatch(/ring-2/)
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
})
