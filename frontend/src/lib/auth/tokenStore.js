// In-memory access token store. Module scope (one instance per JS context)
// so axios reads it directly without going through React. React subscribes
// via useSyncExternalStore — same source of truth for both worlds.
//
// Never write the token to localStorage or sessionStorage: a stolen access
// token grants the bearer N minutes of full API access. Page reload performs
// /auth/refresh to re-mint, paid-for by the HttpOnly refresh cookie that JS
// cannot read.

let accessToken = null
const listeners = new Set()

export const tokenStore = {
  getSnapshot: () => accessToken,
  // CSR app — no SSR / no hydration mismatch path. Returning null satisfies
  // the useSyncExternalStore contract without claiming the token is "absent
  // on the server" semantically.
  getServerSnapshot: () => null,
  subscribe: (listener) => {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  setToken: (token) => {
    accessToken = token
    // Fan out synchronously so React schedules its re-render in the same
    // microtask the caller initiated.
    listeners.forEach((l) => l())
  },
  clear: () => tokenStore.setToken(null),
}
