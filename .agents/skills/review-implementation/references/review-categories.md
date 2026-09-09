# Review categories

Stack-neutral categories for the two-pass structural review. Each names a class of defect and
the questions to ask of every changed file. The concrete, technology-specific checks (which
data-access call lazy-loads, which job runner retries, which template helper escapes) live in
`$DOCS_DIR/REVIEW_CHECKLIST.md`; read it alongside this file and cite its entries in findings.

## Pass 1 — critical

### Data and migration safety

- Raw queries built from strings instead of parameters.
- Multi-step writes without a transaction boundary; a partial failure leaves half a change.
- Schema migrations that lock a large table, drop or narrow a column holding live data, add a
  NOT NULL column without a default or backfill, or cannot be reversed.
- Missing cascade or constraint declarations where the domain implies them (orphans on delete).
- Data written in one shape and read in another (serializer and deserializer drift).

### Concurrency and background-job idempotency

- Check-then-act: read, decide, write, with no lock, version, or unique constraint between.
- Shared mutable state in async handlers, request-scoped caches, or module globals.
- Missing optimistic locking on concurrent updates of the same row or document.
- Background jobs that are not safe to run twice, or that lose work when retried.
- Timeouts and retries on external calls without idempotency keys.

### Trust boundaries and authorization

- User input reaching a query, a shell command, a file path, a URL, or a template unsanitized.
- Responses from external services used without validation.
- Client-supplied data trusted server-side: ids, prices, roles, ownership.
- New endpoints, routes, or handlers missing the authentication or authorization checks their
  siblings have.
- Secrets or tokens logged, echoed in error messages, or committed.

### Enum and value completeness

- A new enum value, status, tier, or type constant introduced anywhere. Search for every file
  that references its sibling values (switches, maps, validators, serializers, UI labels,
  filters, tests) and read them. Any place that enumerates the siblings without the new value
  is a finding. This is the one category where reading only the diff is insufficient.

## Pass 2 — informational

### Conditional side effects and error handling

- Side effects (writes, external calls, messages, notifications) inside branches that may not
  run, or that run before validation finishes.
- Failures swallowed: bare excepts, empty catch blocks, logged-and-continued errors that leave
  state inconsistent.
- Side effects with no rollback or compensation on failure.
- Error paths that return the wrong status, leak internals, or hide the cause from the user.

### Magic values and string coupling

- Hardcoded numbers or strings that belong in constants or config.
- Status and type checks by string comparison where an enum exists.
- The same literal duplicated across files; a rename will miss one.

### Dead code and consistency

- Unreachable paths, unused imports, leftover debug output, commented-out code.
- Divergence from the patterns the surrounding code uses: naming, layering, error shape.
- A copy of a helper that already exists elsewhere in the codebase.

### Test gaps

- New code paths without tests; changed behavior without updated tests.
- Edge cases uncovered: empty, null, boundary, failure. `coverage-diagram.md` does the
  detailed pass.

### View and accessibility

- Missing labels, keyboard navigation, focus management, contrast.
- Missing loading, error, and empty states.
- Injection vectors: raw HTML rendering of user content, unescaped interpolation.
- Broken responsive behavior at the breakpoints `FRONTEND_GUIDELINES.md` documents.

### Query and render efficiency

- N+1 access patterns (a query per row, a fetch per item) and missing eager loading.
- Unbounded fetches without pagination or limits.
- New query patterns without a supporting index.
- Render work repeated on every update: unstable keys, recomputation without memoization,
  effects that refire needlessly.

### Dependency and bundle impact

- New dependencies: size, maintenance, license, overlap with something already present.
- A large dependency pulled in for one small function.
- Version pins that disagree with `TECH_STACK.md`.
