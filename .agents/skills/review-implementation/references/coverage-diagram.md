# Test coverage diagram

Every code path the diff changed, every user flow it touches, checked against an existing
test, drawn as a tree, then filled in. Full coverage is the goal; the ethos says tests are the
cheapest lake to boil.

Test frameworks and commands come from `$DOCS_DIR/development-commands.md`. Test layout,
fixtures, and naming come from the nearest existing test for the same module; match them.

## 1. Trace every changed code path

Read every changed file in full, then follow the data; do not just list functions:

1. Entry points: route handlers, exported functions, event listeners, component renders, job
   entry points.
2. From each entry point, follow the data through every branch: where input comes from
   (request, props, database, external call), what transforms it (validation, mapping,
   computation), where it goes (write, response, render, side effect), what can go wrong at
   each step (null, empty, invalid type, network failure, timeout).
3. Draw it: every added or modified function; every conditional (if/else, match, ternary,
   guard, early return); every error path (try/except, boundary, fallback); every call into
   another function (trace in; does it have untested branches?); every edge (null, empty,
   invalid).

## 2. Map user flows, interactions, and error states

For each changed feature:

- The sequence of user actions that reaches this code, start to finish.
- Interaction edges: double submit, navigate away mid-operation, submit with stale data after
  the page sat open, slow connection (what does the user see for ten seconds?).
- Every error the code handles: what does the user actually experience?
- Empty, zero, and boundary states: no results, thousands of results.

## 3. Check each branch against existing tests

Branch by branch, search for a test that exercises it: the function name in the test tree,
both arms of a conditional, a test that triggers each specific error, a component test covering
render and interaction.

Quality score:

- ★★★ tests behavior with edge cases and error paths
- ★★ tests correct behavior, happy path only
- ★ smoke test, existence check, trivial assertion ("it renders", "it does not throw")

## 4. Print the diagram

```
CODE PATH COVERAGE
===========================
[+] app/services/tasks.py
    │
    ├── create_task()
    │   ├── [★★★ TESTED] happy path + validation error — tests/unit/test_tasks.py:42
    │   ├── [GAP]         database timeout — NO TEST
    │   └── [GAP]         duplicate task name — NO TEST
    │
    └── update_task()
        ├── [★★  TESTED] full update — tests/unit/test_tasks.py:89
        └── [★   TESTED] partial update (checks non-throw only)

USER FLOW COVERAGE
===========================
[+] Task creation flow
    │
    ├── [★★★ TESTED] complete creation — TaskForm.test.jsx:15
    ├── [GAP]         double submit — needs test
    └── [★   TESTED] form validation errors (checks render only)

─────────────────────────────────
COVERAGE: 5/10 paths tested (50%)
  Code paths: 3/5 (60%)
  User flows: 2/5 (40%)
QUALITY:  ★★★: 2  ★★: 1  ★: 2
GAPS: 5 paths need tests
─────────────────────────────────
```

All paths covered: print "All new code paths have test coverage ✓" and continue.

## 5. Fill the gaps (fix-first)

Classify each gap:

- **AUTO-FIX**: unit tests for pure functions; edge cases of functions that already have
  tests; a missing arm of a conditional in an existing test file.
- **ASK**: end-to-end tests, tests that need new infrastructure (fixtures, fakes, a browser
  runner), tests for behavior the plan left ambiguous.

For AUTO-FIX gaps, write the test in the existing pattern, run it with the project's test
command, and quote the result. For ASK gaps, ask one question per gap in the shared format.
Do not commit; `/ship` commits.

## Regression rule

When the audit finds a regression, code that worked before and the diff broke, write the
regression test immediately. No question, no skipping. Regressions are the highest-priority
test because they prove something broke, and the test is what keeps it fixed.
