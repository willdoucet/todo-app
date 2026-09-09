## React

### Rendering & state
- No nested `<form>` elements; an inner submit-like action uses a `<div>` with a button `onClick` and input `onKeyDown` Enter handler, and both call `preventDefault()` and `stopPropagation()`.
- Async UI has loading, empty, and populated states; empty-state guards are gated on `initialLoaded` so they never flash during load.
- No ref mutation during render (Strict Mode double-renders).
- A `useEffect` cleanup that cancels timers keyed to state does not re-run on every state change; when cleanup is unmount-only, the dep array is `[]` with a ref mirror.
- Optimistic updates revert on error and show a toast; the rollback path has a test.
- Contextual ids (`section_id`, `parent_id`) are threaded from UI state into the submit payload; a new write path sends every field the established path sends.
- Nested click targets call `stopPropagation()` so a row click does not fire under a button.
- API validation `detail` arrays are normalized before reaching a toast or an error banner.
- Polling (`setInterval`, `refetchInterval`) is conditional and stops when the pending state clears.

### Styling & accessibility
- Every interactive element has a visible focus ring; icon-only buttons carry `aria-label`; touch targets reach 44px.
- Dialogs trap focus and restore it on close; Escape closes them.

### Secrets & config
- Access tokens live in memory (module scope + `useSyncExternalStore`), never `localStorage` or `sessionStorage`.

### Testing
- The invariant a bug violated has a behavior-level test (one delete removes exactly one card), not a class-name assertion.
- A console error seen during live edits is checked against a clean reload before it is treated as a bug (HMR serves in-between versions).
