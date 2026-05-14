import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import './index.css'
import HydrateFallback from './lib/auth/HydrateFallback'
import { router } from './lib/router'
import { setRouter } from './lib/auth/redirect'

// Bind once at module-eval. Idempotent — safe even if main.jsx is
// imported multiple times in tests.
setRouter(router)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider router={router} fallbackElement={<HydrateFallback />} />
  </StrictMode>,
)
