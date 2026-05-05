// SC #39 — VITE_M2_SHELL=true bypasses the data router entirely. Pins both
// branches of the env-gate that now lives in AppEntry.jsx (lifted out of the
// deleted App.jsx). M5 PR #2 deletes this test alongside PlumbingShell + the
// AppEntry gate.

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'

const { routerProviderSpy } = vi.hoisted(() => ({
  routerProviderSpy: vi.fn(),
}))

vi.mock('../../src/lib/router', () => ({
  router: { navigate: vi.fn() },
}))
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    RouterProvider: (props) => {
      routerProviderSpy(props)
      return <div>__RouterProvider_stub__</div>
    },
  }
})

import AppEntry from '../../src/AppEntry'

describe('AppEntry VITE_M2_SHELL env-gate', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    routerProviderSpy.mockClear()
  })

  it('renders PlumbingShell when VITE_M2_SHELL is the string "true"', () => {
    vi.stubEnv('VITE_M2_SHELL', 'true')
    render(<AppEntry />)
    expect(screen.getByText(/M2 plumbing alive/i)).toBeInTheDocument()
    expect(screen.queryByText('__RouterProvider_stub__')).not.toBeInTheDocument()
  })

  it('renders the data router when VITE_M2_SHELL is unset', () => {
    vi.stubEnv('VITE_M2_SHELL', '')
    render(<AppEntry />)
    expect(screen.getByText('__RouterProvider_stub__')).toBeInTheDocument()
    expect(screen.queryByText(/M2 plumbing alive/i)).not.toBeInTheDocument()
  })

  it('passes HydrateFallback as the CSR router fallback', () => {
    vi.stubEnv('VITE_M2_SHELL', '')
    render(<AppEntry />)
    expect(routerProviderSpy).toHaveBeenCalledWith(
      expect.objectContaining({ fallbackElement: expect.any(Object) })
    )
  })
})
