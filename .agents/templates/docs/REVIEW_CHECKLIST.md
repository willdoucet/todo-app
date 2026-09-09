# Review Checklist

<!-- guidance: Assembled, not written. init-project concatenates one snippet per chosen
technology from `.agents/templates/checklists/*.md` below the marker at the end of this file, in
stack order: backend framework, ORM, migrations, validation, jobs, cache, database, frontend
framework, build tool, styling, data layer, router, test runners, containers, CI. Each snippet is
headed `## <Technology>` with checks grouped under the categories listed here. When a technology
has no snippet, draft one in the same shape and offer it back to the templates directory.
/review-implementation and /final-review run every check that applies to the diff; a check is
one line a reviewer can answer yes or no. When a review finds a repeatable class of bug, add a
check to the matching snippet, not a paragraph to LESSONS.md. -->

Stack: {{BACKEND_FRAMEWORK}} · {{ORM}} · {{MIGRATION_TOOL}} · {{DB}} · {{FRONTEND_FRAMEWORK}} · {{STYLING}} · {{TEST_RUNNER_BACKEND}} · {{TEST_RUNNER_FRONTEND}} · {{CONTAINER_TOOL}} · {{CI_PROVIDER}}

## Categories

Every snippet groups its checks under these headings, in this order, omitting any that do not apply.

### Data & migrations
Schema changes, migration safety and reversibility, constraints that back business rules, soft-delete filtering.

### API & trust boundaries
Auth on every non-public route, input validation at the edge, identical failure bodies, nothing secret in a response.

### Background jobs
Idempotency, retries, transaction boundaries around enqueue, event-loop and connection hygiene.

### Query efficiency
Eager loading for what the response touches, indexes for new query shapes, locks held for the whole unit of work.

### Rendering & state
Async states, form structure, effect cleanup, optimistic updates, where tokens live.

### Styling & accessibility
Tokens over literals, light/dark pairing, motion that survives the build and honors reduced motion, focus and targets.

### Testing
The invariant a bug violated has a test; structural tests for cross-cutting guarantees; isolation between tests.

### Secrets & config
Env from one place, nothing secret reaches the client bundle or the transcript, production fails closed.

### Operations
Health checks, non-root containers, writable paths, graceful shutdown, CI parity with local commands.

---

<!-- snippets appended below -->
