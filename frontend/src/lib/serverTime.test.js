import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { parseServerTime, relativeTime, durationSince } from './serverTime'

// Pinned to a non-UTC zone, or a naive-UTC bug passes in UTC CI either way
// (LESSONS → "Parse API timestamps as UTC").
const realTz = process.env.TZ
beforeAll(() => {
  process.env.TZ = 'America/Los_Angeles'
})
afterAll(() => {
  process.env.TZ = realTz
})

const NOW = Date.parse('2026-09-21T17:02:40Z')

describe('parseServerTime', () => {
  it('reads a naive timestamp as UTC (legacy columns), not local time', () => {
    expect(parseServerTime('2026-09-21T16:57:40').toISOString()).toBe('2026-09-21T16:57:40.000Z')
  })

  it('keeps a timestamp that carries its zone (the job_heartbeats Z form)', () => {
    expect(parseServerTime('2026-09-21T16:57:40Z').toISOString()).toBe('2026-09-21T16:57:40.000Z')
    expect(parseServerTime('2026-09-21T09:57:40-07:00').toISOString()).toBe('2026-09-21T16:57:40.000Z')
  })

  it.each([null, undefined, '', 'not a time'])('returns null for %p', (value) => {
    expect(parseServerTime(value)).toBeNull()
  })
})

describe('relativeTime', () => {
  it.each([
    ['2026-09-21T17:02:10Z', 'just now'],
    ['2026-09-21T16:58:40Z', '4 min ago'],
    ['2026-09-21T14:02:40Z', '3 hr ago'],
    ['2026-09-19T17:02:40Z', '2 days ago'],
    ['2026-09-20T17:02:40Z', '1 day ago'],
  ])('%s → %s against a passed-in now', (iso, words) => {
    expect(relativeTime(iso, NOW)).toBe(words)
  })

  it('uses the now it is given, not the browser clock', () => {
    expect(relativeTime('2026-09-21T16:58:40Z', new Date(NOW + 10 * 60000))).toBe('14 min ago')
  })

  it('says never without a timestamp', () => {
    expect(relativeTime(null, NOW)).toBe('never')
  })
})

describe('durationSince', () => {
  it.each([
    ['2026-09-21T16:17:40Z', '45 min'],
    ['2026-09-21T14:02:40Z', '3 hr'],
    ['2026-09-19T17:02:40Z', '2 days'],
    ['2026-09-20T17:02:40Z', '1 day'],
    ['2026-09-21T17:02:30Z', '1 min'],
  ])('%s → %s (never "… ago")', (iso, words) => {
    expect(durationSince(iso, NOW)).toBe(words)
  })

  it('returns null without a timestamp', () => {
    expect(durationSince(null, NOW)).toBeNull()
  })
})
