// Single shared axios instance for all backend API calls. Every former
// caller of `axios.<method>(${VITE_API_BASE_URL}/...)` migrates to
// `api.<method>('/...')`. The instance carries baseURL + withCredentials
// and adds two interceptors:
//
//   request  — injects `Authorization: Bearer <token>` from tokenStore
//   response — on 401, performs single-flight refresh and retries once.
//              On terminal refresh failure, the helper differentiates
//              "your session ended" (401) from "the backend is broken"
//              (5xx / network / timeout) and routes accordingly.

import axios from 'axios'
import { API_BASE_URL } from './apiBase'
import { tokenStore } from './auth/tokenStore'
import { performRefresh } from './auth/refresh'
import { redirectToAuthOnce } from './auth/redirect'

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = tokenStore.getSnapshot()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

//        api.get('/x')  ──▶  HTTP response
//                                  │
//                          ┌──── status? ────┐
//                          │                 │
//                         200               401
//                          │                 │
//                          ▼                 ▼
//                       return        ┌─ original.config undefined? ─yes─▶ throw original
//                                     │   (DNS / pre-flight failure)
//                                     no
//                                     │
//                                     ▼
//                              ┌─ url starts /auth/* ? ─yes─▶ throw original
//                              │   (login wrong-password, refresh recursion guard)
//                              no
//                              │
//                              ▼
//                              ┌─ original._retried already? ─yes─▶ throw original
//                              │   (infinite-loop guard)
//                              no
//                              │
//                              ▼
//                          original._retried = true
//                          performRefresh()        ◀── single-flight; concurrent
//                              │                       callers await same promise
//              ┌───────────────┼───────────────────┐
//              │               │                   │
//              ▼               ▼                   ▼
//           success          401            5xx / network / timeout
//              │               │                   │
//              ▼               ▼                   ▼
//           retry once     tokenStore.clear()  throw refreshError
//           with new       redirectToAuthOnce  (NO redirect — feature
//           Authorization  throw refreshError   sees infrastructure path)
api.interceptors.response.use(null, async (error) => {
  const original = error?.config
  // Pre-flight axios errors (request canceled, DNS failure before send)
  // come back with no `config`. Without this guard, original._retried = true
  // below throws a TypeError that masks the original error class.
  if (!original || error.response?.status !== 401 || original._retried) {
    throw error
  }
  // Don't refresh-loop on the auth endpoints themselves. A wrong-password
  // 401 from /auth/login propagates straight to the mutation's onError,
  // and /auth/refresh failures are owned by performRefresh's caller.
  if (original.url?.startsWith('/auth/')) {
    throw error
  }
  original._retried = true
  if (import.meta.env.DEV) {
    console.debug('[auth] 401 intercepted — running single-flight refresh', original.url)
  }
  try {
    await performRefresh()
    const next = tokenStore.getSnapshot()
    if (next) {
      original.headers = original.headers ?? {}
      original.headers.Authorization = `Bearer ${next}`
    }
    // `return await` so a rejection from the retry flows into the catch
    // block below — without await, the rejected Promise is returned to the
    // caller and the catch never sees retry-401s. Imperative callers (event
    // handlers awaiting api.* directly) would otherwise never redirect on
    // a stale-token retry.
    return await api(original)
  } catch (refreshError) {
    // Only auth-terminal refresh failures redirect. Non-401 refresh
    // failures (backend down, timeout, malformed response) stay as
    // server errors so the feature can show its normal error path.
    if (
      axios.isAxiosError(refreshError) &&
      refreshError.response?.status === 401
    ) {
      tokenStore.clear()
      redirectToAuthOnce()
    }
    throw refreshError
  }
})
