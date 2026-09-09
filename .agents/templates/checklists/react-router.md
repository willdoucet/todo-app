## React Router

### Rendering & state
- Data router: auth gating is a loader on a pathless protected layout that runs once; new pages go under it unless APP_FLOW.md marks them public.
- `HydrateFallback` and an `errorElement` exist for the boot sequence; a non-401 boot failure shows a retry, not a blank page.
- The router instance is set once and late-bound for redirects triggered outside components (HTTP client, query cache).
- Nested feature routes are owned by the feature's page shell, not the root route table.

### API & trust boundaries
- `return_to` and similar redirect targets are validated as same-origin relative paths (open-redirect defense) before navigation.
- Route params are validated before use; unknown routes render a 404 page.

### Testing
- Route tests render through a memory router so loaders, redirects, and error elements run.
- One test proves an unauthenticated visit to a protected route lands on the sign-in route with the original path preserved.
