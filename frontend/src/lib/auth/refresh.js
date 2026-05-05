// Single-flight refresh helper. The cold-boot loader and every 401 response
// interceptor share one in-flight Promise so concurrent callers cannot fan
// out into N parallel POST /auth/refresh requests against a backend that
// expects exactly one rotation per cookie generation.
//
// Uses raw axios (not the wrapped api instance) to skip the response
// interceptor — otherwise a refresh that itself returned 401 would recurse
// through the same interceptor that triggered it.

import axios from 'axios'
import { apiUrl } from '../apiBase'
import { tokenStore } from './tokenStore'

let inFlight = null
let loggingOut = false

const REFRESH_TIMEOUT_MS = 10_000

// Set by the logout mutation around its post. While true, performRefresh
// completes its network call but does NOT write the resulting token to
// tokenStore — closes the window where a post-click 401 elsewhere could
// trigger a refresh whose token lands after the user has signed out.
export function setLoggingOut(value) {
  loggingOut = value
}

export async function performRefresh() {
  if (inFlight) return inFlight
  inFlight = (async () => {
    try {
      const { data } = await axios.post(apiUrl('/auth/refresh'), null, {
        withCredentials: true,
        timeout: REFRESH_TIMEOUT_MS,
      })
      // Defensive: a backend bug or a rogue proxy that returns 200 with a
      // mangled body must not poison the in-memory token. Throw before any
      // side effect; the caller (loader / interceptor) classifies the
      // failure.
      if (typeof data?.access_token !== 'string') {
        throw new Error('refresh: malformed response')
      }
      // Discard the freshly minted token if the user is mid-logout.
      // performRefresh still resolves cleanly (so awaiting callers do not
      // throw a generic error); the caller treats "no token in store after
      // refresh" as the no-op outcome.
      if (loggingOut) {
        return
      }
      tokenStore.setToken(data.access_token)
    } finally {
      inFlight = null
    }
  })()
  return inFlight
}

// Used by the logout flow so a refresh response landing AFTER the logout
// click cannot resurrect the in-memory token. Returns immediately when no
// refresh is in flight; never throws (logout is best-effort locally even
// if the refresh promise rejected).
export async function waitForRefreshToSettle() {
  if (!inFlight) return
  try {
    await inFlight
  } catch {
    // Swallowed by design — logout proceeds regardless.
  }
}
