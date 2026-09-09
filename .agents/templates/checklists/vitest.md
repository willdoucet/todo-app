## Vitest

### Testing
- Network is mocked with MSW; handlers are reset between tests; no unit test reaches a real API.
- Timers are faked for debounce, undo countdown, and polling tests, and restored afterwards.
- Test placement follows FRONTEND_STRUCTURE.md (co-located or under `tests/`); files are named `<Component>.test.<ext>`.
- Regression tests are named for the bug and assert the invariant (one delete removes exactly one item), not the implementation.
- No test depends on order; stores, contexts, and `localStorage` are reset in `beforeEach`.
- Strict Mode is on in the test renderer so render-time side effects surface.
- CI runs the single-run command, not watch mode; coverage thresholds live in the config file.
- A behavior that a class-name assertion cannot prove (animation, layout shift) gets a browser-level test instead.
