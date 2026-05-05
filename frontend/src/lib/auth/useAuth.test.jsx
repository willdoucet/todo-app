import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { useAuth } from './useAuth'
import { tokenStore } from './tokenStore'

function Probe() {
  const { accessToken, isAuthenticated } = useAuth()
  return (
    <div>
      <span data-testid="token">{accessToken ?? 'null'}</span>
      <span data-testid="auth">{isAuthenticated ? 'yes' : 'no'}</span>
    </div>
  )
}

describe('useAuth', () => {
  beforeEach(() => {
    tokenStore.clear()
  })

  it('reflects the initial null token', () => {
    render(<Probe />)
    expect(screen.getByTestId('token')).toHaveTextContent('null')
    expect(screen.getByTestId('auth')).toHaveTextContent('no')
  })

  it('re-renders when the token is set after mount', () => {
    render(<Probe />)
    act(() => tokenStore.setToken('abc'))
    expect(screen.getByTestId('token')).toHaveTextContent('abc')
    expect(screen.getByTestId('auth')).toHaveTextContent('yes')
  })

  it('re-renders when the token is cleared', () => {
    tokenStore.setToken('abc')
    render(<Probe />)
    expect(screen.getByTestId('auth')).toHaveTextContent('yes')
    act(() => tokenStore.clear())
    expect(screen.getByTestId('auth')).toHaveTextContent('no')
  })
})
