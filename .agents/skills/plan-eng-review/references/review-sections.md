# The four review sections

Loaded by plan-eng-review step 5. Work one section at a time, in order; at most eight top
issues per section; stop after each and ask one question per genuine decision.

Every bullet names a category. The project's concrete checks for it (which data-access call
lazy-loads, which job runner retries, which migration operations lock, which template helper
escapes) live in `$DOCS_DIR/REVIEW_CHECKLIST.md`. Read that file alongside this one and cite
its entries in findings. Test layers and commands come from `$DOCS_DIR/development-commands.md`.

## Section 1: Architecture

Evaluate:

- Overall system design and component boundaries. Does each new component have one reason to
  exist and one owner?
- Dependency graph and coupling. Which components are now coupled that were not before? Draw
  the before and after graph when it changes.
- Data-flow patterns and bottlenecks. Where does data enter, transform, persist, and leave;
  where does it queue up?
- Scaling characteristics and single points of failure. What breaks first at 10x?
- Security architecture: auth boundaries, data-access scoping, API boundaries. For each new
  endpoint or mutation: who can call it, what do they get, what can they change?
- Migration safety, when the plan changes schema: backward compatible with the running code,
  reversible, no lock on a large table. The checklist names the locking operations.
- Background-job idempotency, when the plan adds async work: safe to run twice, safe to
  retry, safe with the old payload shape during a deploy.
- Which key flows deserve ASCII diagrams, in the plan or in code comments.
- For each new codepath or integration point, one realistic production failure scenario
  (timeout, cascade, partial write, auth failure, stale cache) and whether the plan accounts
  for it.

Apply: boring by default, blast radius, reversibility (`cognitive-patterns.md`).

## Section 2: Code quality

Evaluate:

- Organization and module structure by layer: data, API, service, UI, shared. Does new code
  land where its siblings live? If it deviates, is there a reason?
- DRY violations. Be aggressive. Cite the file and line of the existing logic.
- Error-handling patterns and missing edge cases. Call them out explicitly: "what happens when
  X is nil?", "when the upstream returns 429?", "when the list is empty?"
- Technical-debt hotspots the plan touches or creates.
- Over-engineering (an abstraction for a problem that does not exist yet) and
  under-engineering (fragile, happy-path only, missing defensive checks), against the
  engineering preferences.
- New dependencies in any layer: size, maintenance, license, overlap with something already
  present, version agreement with `TECH_STACK.md`.
- Operational scripts and admin tooling the plan needs (backfills, one-off commands): planned,
  tested, and idempotent?
- Existing ASCII diagrams in touched files: still accurate after this change?

Apply: essential versus accidental complexity; make the change easy first.

## Section 3: Tests

### Coverage diagram

Draw it before asking any test question. It is the highest-leverage output of the review
after Step 0 and is never skipped.

```
  NEW UX FLOWS:                       [each new user-visible interaction; what is new about it]
  NEW DATA FLOWS:                     [each new path data takes through the system]
  NEW CODEPATHS:                      [each new branch, condition, or execution path]
  NEW BRANCHING OUTCOMES:             [each new if/else outcome a user or job can reach]
  NEW BACKGROUND JOBS / ASYNC WORK:   [each]
  NEW INTEGRATIONS / EXTERNAL CALLS:  [each]
  NEW ERROR PATHS:                    [each; cross-reference the failure modes output]
```

For each item:

| Question | Answer shape |
|---|---|
| Test type | unit, integration, system, end-to-end |
| Layer | the layer the code lives in, and the suite `development-commands.md` names for it |
| In the plan? | yes, or the test spec header to add |
| Happy path | one line |
| Failure path | which failure, specifically |
| Edge case | nil, empty, boundary, concurrent |

Every item gets a test in its own layer. A UI flow gets a UI-layer test; an endpoint gets an
API-layer test; a job gets a job-layer test; a flow that crosses layers gets one test per
layer it touches plus an end-to-end path in the test artifact.

### Ambition and shape

- For each new feature: the test that would make you confident shipping at 2am on a Friday;
  the test a hostile QA engineer would write; the chaos test.
- Pyramid: many unit, fewer integration, few end-to-end, or inverted?
- Flakiness: flag any test depending on time, randomness, external services, or ordering.
- Load: required for any codepath called frequently or processing significant data.

### Prompt or LLM changes

`AGENTS.md` or `REVIEW_CHECKLIST.md` may list file patterns that count as prompt changes. If
the plan touches any, state which eval suites must run, which cases to add, and which
baselines to compare against. Then ask one question to confirm the eval scope.

Apply: systems over heroes; failure is information.

## Section 4: Performance

Evaluate:

- Query efficiency and data-access patterns: a query per row where one query would do;
  related data loaded up front or lazily; an index for every new query; unbounded fetches
  without pagination.
- Memory: the maximum size of every new data structure in production.
- Caching opportunities for expensive computation or external calls, and what invalidates
  each cache.
- Slow or high-complexity paths: the slowest new codepaths and their rough p99.
- Render efficiency, where there is UI: work repeated on every update, unstable list keys,
  effects or recomputation that refire needlessly.
- Background-job sizing: worst-case payload, runtime, and retry behavior.
- Connection pressure: new database, cache, queue, or HTTP connections against existing pools.

Apply: blast radius; error budgets.
