// Entry-point wrapper that picks between the M2 plumbing shell and the M4
// data router based on VITE_M2_SHELL. Sits between main.jsx (which only
// owns createRoot/render) and the actual route tree, so the env-gate is
// unit-testable as a component instead of a side-effect at module load.
//
// M5 PR #2 deletes this whole file along with PlumbingShell when the M2
// shell goes away.

import { RouterProvider } from 'react-router-dom'
import PlumbingShell from './PlumbingShell'
import HydrateFallback from './lib/auth/HydrateFallback'
import { router } from './lib/router'
import { setRouter } from './lib/auth/redirect'

// Bind once at module-eval. Idempotent — safe even if AppEntry is
// imported multiple times in tests.
setRouter(router)

export default function AppEntry() {
  if (import.meta.env.VITE_M2_SHELL === 'true') {
    return <PlumbingShell />
  }
  return <RouterProvider router={router} fallbackElement={<HydrateFallback />} />
}
