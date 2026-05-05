import { describe, it, expect, beforeEach, vi } from 'vitest'
import { tokenStore } from './tokenStore'

// Pin the module store contract: getSnapshot reflects setToken/clear,
// subscribers are notified on every mutation, and unsubscribe stops them.

describe('tokenStore', () => {
  beforeEach(() => {
    tokenStore.clear()
  })

  it('starts with a null token', () => {
    expect(tokenStore.getSnapshot()).toBeNull()
  })

  it('returns null from getServerSnapshot (CSR contract)', () => {
    expect(tokenStore.getServerSnapshot()).toBeNull()
  })

  it('reflects setToken in getSnapshot', () => {
    tokenStore.setToken('abc.def.ghi')
    expect(tokenStore.getSnapshot()).toBe('abc.def.ghi')
  })

  it('clear() sets snapshot back to null', () => {
    tokenStore.setToken('abc')
    tokenStore.clear()
    expect(tokenStore.getSnapshot()).toBeNull()
  })

  it('notifies subscribers on setToken', () => {
    const listener = vi.fn()
    tokenStore.subscribe(listener)
    tokenStore.setToken('abc')
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('notifies subscribers on clear', () => {
    tokenStore.setToken('abc')
    const listener = vi.fn()
    tokenStore.subscribe(listener)
    tokenStore.clear()
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('subscribe() returns an unsubscribe function that stops further notifications', () => {
    const listener = vi.fn()
    const unsubscribe = tokenStore.subscribe(listener)
    tokenStore.setToken('a')
    expect(listener).toHaveBeenCalledTimes(1)

    unsubscribe()
    tokenStore.setToken('b')
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('multiple subscribers all fire on a single setToken', () => {
    const a = vi.fn()
    const b = vi.fn()
    tokenStore.subscribe(a)
    tokenStore.subscribe(b)
    tokenStore.setToken('xyz')
    expect(a).toHaveBeenCalledTimes(1)
    expect(b).toHaveBeenCalledTimes(1)
  })

  it('handles StrictMode-style double subscribe/unsubscribe pairs', () => {
    const listener = vi.fn()
    const u1 = tokenStore.subscribe(listener)
    u1()
    const u2 = tokenStore.subscribe(listener)
    tokenStore.setToken('a')
    expect(listener).toHaveBeenCalledTimes(1)
    u2()
    tokenStore.setToken('b')
    expect(listener).toHaveBeenCalledTimes(1)
  })
})
