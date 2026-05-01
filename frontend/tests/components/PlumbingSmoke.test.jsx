// Pins the PlumbingShell button's three load-bearing branches: exact-match
// success, probe mismatch, and network error. Without this test, a future
// "treat non-null as success" change would silently undermine the entire
// point of Slice 5's split-origin probe — detecting that the cookie was
// echoed back EXACTLY, not just present in some form.
//
// Deleted in M5 PR #2 alongside PlumbingShell.jsx.

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import PlumbingShell from '../../src/PlumbingShell'
import { server } from '../mocks/server'

const API_BASE = 'http://api.example.test'

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', API_BASE)
})

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('PlumbingShell — Test plumbing button', () => {
  it('renders success when GET echoes the exact probe set by POST', async () => {
    server.use(
      http.post(`${API_BASE}/plumbing-test`, () =>
        HttpResponse.json({ set: true, probe: 'probe-value-abc123' }),
      ),
      http.get(`${API_BASE}/plumbing-test/read`, () =>
        HttpResponse.json({ value: 'probe-value-abc123' }),
      ),
    )

    render(<PlumbingShell />)
    await userEvent.click(screen.getByRole('button', { name: /test plumbing/i }))

    await waitFor(() => {
      expect(screen.getByTestId('plumbing-result')).toHaveTextContent(
        /round-trip succeeded/i,
      )
    })
  })

  it('renders mismatch failure when GET returns a different value', async () => {
    server.use(
      http.post(`${API_BASE}/plumbing-test`, () =>
        HttpResponse.json({ set: true, probe: 'sent-probe' }),
      ),
      http.get(`${API_BASE}/plumbing-test/read`, () =>
        HttpResponse.json({ value: 'a-different-probe' }),
      ),
    )

    render(<PlumbingShell />)
    await userEvent.click(screen.getByRole('button', { name: /test plumbing/i }))

    await waitFor(() => {
      expect(screen.getByTestId('plumbing-result')).toHaveTextContent(
        /probe mismatch/i,
      )
    })
  })

  it('renders cookie-missing failure when GET returns value: null', async () => {
    server.use(
      http.post(`${API_BASE}/plumbing-test`, () =>
        HttpResponse.json({ set: true, probe: 'sent-probe' }),
      ),
      http.get(`${API_BASE}/plumbing-test/read`, () =>
        HttpResponse.json({ value: null }),
      ),
    )

    render(<PlumbingShell />)
    await userEvent.click(screen.getByRole('button', { name: /test plumbing/i }))

    await waitFor(() => {
      expect(screen.getByTestId('plumbing-result')).toHaveTextContent(
        /cookie not echoed back/i,
      )
    })
  })

  it('renders network-error state when fetch throws', async () => {
    server.use(
      http.post(`${API_BASE}/plumbing-test`, () => HttpResponse.error()),
    )

    render(<PlumbingShell />)
    await userEvent.click(screen.getByRole('button', { name: /test plumbing/i }))

    await waitFor(() => {
      expect(screen.getByTestId('plumbing-result')).toHaveTextContent(
        /network error/i,
      )
    })
  })
})
