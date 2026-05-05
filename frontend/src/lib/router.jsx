// Data router for the app. Two top-level decisions:
//
//   1. /auth is reachable WITHOUT the protected loader.
//   2. Every other route lives under a pathless protected layout whose
//      loader runs rootAuthLoader once per cold boot. New protected
//      pages are added as children — no per-route loader plumbing.

import {
  createBrowserRouter,
  Outlet,
  redirect,
} from 'react-router-dom'
import axios from 'axios'

import RootLayout from '../RootLayout'
import HydrateFallback from './auth/HydrateFallback'
import BootErrorScreen from './auth/BootErrorScreen'
import { tokenStore } from './auth/tokenStore'
import { performRefresh } from './auth/refresh'
import { isSafeReturnTo } from './auth/returnTo'

import CalendarPage from '../components/calendar/CalendarPage'
import ListsPage from '../pages/ListsPage'
import ResponsibilitiesPage from '../pages/ResponsibilitiesPage'
import FamilyMembersPage from '../pages/FamilyMembersPage'
import MealboardPage from '../pages/MealboardPage'
import AuthPortalPage from '../pages/AuthPortalPage'

// eslint-disable-next-line react-refresh/only-export-components
function ProtectedOutlet() {
  return <Outlet />
}

//        user navigates to / (or any protected route)
//                       │
//                       ▼
//                ┌─ tokenStore.getSnapshot() ─yes─▶ return null → render protected ✓
//                │   (already authenticated;
//                │    e.g. back/forward nav)
//                │
//                no (cold boot or post-clear)
//                │
//                ▼
//            performRefresh()  (single-flight; raw axios; 10s timeout)
//                       │
//        ┌──────────────┼──────────────┬───────────────────┐
//        │              │              │                   │
//        ▼              ▼              ▼                   ▼
//     success         401         5xx / network      malformed body
//        │              │         / timeout              │
//        ▼              ▼              │                   ▼
//   setToken      throw redirect       ▼              throw Error
//   return null   /auth?return_to= throw Response       (caught below)
//                 (path sanitized)   (status: 503)
//                                      │
//                                      ▼
//                               errorElement: BootErrorScreen
//                               "Can't reach the server. Retry."
export async function rootAuthLoader({ request }) {
  if (tokenStore.getSnapshot() !== null) return null

  try {
    await performRefresh()
    return null
  } catch (err) {
    const status = axios.isAxiosError(err) ? err.response?.status : undefined
    if (status === 401) {
      const url = new URL(request.url)
      const candidate = url.pathname + url.search
      const returnTo = isSafeReturnTo(candidate) ? candidate : '/'
      throw redirect(`/auth?return_to=${encodeURIComponent(returnTo)}`)
    }
    // Non-401 = infrastructure failure. Surface via errorElement so the
    // user sees BootErrorScreen, not a fake "you're logged out" screen.
    throw new Response('refresh failed', { status: 503 })
  }
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    hydrateFallbackElement: <HydrateFallback />,
    children: [
      { path: 'auth', element: <AuthPortalPage /> },
      {
        element: <ProtectedOutlet />,
        loader: rootAuthLoader,
        errorElement: <BootErrorScreen />,
        children: [
          { index: true, element: <CalendarPage /> },
          { path: 'lists', element: <ListsPage /> },
          { path: 'responsibilities', element: <ResponsibilitiesPage /> },
          { path: 'settings', element: <FamilyMembersPage /> },
          { path: 'mealboard/*', element: <MealboardPage /> },
        ],
      },
    ],
  },
])
