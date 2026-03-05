/**
 * Tests for timezone conversion utilities in calendarUtils.
 */

import { describe, it, expect } from 'vitest'
import { convertTime, convertEventForDisplay } from './calendarUtils'

describe('convertTime', () => {
  it('returns unchanged when fromTz === toTz', () => {
    const result = convertTime('2026-03-15', '12:00', 'America/New_York', 'America/New_York')
    expect(result).toEqual({ date: '2026-03-15', time: '12:00' })
  })

  it('returns unchanged when fromTz is null', () => {
    const result = convertTime('2026-03-15', '12:00', null, 'America/New_York')
    expect(result).toEqual({ date: '2026-03-15', time: '12:00' })
  })

  it('returns unchanged when timeStr is null', () => {
    const result = convertTime('2026-03-15', null, 'America/New_York', 'America/Los_Angeles')
    expect(result).toEqual({ date: '2026-03-15', time: null })
  })

  it('converts EST to PST (3 hour difference in winter)', () => {
    // 12:00 PM EST = 9:00 AM PST (January, no DST)
    const result = convertTime('2026-01-15', '12:00', 'America/New_York', 'America/Los_Angeles')
    expect(result.date).toBe('2026-01-15')
    expect(result.time).toBe('09:00')
  })

  it('converts PST to EST (3 hour difference in winter)', () => {
    // 9:00 AM PST = 12:00 PM EST
    const result = convertTime('2026-01-15', '09:00', 'America/Los_Angeles', 'America/New_York')
    expect(result.date).toBe('2026-01-15')
    expect(result.time).toBe('12:00')
  })

  it('handles date boundary crossing (late night PST → next day EST)', () => {
    // 11:00 PM PST = 2:00 AM EST next day
    const result = convertTime('2026-01-15', '23:00', 'America/Los_Angeles', 'America/New_York')
    expect(result.date).toBe('2026-01-16')
    expect(result.time).toBe('02:00')
  })

  it('handles date boundary crossing (early morning EST → previous day PST)', () => {
    // 1:00 AM EST = 10:00 PM PST previous day
    const result = convertTime('2026-01-15', '01:00', 'America/New_York', 'America/Los_Angeles')
    expect(result.date).toBe('2026-01-14')
    expect(result.time).toBe('22:00')
  })

  it('handles DST transition (March, EDT vs PDT)', () => {
    // After spring forward: EDT (UTC-4) and PDT (UTC-7), still 3 hours diff
    // 12:00 PM EDT = 9:00 AM PDT
    const result = convertTime('2026-06-15', '12:00', 'America/New_York', 'America/Los_Angeles')
    expect(result.date).toBe('2026-06-15')
    expect(result.time).toBe('09:00')
  })
})

describe('convertEventForDisplay', () => {
  it('passes through all-day events unchanged', () => {
    const event = {
      id: 1,
      date: '2026-03-15',
      all_day: true,
      start_time: null,
      end_time: null,
      timezone: 'America/New_York',
    }
    const result = convertEventForDisplay(event, 'America/Los_Angeles')
    expect(result).toBe(event)  // Same reference, not copied
  })

  it('passes through events without timezone', () => {
    const event = {
      id: 1,
      date: '2026-03-15',
      all_day: false,
      start_time: '12:00',
      end_time: '13:00',
      timezone: null,
    }
    const result = convertEventForDisplay(event, 'America/Los_Angeles')
    expect(result).toBe(event)
  })

  it('passes through events with same timezone', () => {
    const event = {
      id: 1,
      date: '2026-03-15',
      all_day: false,
      start_time: '12:00',
      end_time: '13:00',
      timezone: 'America/New_York',
    }
    const result = convertEventForDisplay(event, 'America/New_York')
    expect(result).toBe(event)
  })

  it('converts event times from event timezone to display timezone', () => {
    const event = {
      id: 1,
      title: 'Meeting',
      date: '2026-01-15',
      all_day: false,
      start_time: '12:00',
      end_time: '13:00',
      timezone: 'America/New_York',
    }
    const result = convertEventForDisplay(event, 'America/Los_Angeles')

    expect(result.id).toBe(1)
    expect(result.title).toBe('Meeting')
    expect(result.date).toBe('2026-01-15')
    expect(result.start_time).toBe('09:00')
    expect(result.end_time).toBe('10:00')
    // Original timezone preserved in the copy
    expect(result.timezone).toBe('America/New_York')
  })
})
