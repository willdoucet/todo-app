## Next.js

### API & trust boundaries
- Server-only secrets never appear in client components or `NEXT_PUBLIC_` variables.
- Server Actions validate input with a schema and check authorization inside the action; middleware is not the only gate.
- Route handlers set explicit caching and re-check auth; nothing relies on middleware having run.

### Rendering & state
- The client/server boundary is explicit; `'use client'` is as low in the tree as possible and no server component touches browser APIs.
- Caching is deliberate (`revalidate`, cache tags); every mutation invalidates the tags it affects.
- Dynamic routes validate params and call `notFound()` for missing records.
- Loading and error boundaries (`loading`, `error`, `not-found`) exist for every route segment that fetches.

### Query efficiency
- Data is fetched once in the server tree and passed down; sibling client components do not refetch it.
- Images go through `next/image` and fonts through `next/font`.

### Secrets & config
- Required env vars are validated at boot; a production build fails when one is missing.

### Testing
- Route handlers and Server Actions are tested directly; one e2e flow covers a mutation through the UI.
