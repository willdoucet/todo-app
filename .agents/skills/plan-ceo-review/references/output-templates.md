# Output templates

Loaded by plan-ceo-review steps 7 and 12. Every block below is written into `_PLAN_FILE` in
place (see `_shared/plan-footer.md`), except the completion box, which is presented to the
user and condensed into the CEO Review row of the plan's review table.

## NOT in scope

```markdown
## NOT in scope
<!-- CEO review: considered and deferred -->
- {item} — {one-line rationale}; TODOS.md: {yes | no, because ...}
```

## What already exists

```markdown
## What already exists
| Sub-problem | Existing code or flow | Plan reuses it? |
|---|---|---|
| {sub-problem} | `{path}` {what it does} | {yes | no: rebuilds, because ...} |
```

## Dream state delta

```markdown
## Dream state delta
  CURRENT STATE            THIS PLAN                12-MONTH IDEAL
  [describe]      --->     [describe delta]  --->   [describe target]

After this plan: {where the system sits relative to the ideal, and the next step toward it}
```

## Exception and rescue registry (feature plans only)

The completed map from Section 2, one row per codepath that can fail:

```markdown
## Exception and rescue registry
| Codepath | What can go wrong | Error type | Caught? | Rescue action | User sees | Tested? |
|---|---|---|---|---|---|---|
```

## Failure modes registry

```markdown
## Failure modes
| Codepath | Failure mode | Caught? | Test? | User sees? | Logged? |
|---|---|---|---|---|---|
```

Any row with `Caught? = N`, `Test? = N`, and a silent user outcome is a **CRITICAL GAP**. Mark
it in the row and count it for the completion box and the review log.

## Diagrams

Produce all that apply, in the plan, as fenced text blocks:

1. System architecture (new components against existing ones)
2. Data flow, with shadow paths
3. State machine, with impossible transitions
4. Error flow
5. Deployment sequence
6. Rollback flowchart

Epics: the milestone dependency graph and the end-state architecture (see `epic-review.md`).

## Stale diagram audit

```markdown
## Stale diagram audit
| File | Diagram (caption or first line) | Still accurate? | Action |
|---|---|---|---|
| `{path}` | {caption} | {yes | no} | {update in this change | none} |
```

Cover every ASCII diagram in files the plan touches. "None found" is a valid result; say so.

## Unresolved decisions

```markdown
## Unresolved decisions
<!-- CEO review: the user did not answer or moved on; never defaulted -->
- {issue number}: {the decision} — recommended {option}
```

## Completion box

`MODE` is one of `EXPANSION`, `SELECTIVE_EXPANSION`, `HOLD_SCOPE`, `REDUCTION`.

```
  +====================================================================+
  |             CEO PLAN REVIEW — COMPLETION SUMMARY                    |
  +====================================================================+
  | Mode selected        | {MODE}                                      |
  | System audit         | [key findings]                              |
  | Step 0               | [mode + key decisions]                      |
  | Section 1  (Arch)    | ___ issues found                            |
  | Section 2  (Errors)  | ___ error paths mapped, ___ GAPS            |
  | Section 3  (Security)| ___ issues found, ___ High severity         |
  | Section 4  (Data/UX) | ___ edge cases mapped, ___ unhandled        |
  | Section 5  (Quality) | ___ issues found                            |
  | Section 6  (Tests)   | diagram produced, ___ gaps                  |
  | Section 7  (Perf)    | ___ issues found                            |
  | Section 8  (Observ)  | ___ gaps found                              |
  | Section 9  (Deploy)  | ___ risks flagged                           |
  | Section 10 (Future)  | reversibility _/5, debt items ___           |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (___ items)                         |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Exception registry   | ___ codepaths, ___ CRITICAL GAPS            |
  | Failure modes        | ___ total, ___ CRITICAL GAPS                |
  | TODOS.md             | ___ proposed, ___ added                     |
  | Delight              | ___ identified (EXPANSION only)             |
  | Diagrams produced    | ___ (list types)                            |
  | Stale diagrams found | ___                                         |
  | PRD / roadmap sync   | {updated | in sync | conflict resolved}     |
  | Unresolved decisions | ___ (listed below)                          |
  +====================================================================+
```

The values feed the review log: `UNRESOLVED` from the last row, `CRITICAL_GAPS` from the
failure-modes row, `MODE` from the first.

## Completion box, epic variant

```
  +====================================================================+
  |             CEO EPIC REVIEW — COMPLETION SUMMARY                    |
  +====================================================================+
  | Mode selected        | {MODE}                                      |
  | System audit         | [key findings]                              |
  | Step 0 (0A-0C, 0F)   | [premise, leverage, dream state, mode]      |
  | E1 Right milestones  | ___ added, ___ split, ___ merged            |
  | E2 Right order       | ___ reordered; graph acyclic: Y/N           |
  | E3 Shippable alone   | ___ milestones lack a rollback              |
  | E4 Sizes right       | ___ resized                                 |
  | Locked decisions     | ___ reviewed, ___ changed, ___ unlocked     |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (___ items)                         |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Milestone graph      | produced                                    |
  | End-state diagram    | produced                                    |
  | TODOS.md             | ___ proposed, ___ added                     |
  | Roadmap sync         | milestone table {updated | in sync}         |
  | Unresolved decisions | ___ (listed below)                          |
  +====================================================================+
```

For epics, `CRITICAL_GAPS` in the review log is the number of milestones without a rollback
(row E3).
