import { act, renderHook, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { delay, http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
import { createQueryClient } from '../../src/lib/queryClient'
import useBackgroundJobs, {
  POLL_MS,
  announcementFor,
  cadence,
  deriveJobsState,
  jobsViewFromQuery,
} from '../../src/hooks/useBackgroundJobs'

// M8 item 15a. Fixtures use the contract's real shape: job timestamps end in `Z`
// (`job_heartbeats` is timestamptz). The timezone is pinned to a non-UTC zone so a naive
// parse cannot pass by accident (LESSONS → "Parse API timestamps as UTC").
const realTz = process.env.TZ
beforeAll(() => {
  process.env.TZ = 'America/Los_Angeles'
})
afterAll(() => {
  process.env.TZ = realTz
})

const CAL = 'app.tasks.sync_all_icloud_integrations'
const REM = 'app.tasks.sync_all_reminders'
const DEL = 'app.tasks.hard_delete_expired_soft_deletes'
const SWEEP = 'app.tasks.sweep_abandoned_uploads'
const LABELS = {
  [CAL]: 'iCloud calendar sync',
  [REM]: 'iCloud reminders sync',
  [DEL]: 'Deleted item cleanup',
  [SWEEP]: 'Unused photo cleanup',
}
const INTERVAL = { [CAL]: 600, [REM]: 600, [DEL]: 3600, [SWEEP]: 3600 }
const NOW_ISO = '2026-09-21T17:02:40Z'
const NOW = Date.parse(NOW_ISO)
const minAgo = (m) => new Date(NOW - m * 60000).toISOString().replace(/\.\d{3}Z$/, 'Z')

// row(task, { age: minutes since last success | null, stale, err })
function row(task, { age = 4, stale = false, err = false } = {}) {
  return {
    task,
    label: LABELS[task],
    interval_s: INTERVAL[task],
    last_success_at: age === null ? null : minAgo(age),
    stale,
    write_error: err,
  }
}

function jobs(rows, { read = 'ok', readAt = minAgo(0.5) } = {}) {
  return { read, read_at: readAt, now: NOW_ISO, rows }
}

const all = (spec) => [CAL, REM, DEL, SWEEP].map((t) => row(t, typeof spec === 'function' ? spec(t) : spec))
const texts = (view) => view.rows.map((r) => r.text)

describe('deriveJobsState — the 15a precedence table', () => {
  it('6 Running: every row fresh', () => {
    const view = deriveJobsState(jobs([row(CAL, { age: 0.2 }), row(REM, { age: 4 }), row(DEL, { age: 32 }), row(SWEEP, { age: 32 })]), NOW)
    expect(view).toMatchObject({ state: 6, tone: 'ok', headline: 'All running on schedule', alert: null, lines: [] })
    expect(texts(view)).toEqual(['ran just now', 'ran 4 min ago', 'ran 32 min ago', 'ran 32 min ago'])
    expect(view.rows.every((r) => !r.overdue)).toBe(true)
  })

  it('6 Running even when a fresh row carries write_error', () => {
    const view = deriveJobsState(jobs([row(CAL), row(REM), row(DEL, { age: 20, err: true }), row(SWEEP)]), NOW)
    expect(view.state).toBe(6)
    expect(view.rows[2]).toMatchObject({ text: 'ran 20 min ago', overdue: false })
  })

  it('5 Waiting: every row NULL, inside its grace', () => {
    const view = deriveJobsState(jobs(all({ age: null })), NOW)
    expect(view).toMatchObject({ state: 5, tone: 'unknown', headline: 'Waiting for the first runs', alert: null })
    expect(texts(view)).toEqual([
      "hasn't run yet · runs every 10 min",
      "hasn't run yet · runs every 10 min",
      "hasn't run yet · runs every hour",
      "hasn't run yet · runs every hour",
    ])
  })

  it('5 Waiting on N jobs once any row has succeeded (never "Waiting for the first runs" after a success)', () => {
    const view = deriveJobsState(jobs(all((t) => ({ age: t === CAL || t === REM ? 2 : null }))), NOW)
    expect(view.headline).toBe('Waiting on 2 jobs')
    expect(texts(view)).toEqual(['ran 2 min ago', 'ran 2 min ago', "hasn't run yet · runs every hour", "hasn't run yet · runs every hour"])
    const one = deriveJobsState(jobs(all((t) => ({ age: t === SWEEP ? null : 2 }))), NOW)
    expect(one.headline).toBe('Waiting on 1 job')
  })

  it('4 Behind, one job: the alert names it', () => {
    const view = deriveJobsState(jobs(all((t) => (t === SWEEP ? { age: 184, stale: true } : { age: 4 }))), NOW)
    expect(view).toMatchObject({
      state: 4,
      tone: 'bad',
      headline: '1 job is behind schedule',
      alert: 'Unused photo cleanup is behind schedule',
      lines: ["Nothing you'll notice yet."],
    })
    expect(view.rows[3]).toMatchObject({ text: 'last ran 3 hr ago · overdue', overdue: true })
  })

  it('4 Behind, several: calendar line first, "Nothing you\'ll notice yet." only when it is the sole line', () => {
    const view = deriveJobsState(jobs(all((t) => (t === CAL || t === SWEEP ? { age: 184, stale: true } : { age: 4 }))), NOW)
    expect(view.headline).toBe('2 jobs are behind schedule')
    expect(view.alert).toBe('2 background jobs are behind schedule')
    expect(view.lines).toEqual(['If you use iCloud sync, new or changed events may not show up yet.'])
    const both = deriveJobsState(jobs(all((t) => (t === DEL || t === SWEEP ? { age: 184, stale: true } : { age: 4 }))), NOW)
    expect(both.lines).toEqual(["Nothing you'll notice yet."])
  })

  it('4 Behind with never-run rows past their grace', () => {
    const view = deriveJobsState(jobs(all((t) => (t === DEL || t === SWEEP ? { age: null, stale: true } : { age: 3 }))), NOW)
    expect(view.state).toBe(4)
    expect(texts(view).slice(2)).toEqual(["hasn't run yet · overdue", "hasn't run yet · overdue"])
  })

  it('3 Stopped: the headline is a duration, never "… ago"', () => {
    const view = deriveJobsState(jobs(all((t) => ({ age: t === DEL || t === SWEEP ? 190 : 181, stale: true }))), NOW)
    expect(view).toMatchObject({
      state: 3,
      headline: 'Nothing has run in 3 hr',
      alert: 'Background jobs have stopped',
      lines: ["iCloud events and reminders won't sync until this is fixed. If this lasts more than an hour, tell whoever set up this app."],
    })
    expect(texts(view)).toEqual(Array(4).fill('last ran 3 hr ago · overdue'))
  })

  it('3 Stopped with nothing ever run', () => {
    const view = deriveJobsState(jobs(all({ age: null, stale: true })), NOW)
    expect(view.headline).toBe('Nothing has run yet')
    expect(texts(view)).toEqual(Array(4).fill("hasn't run yet · overdue"))
  })

  describe('2 Can\'t record — the line keys on write_error, which only a run can stamp (Eng review 5, 1A)', () => {
    const MAY = "They may still be running, but the app can't confirm it. If this lasts more than an hour, tell whoever set up this app."
    const NOTHING = "Nothing has run, and the app can't record that either. If this lasts more than an hour, tell whoever set up this app."

    it('(a) a stale flagged row and some row not stale → "may still be running"; a fresh flagged row reads normally', () => {
      const view = deriveJobsState(
        jobs([row(CAL, { age: 48, stale: true, err: true }), row(REM, { age: 48, stale: true, err: true }),
          row(DEL, { age: 95, err: true }), row(SWEEP, { age: 95, err: true })]),
        NOW
      )
      expect(view).toMatchObject({ state: 2, headline: "Can't record job runs", lines: [MAY], alert: "Background jobs can't be recorded" })
      expect(view.rows.map((r) => [r.text, r.overdue])).toEqual([
        ["can't record runs", true],
        ["can't record runs", true],
        ['ran 1 hr ago', false],
        ['ran 1 hr ago', false],
      ])
    })

    it('(b) every row stale and flagged → still "may still be running"', () => {
      const view = deriveJobsState(jobs(all({ age: 240, stale: true, err: true })), NOW)
      expect(view.lines).toEqual([MAY])
    })

    it('(b) again with no recorded success at all → "may still be running", never "Nothing has run yet"', () => {
      const view = deriveJobsState(jobs(all({ age: null, stale: true, err: true })), NOW)
      expect(view).toMatchObject({ state: 2, lines: [MAY] })
    })

    it('(c) every row stale and one unflagged → "Nothing has run…"; no stale row renders as fresh', () => {
      const view = deriveJobsState(jobs(all((t) => ({ age: 240, stale: true, err: t !== SWEEP }))), NOW)
      expect(view).toMatchObject({ state: 2, headline: "Can't record job runs", lines: [NOTHING] })
      expect(view.rows.map((r) => [r.text, r.overdue])).toEqual([
        ["can't record runs", true],
        ["can't record runs", true],
        ["can't record runs", true],
        ['last ran 4 hr ago · overdue', true],
      ])
    })
  })

  describe('1 Can\'t check — an unusable reading outranks everything', () => {
    const healthy = () => jobs(all({ age: 4 }))
    it.each([
      ['no jobs key', undefined],
      ['jobs is null', null],
      ['read is unavailable', { read: 'unavailable', read_at: null, now: NOW_ISO, rows: [] }],
      ['read is unknown', { ...jobs(all({})), read: 'maybe' }],
      ['read_at is null', { ...jobs(all({})), read_at: null }],
      ['rows is not an array', { ...jobs(all({})), rows: {} }],
      ['read ok with no rows', jobs([])],
      ['a row lacks stale', jobs([...all({}).slice(1), { ...row(CAL), stale: undefined }])],
      ['stale is not a boolean', jobs([...all({}).slice(1), { ...row(CAL), stale: 'false' }])],
      ['a row lacks interval_s', jobs([...all({}).slice(1), { ...row(CAL), interval_s: undefined }])],
      ['the newest reading is over 2 min old', jobs(all({}), { readAt: minAgo(2.5) })],
    ])('%s', (_, body) => {
      const view = deriveJobsState(body, NOW)
      expect(view).toMatchObject({ state: 1, tone: 'unknown', headline: "Can't check right now", rows: [], alert: null })
      expect(view.lines).toEqual(['Trying again every 30 seconds.'])
    })

    it('an unparseable server now', () => {
      expect(deriveJobsState(healthy(), NaN).state).toBe(1)
    })

    it('every row stale but the reading 5 min old → state 1, never Stopped', () => {
      expect(deriveJobsState(jobs(all({ age: 300, stale: true }), { readAt: minAgo(5) }), NOW).state).toBe(1)
    })

    it('a reading exactly 2 min old is still usable', () => {
      expect(deriveJobsState(jobs(all({ age: 4 }), { readAt: minAgo(2) }), NOW).state).toBe(6)
    })
  })

  it('rows keep the server order and label, and carry a machine-readable time', () => {
    const view = deriveJobsState(jobs(all({ age: 4 })), NOW)
    expect(view.rows.map((r) => r.label)).toEqual(Object.values(LABELS))
    expect(view.rows[0].dateTime).toBe('2026-09-21T16:58:40.000Z')
    expect(view.rows[0].title).toMatch(/9:58/) // the viewer's zone (Los Angeles here), not UTC
  })
})

describe('cadence', () => {
  it.each([
    [3600, 'every hour'],
    [600, 'every 10 min'],
    [7200, 'every 120 min'],
    [90, 'every 90 sec'],
  ])('%i → %s', (s, text) => expect(cadence(s)).toBe(text))
})

describe('announcementFor', () => {
  it('reads the headline as a sentence', () => {
    expect(announcementFor({ headline: '1 job is behind schedule' })).toBe('Background jobs: 1 job is behind schedule.')
    expect(announcementFor({ headline: 'All running on schedule' })).toBe('Background jobs: all running on schedule.')
  })
})

describe('jobsViewFromQuery — one clock, the server\'s', () => {
  const body = { status: 'ok', jobs: jobs(all({ age: 4 }), { readAt: minAgo(0.5) }) }
  const arrived = 1_000_000

  it('loading before the first response; state 1 when the first fetch failed', () => {
    expect(jobsViewFromQuery({ data: undefined, isError: false }, arrived)).toMatchObject({ state: 0, loading: true })
    expect(jobsViewFromQuery({ data: undefined, isError: true }, arrived).state).toBe(1)
  })

  it.each([
    ['10 min fast', 10 * 60000],
    ['10 min slow', -10 * 60000],
    ['right', 0],
  ])('a browser clock %s sees the same state, ages and footnote', (_, skew) => {
    const view = jobsViewFromQuery({ data: body, dataUpdatedAt: arrived + skew, isError: false }, arrived + skew + 30000)
    expect(view.state).toBe(6)
    expect(view.rows[0].text).toBe('ran 4 min ago')
    expect(view.footnote).toBeUndefined()
  })

  it('failed polls do not freeze the 2-minute cap: the same data ages into state 1', () => {
    const q = { data: body, dataUpdatedAt: arrived, isError: true, errorUpdatedAt: arrived + 90000 }
    const soon = jobsViewFromQuery(q, arrived + 60000)
    expect(soon.state).toBe(6)
    expect(soon.footnote).toBe("Couldn't refresh · showing results from 1 min ago")
    expect(jobsViewFromQuery({ ...q, errorUpdatedAt: arrived + 180000 }, arrived + 180000).state).toBe(1)
  })

  it('a reading the refresher marked stale shows the last reading with the footnote', () => {
    const stale = { status: 'ok', jobs: { ...body.jobs, read: 'stale', read_at: minAgo(1) } }
    const view = jobsViewFromQuery({ data: stale, dataUpdatedAt: arrived, isError: false }, arrived)
    expect(view).toMatchObject({ state: 6, footnote: "Couldn't refresh · showing results from 1 min ago" })
  })

  it('a /healthz without jobs (a PR1a backend) is state 1 and does not throw', () => {
    expect(jobsViewFromQuery({ data: { status: 'ok' }, dataUpdatedAt: arrived, isError: false }, arrived).state).toBe(1)
  })
})

describe('useBackgroundJobs — the poll', () => {
  let requests
  const healthz = () => ({ status: 'ok', version: 'abc123', gate_break_glass: false, jobs: jobs(all({ age: 4 })) })

  beforeEach(() => {
    requests = []
    vi.useFakeTimers({ shouldAdvanceTime: true })
    server.use(
      http.get('http://localhost:8000/healthz', ({ request }) => {
        requests.push(request)
        if (requests.length === 2) return new HttpResponse(null, { status: 500 })
        return HttpResponse.json(healthz())
      })
    )
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function renderJobsHook() {
    const client = createQueryClient()
    const wrapper = ({ children }) => createElement(QueryClientProvider, { client }, children)
    return renderHook(() => useBackgroundJobs(), { wrapper })
  }

  it('fetches /healthz without credentials, every 30 s, keeps going after a failure, and stops on unmount', async () => {
    const { result, unmount } = renderJobsHook()
    await waitFor(() => expect(result.current.state).toBeDefined())
    await waitFor(() => expect(requests).toHaveLength(1))
    expect(requests[0].headers.get('authorization')).toBeNull()

    await act(() => vi.advanceTimersByTimeAsync(POLL_MS)) // this poll fails (500)
    await waitFor(() => expect(requests).toHaveLength(2))
    await act(() => vi.advanceTimersByTimeAsync(POLL_MS)) // and polling carries on
    await waitFor(() => expect(requests).toHaveLength(3))

    unmount()
    await act(() => vi.advanceTimersByTimeAsync(POLL_MS * 3))
    expect(requests).toHaveLength(3)
  })

  it('failed polls age the last good reading into state 1 within the 2-minute cap', async () => {
    let calls = 0
    server.use(
      http.get('http://localhost:8000/healthz', () => {
        calls += 1
        return calls === 1 ? HttpResponse.json(healthz()) : new HttpResponse(null, { status: 503 })
      })
    )
    const { result } = renderJobsHook()
    await waitFor(() => expect(result.current.state).toBe(6))
    await act(() => vi.advanceTimersByTimeAsync(POLL_MS))
    await waitFor(() => expect(result.current.footnote).toMatch(/^Couldn't refresh/))
    await act(() => vi.advanceTimersByTimeAsync(POLL_MS * 5)) // three minutes of failures, data unchanged
    await waitFor(() => expect(result.current.state).toBe(1))
  })

  it('works where AbortSignal.timeout does not exist (Safari 14–15, Chrome < 103; TECH_STACK → Browser Support)', async () => {
    const timeout = AbortSignal.timeout
    delete AbortSignal.timeout
    try {
      expect(AbortSignal.timeout).toBeUndefined() // negative control: the API really is gone
      const { result } = renderJobsHook()
      await waitFor(() => expect(result.current.state).toBe(6))
    } finally {
      AbortSignal.timeout = timeout
    }
  })

  it('a /healthz that hangs settles as a failed poll after 10 s, so hung polls still age the reading into state 1', async () => {
    let calls = 0
    server.use(
      http.get('http://localhost:8000/healthz', async () => {
        calls += 1
        if (calls === 1) return HttpResponse.json(healthz())
        await delay('infinite')
      })
    )
    const { result } = renderJobsHook()
    await waitFor(() => expect(result.current.state).toBe(6))
    await act(() => vi.advanceTimersByTimeAsync(POLL_MS)) // the next poll hangs
    expect(result.current.footnote).toBeUndefined()
    await act(() => vi.advanceTimersByTimeAsync(10_000)) // the fetch timeout fires
    await waitFor(() => expect(result.current.footnote).toMatch(/^Couldn't refresh/))
    await act(() => vi.advanceTimersByTimeAsync(POLL_MS * 5)) // every poll hangs, then times out
    await waitFor(() => expect(result.current.state).toBe(1))
  })
})
