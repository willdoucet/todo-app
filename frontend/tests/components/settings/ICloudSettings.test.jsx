import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../mocks/server'
import ICloudSettings from '../../../src/components/settings/ICloudSettings'

const API_BASE = 'http://localhost:8000'

const mockIntegration = {
  id: 1,
  family_member_id: 2,
  provider: 'icloud',
  email: 'alice@icloud.com',
  status: 'ACTIVE',
  last_sync_at: new Date(Date.now() - 5 * 60000).toISOString(), // 5 min ago
  last_error: null,
  sync_range_past_days: 30,
  sync_range_future_days: 90,
  selected_calendars: ['https://caldav.icloud.com/cal1'],
  family_member: { id: 2, name: 'Alice', is_system: false, color: '#3B82F6' },
  created_at: '2026-01-15T10:00:00Z',
  updated_at: null,
}

describe('ICloudSettings', () => {
  describe('no integrations', () => {
    it('shows connect button when no integrations exist', async () => {
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText('Connect iCloud Calendar')).toBeInTheDocument()
      })
    })
  })

  describe('connected state', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/integrations/`, () => {
          return HttpResponse.json([mockIntegration])
        })
      )
    })

    it('shows integration card with email and status', async () => {
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText('alice@icloud.com')).toBeInTheDocument()
      })
      expect(screen.getByText('Active')).toBeInTheDocument()
      expect(screen.getByText('Sync Now')).toBeInTheDocument()
      expect(screen.getByText('Disconnect')).toBeInTheDocument()
    })

    it('shows family member name', async () => {
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText(/Alice/)).toBeInTheDocument()
      })
    })

    it('shows last synced time', async () => {
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText(/Last synced 5 min ago/)).toBeInTheDocument()
      })
    })
  })

  // The API serializes `last_sync_at` with no timezone — it is a `timestamp
  // without time zone` column holding UTC — so these fixtures drop the trailing
  // Z that `toISOString()` adds and `mockIntegration` above carries. Pinning a
  // non-UTC zone is what makes the bug visible: read as local time, a recent
  // sync lands in the future and everything looks fresh.
  describe('sync freshness', () => {
    const realTz = process.env.TZ

    beforeAll(() => {
      process.env.TZ = 'America/Los_Angeles'
    })

    afterAll(() => {
      process.env.TZ = realTz
    })

    const naiveUtc = (msAgo) =>
      new Date(Date.now() - msAgo).toISOString().replace(/\.\d+Z$/, '')

    const serveIntegration = (overrides) =>
      server.use(
        http.get(`${API_BASE}/integrations/`, () =>
          HttpResponse.json([{ ...mockIntegration, ...overrides }])
        )
      )

    it('reads a timestamp with no timezone as UTC, not local time', async () => {
      serveIntegration({ last_sync_at: naiveUtc(5 * 60000) })
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText(/Last synced 5 min ago/)).toBeInTheDocument()
      })
      expect(screen.queryByText(/sync overdue/)).not.toBeInTheDocument()
    })

    it('marks a sync older than three cycles as overdue', async () => {
      serveIntegration({ last_sync_at: naiveUtc(3 * 3600000) })
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(
          screen.getByText(/Last synced 3 hr ago · sync overdue/)
        ).toBeInTheDocument()
      })
    })

    it('says nothing when an integration has never synced', async () => {
      serveIntegration({ last_sync_at: null })
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText('alice@icloud.com')).toBeInTheDocument()
      })
      expect(screen.queryByText(/Last synced/)).not.toBeInTheDocument()
    })
  })

  describe('error state', () => {
    it('shows error message when integration has error', async () => {
      server.use(
        http.get(`${API_BASE}/integrations/`, () => {
          return HttpResponse.json([{
            ...mockIntegration,
            status: 'ERROR',
            last_error: 'Authentication failed',
          }])
        })
      )

      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument()
      })
      expect(screen.getByText('Authentication failed')).toBeInTheDocument()
    })
  })

  describe('connection flow', () => {
    it('shows credentials form when Connect clicked', async () => {
      const user = userEvent.setup()
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText('Connect iCloud Calendar')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Connect iCloud Calendar'))

      expect(screen.getByText('Family Member')).toBeInTheDocument()
      expect(screen.getByText('iCloud Email')).toBeInTheDocument()
      expect(screen.getByText('App-Specific Password')).toBeInTheDocument()
      expect(screen.getByText('How to generate an app-specific password')).toBeInTheDocument()
    })

    it('hides form when Cancel clicked', async () => {
      const user = userEvent.setup()
      render(<ICloudSettings />)

      await waitFor(() => {
        expect(screen.getByText('Connect iCloud Calendar')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Connect iCloud Calendar'))
      expect(screen.getByText('iCloud Email')).toBeInTheDocument()

      await user.click(screen.getByText('Cancel'))

      await waitFor(() => {
        expect(screen.queryByText('iCloud Email')).not.toBeInTheDocument()
      })
    })
  })

  describe('syncing state', () => {
    it('shows Syncing status and disables Sync Now button', async () => {
      server.use(
        http.get(`${API_BASE}/integrations/`, () => {
          return HttpResponse.json([{
            ...mockIntegration,
            status: 'SYNCING',
          }])
        })
      )

      render(<ICloudSettings />)

      await waitFor(() => {
        const syncTexts = screen.getAllByText('Syncing...')
        expect(syncTexts.length).toBeGreaterThanOrEqual(1)
      })

      // Sync Now button should show "Syncing..." and be disabled
      const syncButton = screen.getAllByText('Syncing...').find(
        (el) => el.tagName === 'BUTTON'
      )
      expect(syncButton).toBeDisabled()
    })
  })
})
