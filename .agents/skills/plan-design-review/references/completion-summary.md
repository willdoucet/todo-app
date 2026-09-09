# Completion summary

Loaded by `plan-design-review` at step 12. Fill in every row and present it before the
completion status. Scores are before and after fixes.

```
  +====================================================================+
  |         DESIGN PLAN REVIEW: COMPLETION SUMMARY                     |
  +====================================================================+
  | System audit         | [design-system status, UI scope, drift]      |
  | Step 0               | [initial rating, focus areas]                |
  | Pass 1  (Info arch)  | ___/10 -> ___/10 after fixes                 |
  | Pass 2  (States)     | ___/10 -> ___/10 after fixes                 |
  | Pass 3  (Journey)    | ___/10 -> ___/10 after fixes                 |
  | Pass 4  (AI slop)    | ___/10 -> ___/10 after fixes                 |
  | Pass 5  (Design sys) | ___/10 -> ___/10 after fixes                 |
  | Pass 6  (Responsive) | ___/10 -> ___/10 after fixes                 |
  | Pass 7  (Decisions)  | ___ resolved, ___ deferred                   |
  | Step 8  (Visuals)    | path: A/B/C, ___ components covered          |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (___ items)                          |
  | What already exists  | written                                      |
  | TODOS.md updates     | ___ items proposed, ___ added                |
  | Decisions made       | ___ added to plan                            |
  | Decisions deferred   | ___ (listed below)                           |
  | Overall design score | ___/10 -> ___/10                             |
  +====================================================================+
```

Below the box:

- **Unresolved decisions:** by issue number, with what happens if each stays deferred. Never
  a silent default.
- If every pass is 8 or above: "Plan is design-complete. `/design-review` audits the live
  pages after implementation."
- If any pass is below 8: name what is unresolved and why (the user chose to defer, or the
  choice needs information the plan does not have yet).
- If the prototype was deferred with `skip`: say the implementer will work without it.
- On an epic: one line per milestone seam the review changed.

The values feed the review log: `INITIAL_SCORE` and `OVERALL_SCORE` from the last row,
`DECISIONS_MADE` and `UNRESOLVED` from the decisions rows.
