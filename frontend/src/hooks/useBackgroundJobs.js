import { useQuery } from '@tanstack/react-query'
import { apiUrl } from '../lib/apiBase'
import { durationSince, parseServerTime, relativeTime } from '../lib/serverTime'

/**
 * The Background jobs reading for Settings (M8 item 15a), from the public `/healthz`.
 *
 * One query both surfaces call (the card and the top alert); TanStack dedupes them to one
 * request per interval. It is a raw `fetch`, not the authenticated API client: `/healthz` is
 * public, and a 421 or a CORS failure routed through `api.js`'s 401 handling would sign the
 * household out while they look at this card. It throws a plain `Error` on a non-2xx, which
 * `queryClient.js`'s `handle401` (axios errors only) ignores.
 *
 * Recorded exception to REVIEW_CHECKLIST (React / TanStack Query: "polling stops when the
 * pending state clears"): this is a liveness poll with no pending state to clear. It stops on
 * unmount and pauses while the tab is hidden (TanStack's default), which is the checklist's
 * underlying concern.
 */
export const HEALTHZ_QUERY_KEY = ['healthz']
export const POLL_MS = 30_000
const READING_MAX_AGE_MS = 120_000 // "Can't check" once the newest reading is older (2B)
// A request that hangs never fails, and a poll that never fails never advances the
// 2-minute cap; the timeout turns a hang into a failed poll.
const FETCH_TIMEOUT_MS = 10_000

async function fetchHealthz() {
  // An AbortController and a timer, not AbortSignal.timeout(): that is Safari 16 / Chrome 103,
  // and TECH_STACK → Browser Support promises Safari 14 and Chrome 90, where it would throw on
  // every poll and pin the card on "Can't check". The timer covers the body read too.
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  try {
    const response = await fetch(apiUrl('/healthz'), { cache: 'no-store', signal: controller.signal })
    if (!response.ok) throw new Error(`/healthz answered ${response.status}`)
    return await response.json()
  } finally {
    clearTimeout(timer)
  }
}

// "What this means" lines stay in the frontend, keyed by Celery task name (Eng review 4);
// labels come from the server. An unmapped task contributes no line of its own.
const CONSEQUENCES = {
  'app.tasks.sync_all_icloud_integrations': 'If you use iCloud sync, new or changed events may not show up yet.',
  'app.tasks.sync_all_reminders': 'If you use iCloud sync, reminder changes may not sync yet.',
  'app.tasks.hard_delete_expired_soft_deletes': "Nothing you'll notice yet.",
  'app.tasks.sweep_abandoned_uploads': "Nothing you'll notice yet.",
}
const NOTHING_YET = "Nothing you'll notice yet."
const HANDOFF = ' If this lasts more than an hour, tell whoever set up this app.'

/** "every hour" for 3600 s, "every N min" for another multiple of 60, else "every N sec". */
export function cadence(intervalS) {
  if (intervalS === 3600) return 'every hour'
  if (intervalS > 0 && intervalS % 60 === 0) return `every ${intervalS / 60} min`
  return `every ${intervalS} sec`
}

function isUsableRow(row) {
  return (
    row !== null &&
    typeof row === 'object' &&
    typeof row.task === 'string' &&
    typeof row.label === 'string' &&
    typeof row.interval_s === 'number' &&
    row.interval_s > 0 &&
    typeof row.stale === 'boolean' &&
    typeof row.write_error === 'boolean' &&
    (row.last_success_at === null || parseServerTime(row.last_success_at) !== null)
  )
}

const CANT_CHECK = {
  state: 1,
  tone: 'unknown',
  headline: "Can't check right now",
  lines: ['Trying again every 30 seconds.'],
  rows: [],
  alert: null,
}

/** What a row says follows that row's own values, never the card's state (15a). */
function rowView(row, now) {
  const succeeded = row.last_success_at !== null
  let text
  if (row.stale && row.write_error) text = "can't record runs"
  else if (row.stale) text = succeeded ? `last ran ${relativeTime(row.last_success_at, now)} · overdue` : "hasn't run yet · overdue"
  else if (!succeeded) text = `hasn't run yet · runs ${cadence(row.interval_s)}`
  else text = `ran ${relativeTime(row.last_success_at, now)}`
  const at = succeeded ? parseServerTime(row.last_success_at) : null
  return {
    task: row.task,
    label: row.label,
    text,
    overdue: row.stale, // only a stale row is red; a write_error on a fresh row changes nothing
    dateTime: at ? at.toISOString() : null,
    title: at ? at.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : null,
  }
}

/**
 * The Background jobs card's state from one `/healthz.jobs` reading.
 *
 * `now` is the server-aligned clock in epoch ms: `jobs.now` plus the time since the response
 * arrived, never `Date.now()` against a server timestamp, so a device with a wrong clock sees
 * the same state as every other (Eng review 4). Pure, and called on every render (not in a
 * TanStack `select`, which does not re-run while `data` is unchanged: a run of failed polls
 * must still age the reading into state 1).
 *
 * First match wins (15a). An unusable reading outranks everything, so an outage that takes
 * the database from web and worker together reads "Can't check", never "Stopped":
 *
 *   1 Can't check    no jobs / unavailable / malformed / newest reading > 2 min old
 *   2 Can't record   any stale row with write_error
 *   3 Stopped        every row stale
 *   4 Behind         some rows stale
 *   5 Waiting        a row that never ran, none stale
 *   6 Running        every row fresh
 *
 * State 2's line needs evidence that something stopped: every row stale AND some row without
 * write_error picks "Nothing has run…"; anything else is "They may still be running…",
 * because write_error is only ever stamped by a SUCCESS whose recording failed, so a row
 * carrying it ran inside its window (Eng review 5, 1A). A full set of flags does not prove the
 * worker is still up either: those rows are also a worker that died within 3× the shortest
 * flagged interval, so the copy stays "may" (Adversarial re-review, 2026-09-21).
 */
export function deriveJobsState(jobs, now) {
  if (jobs === null || typeof jobs !== 'object') return CANT_CHECK
  if (!['ok', 'stale', 'unavailable'].includes(jobs.read) || jobs.read === 'unavailable') return CANT_CHECK
  if (!Number.isFinite(now)) return CANT_CHECK
  const readAt = parseServerTime(jobs.read_at)
  if (!readAt) return CANT_CHECK
  if (!Array.isArray(jobs.rows) || jobs.rows.length === 0 || !jobs.rows.every(isUsableRow)) return CANT_CHECK
  if (now - readAt.getTime() > READING_MAX_AGE_MS) return CANT_CHECK

  const rows = jobs.rows
  const staleRows = rows.filter((r) => r.stale)
  const succeeded = rows.filter((r) => r.last_success_at !== null)
  const rowViews = rows.map((r) => rowView(r, now))

  if (staleRows.some((r) => r.write_error)) {
    const nothingRan = rows.every((r) => r.stale) && rows.some((r) => !r.write_error)
    return {
      state: 2,
      tone: 'bad',
      headline: "Can't record job runs",
      lines: [(nothingRan ? "Nothing has run, and the app can't record that either." : "They may still be running, but the app can't confirm it.") + HANDOFF],
      rows: rowViews,
      alert: "Background jobs can't be recorded",
    }
  }
  if (staleRows.length === rows.length) {
    const newest = succeeded.map((r) => r.last_success_at).sort((a, b) => parseServerTime(b) - parseServerTime(a))[0]
    return {
      state: 3,
      tone: 'bad',
      headline: newest ? `Nothing has run in ${durationSince(newest, now)}` : 'Nothing has run yet',
      lines: ["iCloud events and reminders won't sync until this is fixed." + HANDOFF],
      rows: rowViews,
      alert: 'Background jobs have stopped',
    }
  }
  if (staleRows.length > 0) {
    const all = [...new Set(staleRows.map((r) => CONSEQUENCES[r.task]).filter(Boolean))]
    const notable = all.filter((line) => line !== NOTHING_YET)
    const n = staleRows.length
    return {
      state: 4,
      tone: 'bad',
      headline: `${n} ${n === 1 ? 'job is' : 'jobs are'} behind schedule`,
      lines: notable.length ? notable : all,
      rows: rowViews,
      alert: n === 1 ? `${staleRows[0].label} is behind schedule` : `${n} background jobs are behind schedule`,
    }
  }
  const waitingOn = rows.length - succeeded.length
  if (waitingOn > 0) {
    return {
      state: 5,
      tone: 'unknown',
      headline: succeeded.length === 0 ? 'Waiting for the first runs' : `Waiting on ${waitingOn} ${waitingOn === 1 ? 'job' : 'jobs'}`,
      lines: [],
      rows: rowViews,
      alert: null,
    }
  }
  return { state: 6, tone: 'ok', headline: 'All running on schedule', lines: [], rows: rowViews, alert: null }
}

/** The status region's words for a state change: "Background jobs: all running on schedule." */
export function announcementFor(view) {
  return `Background jobs: ${view.headline.charAt(0).toLowerCase()}${view.headline.slice(1)}.`
}

/**
 * The card's view from the query's current values and the browser clock. Pure, so the
 * server-aligned clock, the 2-minute cap across failed polls and the footnote are testable.
 */
export function jobsViewFromQuery({ data, dataUpdatedAt, isError, errorUpdatedAt }, browserNow) {
  if (data === undefined) {
    return isError ? CANT_CHECK : { state: 0, loading: true }
  }
  const jobs = data && typeof data === 'object' ? data.jobs : undefined
  const serverNow = parseServerTime(jobs?.now)
  const now = serverNow ? serverNow.getTime() + (browserNow - dataUpdatedAt) : NaN
  const view = deriveJobsState(jobs, now)
  if (view.state === 1) return view
  const lastFetchFailed = isError && errorUpdatedAt >= dataUpdatedAt
  if (jobs.read === 'stale' || lastFetchFailed) {
    return { ...view, footnote: `Couldn't refresh · showing results from ${durationSince(jobs.read_at, now)} ago` }
  }
  return view
}

export default function useBackgroundJobs() {
  const query = useQuery({
    queryKey: HEALTHZ_QUERY_KEY,
    queryFn: fetchHealthz,
    refetchInterval: POLL_MS,
    staleTime: 0, // returning to Settings fetches at once instead of showing a cached reading
    retry: false,
  })
  // Derived on every render. The browser clock is read through TanStack's timestamp of the
  // latest fetch outcome, success or failure, which is what re-renders this card anyway (a
  // component may not read Date.now() during render: react-hooks/purity). A failed poll moves
  // that timestamp, so failed polls still age the reading into state 1.
  return jobsViewFromQuery(query, Math.max(query.dataUpdatedAt, query.errorUpdatedAt))
}
