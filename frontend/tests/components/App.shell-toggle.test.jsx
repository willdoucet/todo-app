// Pins both branches of the VITE_M2_SHELL env-gate in App.jsx. A future
// polarity flip (=== 'true' → !== 'true'), a typo ('TRUE' instead of
// 'true'), or a debug-forgotten unconditional return <PlumbingShell />
// would silently ship without a test like this; ditto a missing import.
//
// Page imports are stubbed because rendering the real CalendarPage tree
// would require DarkModeProvider/ToastProvider context that's wired in
// main.jsx, not App.jsx. The env-gate is App.jsx's job; pages are
// out-of-scope.
//
// Deleted in M5 PR #2 alongside PlumbingShell.jsx and the App.jsx guard.

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../../src/components/calendar/CalendarPage', () => ({
  default: () => <div>__CalendarPage_stub__</div>,
}))
vi.mock('../../src/pages/ListsPage', () => ({ default: () => null }))
vi.mock('../../src/pages/ResponsibilitiesPage', () => ({ default: () => null }))
vi.mock('../../src/pages/FamilyMembersPage', () => ({ default: () => null }))
vi.mock('../../src/pages/MealboardPage', () => ({ default: () => null }))

import App from '../../src/App'

describe('App VITE_M2_SHELL env-gate', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('renders PlumbingShell when VITE_M2_SHELL is the string "true"', () => {
    vi.stubEnv('VITE_M2_SHELL', 'true')
    render(<App />)
    expect(screen.getByText(/M2 plumbing alive/i)).toBeInTheDocument()
    expect(screen.queryByText('__CalendarPage_stub__')).not.toBeInTheDocument()
  })

  it('renders the Routes tree when VITE_M2_SHELL is unset', () => {
    vi.stubEnv('VITE_M2_SHELL', '')
    render(<App />, { wrapper: MemoryRouter })
    expect(screen.getByText('__CalendarPage_stub__')).toBeInTheDocument()
    expect(screen.queryByText(/M2 plumbing alive/i)).not.toBeInTheDocument()
  })
})
