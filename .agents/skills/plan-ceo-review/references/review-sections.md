# The ten review sections

Loaded by plan-ceo-review step 6. Work one section at a time, in order. After each section,
stop and ask one question per genuine decision; if a section has no issues or the fix is
obvious, say so and move on. Never start the next section with an issue unresolved.

Every section names categories. The project's concrete checks for each category (which
data-access call lazy-loads, which job runner retries, which template helper escapes, which
migration operations lock) are in `$DOCS_DIR/REVIEW_CHECKLIST.md`; apply them where the
category appears and cite the entry in the finding. The sections themselves stay
stack-neutral. Test layers and commands come from `$DOCS_DIR/development-commands.md`.

Mode additions (EXPANSION and SELECTIVE EXPANSION) are marked; see `mode-guide.md`.

## Section 1: Architecture

Evaluate and diagram:

- Overall system design and component boundaries. Draw the dependency graph.
- Data flow, all four paths. For every new data flow, diagram the happy path (data flows
  correctly), the nil path (input missing), the empty path (present but zero-length), and the
  error path (an upstream call fails).
- State machines. A diagram for every new stateful object, including impossible or invalid
  transitions and what prevents them.
- Coupling. Which components are now coupled that were not before? Is it justified? Draw the
  before and after dependency graph.
- Scaling. What breaks first at 10x load? At 100x?
- Single points of failure. Map them.
- Security architecture. Auth boundaries, data-access patterns, API surfaces. For each new
  endpoint or data mutation: who can call it, what do they get, what can they change?
- Production failure scenarios. For each new integration point, one realistic failure
  (timeout, cascade, data corruption, auth failure) and whether the plan accounts for it.
- Rollback posture. If this ships and immediately breaks: revert, feature flag, migration
  rollback? How long does it take?

Required diagram: the full system with new components and their relationships to existing
ones.

EXPANSION additions: what would make this architecture beautiful, not just correct; what
infrastructure would make this feature a platform other features build on.

## Section 2: Exception and rescue map

The section that catches silent failures. Not optional. For every new function, service, or
codepath that can fail, fill in both tables. Error types are whatever the project's runtime
and libraries raise; the names below are placeholders, not a vocabulary.

```
  CODEPATH                 | WHAT CAN GO WRONG             | ERROR TYPE
  -------------------------|-------------------------------|--------------------------
  SyncService.run          | upstream API times out        | <http client timeout>
                           | upstream returns 429          | <rate-limit error>
                           | upstream returns malformed    | <parse or decode error>
                           | DB connection pool exhausted  | <pool timeout>
                           | record not found              | <not-found error>

  ERROR TYPE               | CAUGHT? | RESCUE ACTION            | USER SEES
  -------------------------|---------|--------------------------|--------------------------
  <http client timeout>    | Y       | retry 2x, then raise     | "Service temporarily unavailable"
  <rate-limit error>       | Y       | backoff and retry        | nothing (transparent)
  <parse or decode error>  | N ← GAP | —                        | 500 ← BAD
  <pool timeout>           | N ← GAP | —                        | 500 ← BAD
  <not-found error>        | Y       | return empty, log warn   | "Not found"
```

Rules:

- A catch-all handler (catching the base error type, or a bare catch) is always a smell. Name
  the specific error types.
- A handler that only logs the message is insufficient. Log the full context: what was being
  attempted, with what arguments, for which user or request.
- Every caught error must retry with backoff, degrade gracefully with a user-visible message,
  or re-raise with added context. "Swallow and continue" is almost never acceptable.
- For each GAP: specify the rescue action and what the user should see.
- For LLM or AI service calls: a malformed response, an empty response, invalid structure
  (something that does not parse into the expected shape), and a refusal are four distinct
  failure modes. Map each.

## Section 3: Security and threat model

Security is not a sub-bullet of architecture. Evaluate:

- Attack surface expansion. New endpoints, params, file paths, background jobs, webhooks.
- Input validation. For every new user input: validated, sanitized, rejected loudly on
  failure? What happens with nil, empty string, a string where a number is expected, a value
  over the maximum length, unicode edge cases, HTML or script injection attempts?
- Authorization. For every new data access: scoped to the right user or role? Can a user
  reach another user's data by manipulating an id? If `PRD.md` says the deployment is
  single-tenant, say so and scope the check accordingly.
- Secrets and credentials. New secrets in env vars, not hardcoded? Rotatable?
- Dependency risk. New packages, in any layer? Maintenance and security track record?
- Data classification. PII, payment data, credentials? Handled like existing patterns?
- Injection vectors. SQL, command, template, path, and LLM prompt injection.
- Audit logging. For sensitive operations, is there an audit trail?

For each finding: threat, likelihood (High/Med/Low), impact (High/Med/Low), mitigated or not.

## Section 4: Data flow and interaction edge cases

Trace data through the system and interactions through the UI with adversarial thoroughness.

Data flow tracing. For every new data flow, a diagram with the shadow paths at each node:

```
  INPUT ──▶ VALIDATION ──▶ TRANSFORM ──▶ PERSIST ──▶ OUTPUT
    │            │              │            │           │
    ▼            ▼              ▼            ▼           ▼
  [nil?]    [invalid?]    [exception?]  [conflict?]  [stale?]
  [empty?]  [too long?]   [timeout?]    [dup key?]   [partial?]
  [wrong    [wrong type?] [OOM?]        [locked?]    [encoding?]
   type?]
```

For each node: what happens on each shadow path, and is it tested?

Interaction edge cases. For every new user-visible interaction:

```
  INTERACTION          | EDGE CASE                         | HANDLED? | HOW?
  ---------------------|-----------------------------------|----------|--------
  Form submission      | double-click submit               | ?        |
                       | submit with a stale session token | ?        |
                       | submit during a deploy            | ?        |
  Async operation      | user navigates away               | ?        |
                       | operation times out               | ?        |
                       | retry while in flight             | ?        |
  List or table view   | zero results                      | ?        |
                       | ten thousand results              | ?        |
                       | results change mid-page           | ?        |
  Background job       | fails after 3 of 10 items         | ?        |
                       | runs twice (duplicate delivery)   | ?        |
                       | queue backs up two hours          | ?        |
```

Every unhandled cell is a gap. For each gap, specify the fix.

## Section 5: Code quality

- Organization and module structure. Does new code fit existing patterns? If it deviates, is
  there a reason?
- DRY violations. Be aggressive. If the same logic exists elsewhere, cite the file and line.
- Naming. Named for what it does, not how it does it?
- Error-handling patterns. Section 2 maps the specifics; this section reviews the patterns.
- Missing edge cases, listed explicitly: "what happens when X is nil?", "when the API returns
  429?"
- Over-engineering: any new abstraction solving a problem that does not exist yet?
- Under-engineering: anything fragile, happy-path-only, or missing obvious defensive checks?
- Complexity: flag any new function that branches more than five times and propose a
  refactor.

## Section 6: Tests

Make a complete diagram of every new thing this plan introduces:

```
  NEW UX FLOWS:                       [each new user-visible interaction]
  NEW DATA FLOWS:                     [each new path data takes through the system]
  NEW CODEPATHS:                      [each new branch, condition, or execution path]
  NEW BACKGROUND JOBS / ASYNC WORK:   [each]
  NEW INTEGRATIONS / EXTERNAL CALLS:  [each]
  NEW ERROR / RESCUE PATHS:           [each; cross-reference Section 2]
```

For each item: the test type that covers it (unit, integration, system, end-to-end) in the
layer the code lives in; whether the plan already has that test (if not, write the test spec
header); the happy-path test; the failure-path test (which failure, specifically); the
edge-case test (nil, empty, boundary values, concurrent access).

Test ambition, all modes. For each new feature: the test that would make you confident
shipping at 2am on a Friday; the test a hostile QA engineer would write to break it; the
chaos test.

Pyramid shape: many unit, fewer integration, few end-to-end, or inverted? Flakiness: flag any
test depending on time, randomness, external services, or ordering. Load and stress: required
for any new codepath called frequently or processing significant data.

Prompt or LLM changes: `AGENTS.md` or `REVIEW_CHECKLIST.md` may list file patterns that count
as prompt changes. If the plan touches any, state which eval suites must run, which cases to
add, and which baselines to compare against; confirm the eval scope with one question.

## Section 7: Performance

- Query efficiency. For every new traversal of related data: loaded up front, or a query per
  row? For every new query: is there an index?
- Memory. For every new data structure: maximum size in production?
- Caching. For every expensive computation or external call: should it be cached, and what
  invalidates it?
- Background-job sizing. For every new job: worst-case payload, runtime, retry behavior?
- Slow paths. The three slowest new codepaths and their estimated p99 latency.
- Connection pressure. New database, cache, queue, or HTTP connections, against the pools that
  exist?
- Render efficiency, where there is UI: work repeated on every update, unstable list keys,
  effects or recomputation that refire needlessly.

## Section 8: Observability and debuggability

New systems break. This section makes sure you can see why.

- Logging. Structured log lines at entry, exit, and each significant branch of every new
  codepath?
- Metrics. What metric says the feature is working? What says it is broken?
- Tracing. For cross-service or cross-job flows: trace ids propagated?
- Alerting. What new alerts should exist?
- Dashboards. What panels do you want on day one?
- Debuggability. If a bug is reported three weeks after ship, can you reconstruct what
  happened from logs alone?
- Admin tooling. New operational tasks that need an admin UI or an operational script?
- Runbooks. For each new failure mode: the operational response.

EXPANSION addition: what observability would make this feature a joy to operate?

## Section 9: Deployment and rollout

- Migration safety. For every new schema migration: backward compatible? Zero downtime? Table
  locks? The checklist names the operations that lock on this project's database.
- Feature flags. Should any part sit behind one?
- Rollout order. Migrate first, deploy second, or the reverse; and why.
- Rollback. Explicit, step by step.
- Deploy-time risk window. Old and new code running at the same time: what breaks?
- Environment parity. Tested somewhere that resembles production?
- Post-deploy verification. The first five minutes; the first hour.
- Smoke tests. Which automated checks run immediately after deploy?

EXPANSION addition: what deploy infrastructure would make shipping this feature routine?

## Section 10: Long-term trajectory

- Debt introduced: code, operational, testing, documentation.
- Path dependency. Does this make future changes harder?
- Knowledge concentration. Is the documentation enough for a new engineer?
- Reversibility, 1 to 5: 1 is a one-way door, 5 is easily reversible.
- Ecosystem fit. Aligned with where the project's stack (per `TECH_STACK.md`) is heading?
- The one-year question. Read this plan as a new engineer in twelve months: is it obvious?

EXPANSION additions: what comes after this ships (phase 2, phase 3), and does the architecture
support that trajectory; does this create capabilities other features can leverage?
