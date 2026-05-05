// TanStack Query is the app's state-cache for /auth/* and (later) read
// queries. The cache hooks delegate terminal-auth failures to the same
// one-shot redirect helper that the axios interceptor uses, so a 401
// observed by either path produces exactly one navigation.

import axios from 'axios'
import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query'
import { redirectToAuthOnce } from './auth/redirect'

// Narrow guard: only true axios 401s should logout the user. A backend
// hiccup (500), a network failure (no response), or a non-axios error that
// happens to carry a 401-shaped property must not flip auth state.
function handle401(error) {
  if (!axios.isAxiosError(error)) return
  if (error.response?.status !== 401) return
  redirectToAuthOnce()
}

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
    queryCache: new QueryCache({ onError: handle401 }),
    mutationCache: new MutationCache({ onError: handle401 }),
  })
}

// Exported for testing; production code should prefer the factory above
// so each test gets a fresh isolated cache.
export { handle401 }
