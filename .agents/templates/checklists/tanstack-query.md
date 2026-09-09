## TanStack Query

### Rendering & state
- Query keys are arrays containing every variable the fetch depends on.
- Mutations invalidate or set the affected keys in `onSuccess`; optimistic updates snapshot in `onMutate` and roll back in `onError`.
- 401 handling lives once in `QueryCache` / `MutationCache` and triggers a single redirect, not per caller.
- Dependent queries use `enabled`; no fetch runs with an undefined parameter.
- `refetchInterval` is a function that returns `false` once the pending state clears.
- Boot-time data (auth status) is loaded by a router loader or a top-level query, not by every page.

### Query efficiency
- `staleTime` is set deliberately per query; heavy lists disable `refetchOnWindowFocus`.
- Lists and details share a normalized key prefix so one invalidation covers both.

### Testing
- Tests wrap components in a fresh `QueryClient` with `retry: false`; no client is shared across tests.
- The rollback path of every optimistic mutation has a test.
