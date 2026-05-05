// React subscription wrapper around the module-scope tokenStore. The
// underlying source of truth lives outside the React tree (so axios can
// read it directly); useSyncExternalStore is React 18's purpose-built
// primitive for "external mutable thing the components need to render
// against."

import { useSyncExternalStore } from 'react'
import { tokenStore } from './tokenStore'

export function useAuth() {
  const accessToken = useSyncExternalStore(
    tokenStore.subscribe,
    tokenStore.getSnapshot,
    tokenStore.getServerSnapshot,
  )
  return { accessToken, isAuthenticated: accessToken !== null }
}
