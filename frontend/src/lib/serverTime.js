/**
 * Timestamps from the API, parsed and described in words. Shared by the iCloud
 * "Last synced" line and the Background jobs card (M8 item 15), so the naive-UTC
 * bug logged 2026-09-11 has exactly one place it can be fixed.
 */

/**
 * Parse a timestamp from the API.
 *
 * Legacy columns such as `last_sync_at` are `timestamp without time zone`
 * holding UTC, which serialize with no offset (`2026-09-11T20:07:34`).
 * `new Date()` reads that form as LOCAL time, so every relative time was skewed
 * by the viewer's offset — in PDT a sync from five hours ago rendered "just
 * now". A value that carries a zone (the `job_heartbeats` timestamps end in `Z`)
 * is parsed as given. Same naive-UTC trap as the meal-planner undo window
 * (MealPlannerView.jsx).
 */
export function parseServerTime(value) {
  if (!value) return null
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value)
  const parsed = new Date(hasZone ? value : `${value}Z`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function toMs(now) {
  return now instanceof Date ? now.getTime() : now
}

/**
 * "5 min ago", "3 hr ago", "2 days ago", "just now" under a minute, "never"
 * without a timestamp. `now` (a Date or epoch ms) defaults to the browser clock;
 * the Background jobs card passes a server-aligned one instead (Eng review 4).
 */
export function relativeTime(isoString, now = Date.now()) {
  const then = parseServerTime(isoString)
  if (!then) return 'never'
  const diffMin = Math.floor((toMs(now) - then.getTime()) / 60000)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin} min ago`

  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr} hr ago`

  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`
}

/**
 * How long since `isoString`, as a duration rather than a time ago: "45 min",
 * "3 hr", "2 days". For "Nothing has run in 3 hr" (Design review 7), where
 * `relativeTime` would read "…in 3 hr ago". Never less than "1 min".
 */
export function durationSince(isoString, now = Date.now()) {
  const then = parseServerTime(isoString)
  if (!then) return null
  const diffMin = Math.max(1, Math.floor((toMs(now) - then.getTime()) / 60000))
  if (diffMin < 60) return `${diffMin} min`

  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr} hr`

  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay} day${diffDay !== 1 ? 's' : ''}`
}
