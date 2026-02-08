import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MonthView from '../../../src/components/calendar/MonthView'
import { formatDateKey } from '../../../src/components/calendar/calendarUtils'

const mockFamilyMembers = [
  { id: 1, name: 'Everyone', is_system: true, color: '#D97452' },
  { id: 2, name: 'Alice', is_system: false, color: '#3B82F6' },
]

const today = new Date()
const todayKey = formatDateKey(today)

const mockTasks = [
  {
    id: 1,
    title: 'Buy groceries',
    due_date: todayKey,
    completed: false,
    assigned_to: 2,
    family_member: mockFamilyMembers[1],
  },
]

const mockEvents = [
  {
    id: 1,
    title: 'Team meeting',
    date: todayKey,
    start_time: '09:00',
    end_time: '10:00',
    all_day: false,
    assigned_to: 2,
    family_member: mockFamilyMembers[1],
  },
]

const defaultProps = {
  currentDate: new Date(2026, 1, 1), // February 2026
  tasks: [],
  events: [],
  familyMembers: mockFamilyMembers,
  selectedDate: null,
  onSelectDate: vi.fn(),
  onViewDay: vi.fn(),
  onQuickAddTask: vi.fn(),
  onQuickAddEvent: vi.fn(),
  isMobile: false,
}

function renderMonthView(overrides = {}) {
  const props = { ...defaultProps, ...overrides }
  return render(<MonthView {...props} />)
}

describe('MonthView', () => {
  describe('day-of-week headers', () => {
    it('renders 7 day headers (desktop)', () => {
      renderMonthView()
      expect(screen.getByText('Sun')).toBeInTheDocument()
      expect(screen.getByText('Mon')).toBeInTheDocument()
      expect(screen.getByText('Tue')).toBeInTheDocument()
      expect(screen.getByText('Wed')).toBeInTheDocument()
      expect(screen.getByText('Thu')).toBeInTheDocument()
      expect(screen.getByText('Fri')).toBeInTheDocument()
      expect(screen.getByText('Sat')).toBeInTheDocument()
    })

    it('renders single-letter headers on mobile', () => {
      renderMonthView({ isMobile: true })
      // S, M, T, W, T, F, S — but there are duplicates, so just check "S" appears
      const headers = screen.getAllByText('S')
      expect(headers.length).toBeGreaterThanOrEqual(2) // Sun and Sat
    })
  })

  describe('grid cells', () => {
    it('renders 42 day cells', () => {
      const { container } = renderMonthView()
      // The cell grid has border class; header grid has mb-1 class
      const cellGrid = container.querySelector('.grid.grid-cols-7.border')
      const cells = cellGrid.querySelectorAll(':scope > div')
      expect(cells).toHaveLength(42)
    })

    it('shows day numbers', () => {
      renderMonthView()
      // February 2026 has 28 days; "1" appears twice (Feb 1 + March 1 padding)
      const ones = screen.getAllByText('1')
      expect(ones.length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('28')).toBeInTheDocument()
    })
  })

  describe('today highlight', () => {
    it('highlights today with terracotta background', () => {
      renderMonthView({ currentDate: today })
      const todayNumber = today.getDate().toString()
      // Find the today span with the highlight class
      const spans = screen.getAllByText(todayNumber)
      const todaySpan = spans.find((el) =>
        el.className.includes('bg-terracotta-500')
      )
      expect(todaySpan).toBeTruthy()
    })
  })

  describe('colored dots', () => {
    it('renders dots when day has tasks or events', () => {
      const { container } = renderMonthView({
        currentDate: today,
        tasks: mockTasks,
        events: mockEvents,
      })
      // Dots are rendered as small spans with backgroundColor style
      const dots = container.querySelectorAll('span[style*="background-color"]')
      expect(dots.length).toBeGreaterThan(0)
    })
  })

  describe('mobile mode', () => {
    it('calls onSelectDate when a cell is tapped', async () => {
      const user = userEvent.setup()
      const onSelectDate = vi.fn()
      renderMonthView({
        currentDate: new Date(2026, 1, 1),
        isMobile: true,
        onSelectDate,
      })
      // Click on day "15"
      await user.click(screen.getByText('15'))
      expect(onSelectDate).toHaveBeenCalled()
      const calledDate = onSelectDate.mock.calls[0][0]
      expect(calledDate.getDate()).toBe(15)
    })

    it('shows MobileDayList when a date is selected', () => {
      const selectedDate = new Date(2026, 1, 15)
      renderMonthView({
        currentDate: new Date(2026, 1, 1),
        isMobile: true,
        selectedDate,
        tasks: [],
        events: [],
      })
      // MobileDayList renders the day heading
      expect(screen.getByText(/Sunday, Feb 15/)).toBeInTheDocument()
    })

    it('does not show MobileDayList when no date selected', () => {
      renderMonthView({
        isMobile: true,
        selectedDate: null,
      })
      expect(screen.queryByText(/No events or tasks/)).not.toBeInTheDocument()
    })
  })

  describe('desktop mode', () => {
    it('does not call onSelectDate on cell click', async () => {
      const user = userEvent.setup()
      const onSelectDate = vi.fn()
      renderMonthView({
        currentDate: new Date(2026, 1, 1),
        isMobile: false,
        onSelectDate,
      })
      await user.click(screen.getByText('15'))
      expect(onSelectDate).not.toHaveBeenCalled()
    })

    it('shows quick-add popover with "New Task" and "New Event" when clicking an empty day', async () => {
      const user = userEvent.setup()
      renderMonthView({
        currentDate: new Date(2026, 1, 1),
        isMobile: false,
        tasks: [],
        events: [],
      })
      // Click on an empty day (day 15 has no tasks or events)
      await user.click(screen.getByText('15'))

      // Should show the quick-add popover with both options
      expect(screen.getByText('New Task')).toBeInTheDocument()
      expect(screen.getByText('New Event')).toBeInTheDocument()
    })

    it('calls onQuickAddTask when "New Task" is clicked in quick-add popover', async () => {
      const user = userEvent.setup()
      const onQuickAddTask = vi.fn()
      renderMonthView({
        currentDate: new Date(2026, 1, 1),
        isMobile: false,
        tasks: [],
        events: [],
        onQuickAddTask,
      })
      await user.click(screen.getByText('15'))
      await user.click(screen.getByText('New Task'))
      expect(onQuickAddTask).toHaveBeenCalled()
    })

    it('calls onQuickAddEvent when "New Event" is clicked in quick-add popover', async () => {
      const user = userEvent.setup()
      const onQuickAddEvent = vi.fn()
      renderMonthView({
        currentDate: new Date(2026, 1, 1),
        isMobile: false,
        tasks: [],
        events: [],
        onQuickAddEvent,
      })
      await user.click(screen.getByText('15'))
      await user.click(screen.getByText('New Event'))
      expect(onQuickAddEvent).toHaveBeenCalled()
    })
  })
})
