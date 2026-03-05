import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarSelector from '../../../src/components/settings/CalendarSelector'

const mockCalendars = [
  { url: 'https://caldav.icloud.com/cal1', name: 'Personal', color: '#FF0000', event_count: 5, already_synced_by: null },
  { url: 'https://caldav.icloud.com/cal2', name: 'Work', color: '#0000FF', event_count: 12, already_synced_by: null },
  { url: 'https://caldav.icloud.com/cal3', name: 'Shared', color: '#00FF00', event_count: 3, already_synced_by: 'Alice' },
]

describe('CalendarSelector', () => {
  it('renders all calendars with names and event counts', () => {
    render(
      <CalendarSelector
        calendars={mockCalendars}
        selected={[]}
        onChange={() => {}}
      />
    )

    expect(screen.getByText('Personal')).toBeInTheDocument()
    expect(screen.getByText('Work')).toBeInTheDocument()
    expect(screen.getByText('Shared')).toBeInTheDocument()
    expect(screen.getByText('5 events')).toBeInTheDocument()
    expect(screen.getByText('12 events')).toBeInTheDocument()
    expect(screen.getByText('3 events')).toBeInTheDocument()
  })

  it('shows shared calendar warning', () => {
    render(
      <CalendarSelector
        calendars={mockCalendars}
        selected={[]}
        onChange={() => {}}
      />
    )

    expect(screen.getByText("Already synced from Alice's account")).toBeInTheDocument()
  })

  it('calls onChange when checkbox is toggled', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <CalendarSelector
        calendars={mockCalendars}
        selected={[]}
        onChange={onChange}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])

    expect(onChange).toHaveBeenCalledWith(['https://caldav.icloud.com/cal1'])
  })

  it('unchecks a selected calendar', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <CalendarSelector
        calendars={mockCalendars}
        selected={['https://caldav.icloud.com/cal1', 'https://caldav.icloud.com/cal2']}
        onChange={onChange}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])

    expect(onChange).toHaveBeenCalledWith(['https://caldav.icloud.com/cal2'])
  })

  it('shows Select All / Deselect All toggle', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <CalendarSelector
        calendars={mockCalendars}
        selected={[]}
        onChange={onChange}
      />
    )

    const selectAll = screen.getByText('Select All')
    await user.click(selectAll)

    expect(onChange).toHaveBeenCalledWith(mockCalendars.map((c) => c.url))
  })

  it('shows hint when nothing is selected', () => {
    render(
      <CalendarSelector
        calendars={mockCalendars}
        selected={[]}
        onChange={() => {}}
      />
    )

    expect(screen.getByText('Select at least one calendar to sync.')).toBeInTheDocument()
  })
})
