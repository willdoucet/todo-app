import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import useDelayedFlag from '../../src/hooks/useDelayedFlag'

describe('useDelayedFlag', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('returns false when flag is true but delay has not elapsed', () => {
    const { result } = renderHook(() => useDelayedFlag(true, 200))
    expect(result.current).toBe(false)

    act(() => { vi.advanceTimersByTime(100) })
    expect(result.current).toBe(false)
  })

  it('returns true after flag has been true for at least delayMs', () => {
    const { result } = renderHook(() => useDelayedFlag(true, 200))
    expect(result.current).toBe(false)

    act(() => { vi.advanceTimersByTime(200) })
    expect(result.current).toBe(true)
  })

  it('returns false and cancels timer when flag goes false before delay', () => {
    const { result, rerender } = renderHook(
      ({ flag }) => useDelayedFlag(flag, 200),
      { initialProps: { flag: true } }
    )
    expect(result.current).toBe(false)

    // Flag goes false before timer fires
    act(() => { vi.advanceTimersByTime(100) })
    rerender({ flag: false })
    expect(result.current).toBe(false)

    // Advancing past original delay should NOT flip to true
    act(() => { vi.advanceTimersByTime(200) })
    expect(result.current).toBe(false)
  })

  it('does not warn on unmount before timer fires', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { unmount } = renderHook(() => useDelayedFlag(true, 200))

    // Unmount before timer fires
    unmount()
    act(() => { vi.advanceTimersByTime(300) })

    // No "setState on unmounted component" warning
    expect(consoleSpy).not.toHaveBeenCalled()
    consoleSpy.mockRestore()
  })
})
