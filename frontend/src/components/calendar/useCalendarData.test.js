/**
 * Tests for useCalendarData hook — auto-refetch when events have PENDING_PUSH.
 *
 * Bug: After saving an iCloud event, sync_status is PENDING_PUSH. The Celery
 * task runs ~30s later and sets SYNCED, but the frontend never re-fetches,
 * so "Syncing..." badge stays forever.
 *
 * Fix: useCalendarData should auto-poll when any event has PENDING_PUSH.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import axios from 'axios'

vi.mock('axios')

import useCalendarData from './useCalendarData'

describe('useCalendarData', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  const syncedEvent = {
    id: 1,
    title: 'Golf',
    source: 'ICLOUD',
    sync_status: 'SYNCED',
    date: '2026-03-09',
    assigned_to: null,
  }

  const pendingEvent = {
    ...syncedEvent,
    sync_status: 'PENDING_PUSH',
  }

  function mockApiResponses(events) {
    axios.get.mockImplementation((url) => {
      if (url.includes('/calendar-events')) {
        return Promise.resolve({ data: events })
      }
      if (url.includes('/tasks')) {
        return Promise.resolve({ data: [] })
      }
      if (url.includes('/family-members')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.resolve({ data: [] })
    })
  }

  async function flushPromises() {
    await act(async () => {
      await vi.runAllTimersAsync()
    })
  }

  it('does not schedule refetch when all events are SYNCED', async () => {
    mockApiResponses([syncedEvent])

    const { result } = renderHook(() =>
      useCalendarData('2026-03-01', '2026-03-31')
    )

    await flushPromises()
    expect(result.current.events[0].sync_status).toBe('SYNCED')

    const callCount = axios.get.mock.calls.length

    // Advance well past poll interval
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000)
    })

    // No additional fetches
    expect(axios.get.mock.calls.length).toBe(callCount)
  })

  it('auto-refetches when events have PENDING_PUSH status', async () => {
    // First fetch returns PENDING_PUSH, second returns SYNCED
    let fetchCount = 0
    axios.get.mockImplementation((url) => {
      if (url.includes('/calendar-events')) {
        fetchCount++
        return Promise.resolve({ data: [fetchCount <= 1 ? pendingEvent : syncedEvent] })
      }
      if (url.includes('/tasks')) {
        return Promise.resolve({ data: [] })
      }
      if (url.includes('/family-members')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.resolve({ data: [] })
    })

    const { result } = renderHook(() =>
      useCalendarData('2026-03-01', '2026-03-31')
    )

    // Wait for initial fetch
    await flushPromises()
    expect(result.current.events[0].sync_status).toBe('PENDING_PUSH')

    // Advance past the poll interval to trigger auto-refetch
    await act(async () => {
      await vi.advanceTimersByTimeAsync(11000)
    })

    // After auto-refetch, should be SYNCED
    expect(result.current.events[0].sync_status).toBe('SYNCED')
  })

  it('stops polling once all events are SYNCED', async () => {
    let fetchCount = 0
    axios.get.mockImplementation((url) => {
      if (url.includes('/calendar-events')) {
        fetchCount++
        return Promise.resolve({ data: [fetchCount <= 1 ? pendingEvent : syncedEvent] })
      }
      if (url.includes('/tasks')) {
        return Promise.resolve({ data: [] })
      }
      if (url.includes('/family-members')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.resolve({ data: [] })
    })

    const { result } = renderHook(() =>
      useCalendarData('2026-03-01', '2026-03-31')
    )

    await flushPromises()

    // Advance to trigger refetch (PENDING_PUSH → SYNCED)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(11000)
    })

    expect(result.current.events[0].sync_status).toBe('SYNCED')
    const callCountAfterSync = axios.get.mock.calls.length

    // Advance again — should NOT trigger more fetches
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000)
    })

    expect(axios.get.mock.calls.length).toBe(callCountAfterSync)
  })
})
