## Playwright

### Testing
- Runs against the production build (`preview`) in a container with pinned fonts, never the dev server.
- Auth is handled in global setup (login-or-register a synthetic user); the cached token file is git-ignored; `context.route()` stubs the refresh endpoint instead of a production bypass flag.
- Geometric assertions (bounding boxes stable across hover / rest / exit) come before pixel diffs; pixel diffs have a tolerance and a written baseline-bump rule.
- Every spec waits on a state (`expect(...).toBeVisible()`), never a fixed sleep.
- The flake protocol is written down: rerun once, then quarantine with a TODOS.md item; the suite stays informational in CI until it has soaked.
- Reports, traces, and screenshots are git-ignored and uploaded by CI on failure only.
- A mobile project covers the views that only exist below the mobile breakpoint.
- Test data is created and deleted by the spec; no spec depends on another's leftovers.
