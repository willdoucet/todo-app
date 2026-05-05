import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('../api', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

vi.mock('./refresh', () => ({
  performRefresh: vi.fn(),
  setLoggingOut: vi.fn(),
  waitForRefreshToSettle: vi.fn(),
}))

import { api } from '../api'
import { performRefresh, setLoggingOut, waitForRefreshToSettle } from './refresh'
import { tokenStore } from './tokenStore'
import { useLogoutMutation } from './queries'

function wrapper({ children }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

describe('useLogoutMutation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    tokenStore.setToken('old-token')
    waitForRefreshToSettle.mockResolvedValue(undefined)
    performRefresh.mockResolvedValue(undefined)
    api.post.mockResolvedValue({ data: null })
  })

  it('refreshes before posting logout so an expired access token can still revoke the refresh cookie', async () => {
    const { result } = renderHook(() => useLogoutMutation(), { wrapper })

    act(() => result.current.mutate())

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(waitForRefreshToSettle).toHaveBeenCalledTimes(1)
    expect(performRefresh).toHaveBeenCalledTimes(1)
    expect(setLoggingOut).toHaveBeenNthCalledWith(1, true)
    expect(api.post).toHaveBeenCalledWith('/auth/logout')
    expect(setLoggingOut).toHaveBeenLastCalledWith(false)
    expect(tokenStore.getSnapshot()).toBeNull()

    expect(waitForRefreshToSettle.mock.invocationCallOrder[0]).toBeLessThan(
      performRefresh.mock.invocationCallOrder[0],
    )
    expect(performRefresh.mock.invocationCallOrder[0]).toBeLessThan(
      setLoggingOut.mock.invocationCallOrder[0],
    )
    expect(setLoggingOut.mock.invocationCallOrder[0]).toBeLessThan(
      api.post.mock.invocationCallOrder[0],
    )
  })

  it('still posts logout and fail-closes locally when proactive refresh fails', async () => {
    performRefresh.mockRejectedValueOnce(new Error('refresh down'))
    const { result } = renderHook(() => useLogoutMutation(), { wrapper })

    act(() => result.current.mutate())

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.post).toHaveBeenCalledWith('/auth/logout')
    expect(tokenStore.getSnapshot()).toBeNull()
  })
})
