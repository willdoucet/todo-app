// One-shot auth redirect. Both the axios response interceptor and the
// TanStack Query Cache/MutationCache onError hooks delegate here so a
// terminal refresh 401 produces exactly one navigation no matter how many
// concurrent failing requests observe the failure.
//
// The router is bound late (from main.jsx, after both this module and
// router.jsx have been imported) — keeps router.jsx free to depend on
// page components that themselves depend on the QueryClient.

import { tokenStore } from './tokenStore'

let _router = null
export function setRouter(router) {
  _router = router
}

let redirecting = false

export function redirectToAuthOnce() {
  if (redirecting) return

  // Already on /auth? The mount effect on AuthPortalPage will reset the
  // guard; no redundant navigation needed.
  if (typeof window !== 'undefined' && window.location.pathname.startsWith('/auth')) {
    return
  }

  // Self-heal when the router has not been bound yet — happens during the
  // narrow window between module evaluation and main.jsx's setRouter() call,
  // and in unit tests that exercise this helper without bootstrapping the
  // full data router. Without this guard, redirecting would latch true and
  // every subsequent call would no-op forever (no /auth mount to fire
  // resetRedirectGuard).
  if (!_router) {
    tokenStore.clear()
    if (import.meta.env.DEV) {
      console.warn(
        '[auth] redirectToAuthOnce called before setRouter(); skipping navigation'
      )
    }
    return
  }

  redirecting = true
  tokenStore.clear()
  const returnTo =
    typeof window !== 'undefined'
      ? window.location.pathname + window.location.search
      : '/'
  _router.navigate(`/auth?return_to=${encodeURIComponent(returnTo)}`)
}

export function resetRedirectGuard() {
  redirecting = false
}

// Test helper — mirrors the shape used by other module-scope stores in the
// repo. Production code never calls this; only test setup/teardown.
export function __resetRedirectModuleState() {
  _router = null
  redirecting = false
}
