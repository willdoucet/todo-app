## TypeScript

### Rendering & state
- `strict: true`; every `any` has a comment saying why.
- Shared API types are generated from the backend schema or single-sourced; no hand-copied response shapes.
- Variant types are discriminated unions with an exhaustive `switch` ending in `never`.
- Nullability is explicit; no non-null assertions on data that came from the network.

### Testing
- `tsc --noEmit` runs in CI as its own job.
- Public utility signatures that encode behavior have type-level tests.

### Operations
- Path aliases are defined once and shared by the build, test, and lint configs through a base `tsconfig`.
