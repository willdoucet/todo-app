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
