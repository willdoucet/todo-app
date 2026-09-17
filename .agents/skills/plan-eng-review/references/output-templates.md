# Output templates

Loaded by plan-eng-review steps 8 and 12. Every block is written into `_PLAN_FILE` in place
(see `_shared/plan-footer.md`) except the completion summary, which is presented to the user
and condensed into the Eng Review row of the plan's review table.

## NOT in scope

```markdown
## NOT in scope
<!-- Eng review: considered and deferred -->
- {item} — {one-line rationale}; TODOS.md: {yes | no, because ...}
```

## What already exists

```markdown
## What already exists
| Sub-problem | Existing code or flow | Plan reuses it? |
|---|---|---|
| {sub-problem} | `{path}` {what it does} | {yes | no: rebuilds, because ...} |
```

## Diagrams

In the plan: one fenced ASCII diagram per non-trivial data flow, state machine, or pipeline.
Then the inline-diagram list:

```markdown
## Inline diagrams to add during implementation
| File | Layer | Diagram | Why |
|---|---|---|---|
| `{path}` | data | state transitions of {object} | {non-obvious transitions} |
| `{path}` | service | {pipeline} | {multi-step with branches} |
| `{path}` | API | request flow for {endpoint} | {auth and validation order} |
| `{path}` | shared | what {mixin or middleware} does to its host | {invisible behavior} |
| `{path}` | test | setup for {suite} | {fixture shape is not obvious} |
```

Execute-plan adds these as part of the change. A stale diagram found during review is listed
here with "update" in the Why column.

## Failure modes

```markdown
## Failure modes
| Codepath | Failure mode | Test? | Handled? | User sees | Critical gap? |
|---|---|---|---|---|---|
| {from the coverage diagram} | {timeout, nil, race, stale data, ...} | Y/N | Y/N | {clear error | silent} | {yes when N, N, silent} |
```

One row per new codepath in the coverage diagram. `Test? = N`, `Handled? = N`, and `silent`
together are a **CRITICAL GAP**; count them for the completion summary and the review log.

## Unresolved decisions

```markdown
## Unresolved decisions
<!-- Eng review: decisions that may bite you later; the user did not answer or moved on -->
- {issue number}: {the decision} — recommended {option}; never defaulted
```

## Completion summary

```
  +====================================================================+
  |             ENG PLAN REVIEW — COMPLETION SUMMARY                    |
  +====================================================================+
  | Step 0 (scope)       | {FULL_REVIEW | SCOPE_REDUCED}: [key decisions] |
  | Inherited constraints| {n/a | honored | violation resolved: ...}     |
  | Architecture         | ___ issues found                            |
  | Code quality         | ___ issues found                            |
  | Tests                | diagram produced, ___ gaps                  |
  | Performance          | ___ issues found                            |
  +--------------------------------------------------------------------+
  | Test artifact        | {path} ({written | merged}), ___ critical paths |
  | NOT in scope         | written (___ items)                         |
  | What already exists  | written                                     |
  | Diagrams             | ___ in plan, ___ inline to add, ___ stale   |
  | Failure modes        | ___ total, ___ CRITICAL GAPS                |
  | TODOS.md             | ___ proposed, ___ added                     |
  | Flags                | ui_scope={true | false}, risk_tags=[...]    |
  | Unresolved decisions | ___ (listed below)                          |
  | Lake score           | ___/___ recommendations chose the complete option |
  +====================================================================+
```

`UNRESOLVED`, `CRITICAL_GAPS_FOUND`, `CRITICAL_GAPS_OPEN`, and `MODE` feed the review log.

## Completion summary, epic variant

```
  +====================================================================+
  |             ENG EPIC REVIEW — COMPLETION SUMMARY                    |
  +====================================================================+
  | Step 0 (scope)       | [leverage, minimum set, TODOS, completeness]|
  | E1 Sequencing        | ___ issues; graph acyclic: Y/N; ___ reordered |
  | E2 Dependency map    | ___ shared things, ___ without a contract   |
  | E3 Rollout/rollback  | ___ boundaries, ___ without a rollback      |
  +--------------------------------------------------------------------+
  | Milestone graph      | produced                                    |
  | End-state diagram    | produced                                    |
  | NOT in scope         | written (___ items)                         |
  | What already exists  | written                                     |
  | TODOS.md             | ___ proposed, ___ added                     |
  | Flags                | ui_scope={true | false}, risk_tags=[...]    |
  | Roadmap sync         | milestone table {updated | in sync}         |
  | Unresolved decisions | ___ (listed below)                          |
  | Lake score           | ___/___                                     |
  +====================================================================+
```

For epics, `CRITICAL_GAPS_FOUND` in the review log is the number of shared things without a
contract plus the number of boundaries without a rollback, and `CRITICAL_GAPS_OPEN` how many
of those the review left unresolved.
