## Vite

### Secrets & config
- Only `VITE_`-prefixed variables reach the client bundle; nothing secret is ever `VITE_`-prefixed.
- Exactly one module reads `import.meta.env` for the API base URL; every caller imports from it.
- A production build throws when the API base URL is unset instead of silently falling back to localhost.

### Rendering & state
- HMR artifacts are recognized before debugging: a stack line number larger than the file, a `?t=` cache-buster in the URL, or a "useEffect changed size between renders" warning means reload first.

### Operations
- End-to-end and visual suites run against `vite preview` (the production build), never the dev server.
- Chunk-size warnings are reviewed; heavy dependencies (emoji pickers, editors, charts) are lazy-loaded.
- `node_modules` inside a container uses an anonymous volume so host and container installs do not collide.

### Testing
- `build` runs in CI as its own step, with the production env shape.
