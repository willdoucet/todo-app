import { StrictMode } from 'react'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../../mocks/server'
import { HEALTHZ_HEALTHY } from '../../mocks/handlers'
import { createQueryClient } from '../../../src/lib/queryClient'
import BackgroundJobsSection from '../../../src/components/settings/BackgroundJobsSection'
import BackgroundJobsAlert from '../../../src/components/settings/BackgroundJobsAlert'
import { HEALTHZ_QUERY_KEY } from '../../../src/hooks/useBackgroundJobs'
import { redirectToAuthOnce } from '../../../src/lib/auth/redirect'

vi.mock('../../../src/lib/auth/redirect', () => ({ redirectToAuthOnce: vi.fn(), setRouter: vi.fn() }))

// M8 item 15a. The ladder itself is unit-tested in tests/hooks/useBackgroundJobs.test.js;
// these pin what renders, the alert, the link, and the status region.
const HEALTHZ = 'http://localhost:8000/healthz'
const realTz = process.env.TZ
beforeAll(() => {
  process.env.TZ = 'America/Los_Angeles'
})
afterAll(() => {
  process.env.TZ = realTz
})

function serve(body, status = 200) {
  server.use(http.get(HEALTHZ, () => (status === 200 ? HttpResponse.json(body) : new HttpResponse(null, { status }))))
}

function withRows(mutate) {
  const body = structuredClone(HEALTHZ_HEALTHY)
  body.jobs.rows = body.jobs.rows.map((row, i) => ({ ...row, ...mutate(row, i) }))
  return body
}

function renderSettingsPieces() {
  const client = createQueryClient()
  const utils = render(
    <StrictMode>
      <QueryClientProvider client={client}>
        <h1>Settings</h1>
        <BackgroundJobsAlert />
        <BackgroundJobsSection />
      </QueryClientProvider>
    </StrictMode>
  )
  return { ...utils, client }
}

const status = () => screen.getByRole('status')
const card = () => screen.getByRole('region', { name: 'Background jobs' })

describe('BackgroundJobsSection', () => {
  it('state 6: the heading and description at once, then a green headline over four ages', async () => {
    renderSettingsPieces()
    expect(screen.getByRole('heading', { level: 2, name: 'Background jobs' })).toBeInTheDocument()
    expect(screen.getByText(/Work the app does on its own/)).toBeInTheDocument()

    const headline = await within(card()).findByText('All running on schedule')
    expect(headline.previousSibling).toHaveClass('bg-sage-500')
    expect(headline.previousSibling).toHaveAttribute('aria-hidden', 'true')
    const rows = within(card()).getAllByRole('term').map((dt) => [dt.textContent, dt.nextSibling.textContent])
    expect(rows).toEqual([
      ['iCloud calendar sync', 'ran 4 min ago'],
      ['iCloud reminders sync', 'ran 4 min ago'],
      ['Deleted item cleanup', 'ran 32 min ago'],
      ['Unused photo cleanup', 'ran 32 min ago'],
    ])
    const time = within(card()).getAllByText(/ran/)[0]
    expect(time.tagName).toBe('TIME')
    expect(time).toHaveAttribute('dateTime', '2026-09-21T16:58:03.000Z')
    expect(screen.queryByText(/See background jobs/)).not.toBeInTheDocument()
  })

  it('state 4: one line under the h1 names the job, with no banner, dismiss or alert role', async () => {
    serve(withRows((row) => (row.task.endsWith('sweep_abandoned_uploads') ? { stale: true, last_success_at: '2026-09-21T13:58:00Z' } : {})))
    renderSettingsPieces()

    const link = await screen.findByRole('link', { name: 'See background jobs' })
    const alert = link.closest('p')
    expect(alert).toHaveTextContent('Unused photo cleanup is behind schedule · See background jobs')
    expect(alert).not.toHaveAttribute('role')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(within(alert).queryByRole('button')).not.toBeInTheDocument()

    expect(within(card()).getByText('1 job is behind schedule').closest('p')).toHaveClass('text-red-600')
    expect(within(card()).getByText("Nothing you'll notice yet.")).toBeInTheDocument()
    const overdue = within(card()).getByText('last ran 3 hr ago · overdue')
    expect(overdue.closest('dd')).toHaveClass('text-red-600')
  })

  it('state 1: a /healthz without jobs (a PR1a backend) says it cannot check, hides the rows, raises no alert', async () => {
    serve({ status: 'ok' })
    renderSettingsPieces()
    expect(await within(card()).findByText("Can't check right now")).toBeInTheDocument()
    expect(within(card()).getByText('Trying again every 30 seconds.')).toBeInTheDocument()
    expect(within(card()).queryAllByRole('term')).toHaveLength(0)
    expect(screen.queryByText(/See background jobs/)).not.toBeInTheDocument()
  })

  it('a 421 from a mis-deployed origin lock is "can\'t check" and never signs anyone out', async () => {
    serve(null, 421)
    renderSettingsPieces()
    expect(await within(card()).findByText("Can't check right now")).toBeInTheDocument()
    expect(redirectToAuthOnce).not.toHaveBeenCalled()
  })

  it('fetches without credentials, even when the app holds a bearer', async () => {
    const seen = []
    server.use(http.get(HEALTHZ, ({ request }) => {
      seen.push(request.headers.get('authorization'))
      return HttpResponse.json(HEALTHZ_HEALTHY)
    }))
    renderSettingsPieces()
    await within(card()).findByText('All running on schedule')
    expect(seen.length).toBeGreaterThan(0)
    expect(seen.every((value) => value === null)).toBe(true)
  })

  it('never renders version or gate_break_glass, and works without them', async () => {
    const bare = structuredClone(HEALTHZ_HEALTHY)
    delete bare.version
    delete bare.gate_break_glass
    serve(bare)
    renderSettingsPieces()
    await within(card()).findByText('All running on schedule')
    expect(screen.queryByText(new RegExp(HEALTHZ_HEALTHY.version.slice(0, 7)))).not.toBeInTheDocument()
    expect(screen.queryByText(/break.glass/i)).not.toBeInTheDocument()
  })

  it('shows the last reading with a footnote while the refresher reports stale (2B)', async () => {
    serve({ ...HEALTHZ_HEALTHY, jobs: { ...HEALTHZ_HEALTHY.jobs, read: 'stale', read_at: '2026-09-21T17:01:40Z' } })
    renderSettingsPieces()
    expect(await within(card()).findByText("Couldn't refresh · showing results from 1 min ago")).toBeInTheDocument()
    expect(within(card()).getByText('All running on schedule')).toBeInTheDocument()
  })

  describe('loading', () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      server.use(http.get(HEALTHZ, () => new Promise(() => {}))) // never answers
    })
    afterEach(() => vi.useRealTimers())

    it('nothing in the body for 200 ms, then "Checking…"; the heading renders at once', async () => {
      renderSettingsPieces()
      expect(screen.getByRole('heading', { name: 'Background jobs' })).toBeInTheDocument()
      expect(screen.queryByText('Checking…')).not.toBeInTheDocument()
      await act(() => vi.advanceTimersByTimeAsync(199))
      expect(screen.queryByText('Checking…')).not.toBeInTheDocument()
      await act(() => vi.advanceTimersByTimeAsync(5))
      expect(screen.getByText('Checking…')).toBeInTheDocument()
    })
  })

  describe('the status region', () => {
    it('stays silent on mount, on the first reading, on an age change and inside one state', async () => {
      const { client } = renderSettingsPieces()
      await within(card()).findByText('All running on schedule')
      expect(status()).toBeEmptyDOMElement()

      // Same state, later ages: nothing announced.
      serve({ ...HEALTHZ_HEALTHY, jobs: { ...HEALTHZ_HEALTHY.jobs, now: '2026-09-21T17:03:40Z', read_at: '2026-09-21T17:03:11Z' } })
      await act(() => client.refetchQueries({ queryKey: HEALTHZ_QUERY_KEY }))
      await within(card()).findAllByText('ran 5 min ago')
      expect(status()).toBeEmptyDOMElement()
    })

    it('announces once when the state number changes, and not for a headline change inside state 5', async () => {
      serve(withRows(() => ({ last_success_at: null })))
      const { client } = renderSettingsPieces()
      await within(card()).findByText('Waiting for the first runs')

      serve(withRows((row, i) => (i < 2 ? {} : { last_success_at: null })))
      await act(() => client.refetchQueries({ queryKey: HEALTHZ_QUERY_KEY }))
      await within(card()).findByText('Waiting on 2 jobs')
      expect(status()).toBeEmptyDOMElement()

      serve(withRows((row) => (row.task.endsWith('sweep_abandoned_uploads') ? { stale: true } : {})))
      await act(() => client.refetchQueries({ queryKey: HEALTHZ_QUERY_KEY }))
      await within(card()).findByText('1 job is behind schedule')
      await waitFor(() => expect(status()).toHaveTextContent('Background jobs: 1 job is behind schedule.'))
    })
  })

  describe('"See background jobs"', () => {
    let scrolled
    beforeEach(() => {
      scrolled = []
      Element.prototype.scrollIntoView = function scrollIntoView(options) {
        scrolled.push([this.id, options])
      }
      serve(withRows((row) => (row.task.endsWith('sync_all_reminders') ? { stale: true } : {})))
    })
    afterEach(() => {
      delete Element.prototype.scrollIntoView
    })

    it('scrolls to the card and focuses its heading without touching the URL', async () => {
      const user = userEvent.setup()
      renderSettingsPieces()
      const link = await screen.findByRole('link', { name: 'See background jobs' })
      const before = window.location.href
      await user.click(link)
      expect(window.location.href).toBe(before)
      expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'Background jobs' }))
      expect(scrolled).toEqual([['background-jobs', { behavior: 'smooth', block: 'start' }]])
    })

    it('does not animate the scroll under prefers-reduced-motion', async () => {
      const real = window.matchMedia
      window.matchMedia = (query) => ({ matches: query.includes('reduce'), media: query, addEventListener() {}, removeEventListener() {} })
      try {
        const user = userEvent.setup()
        renderSettingsPieces()
        await user.click(await screen.findByRole('link', { name: 'See background jobs' }))
        expect(scrolled[0][1]).toEqual({ behavior: 'auto', block: 'start' })
      } finally {
        window.matchMedia = real
      }
    })
  })
})
