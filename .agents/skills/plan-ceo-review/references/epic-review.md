# Epic review

Loaded by plan-ceo-review step 5 when `plan_kind` is `epic`. An epic never executes; it
defines milestones that each become a feature plan or a quickfix. So this review is not about
implementation detail (each child gets its own eng review) but about whether the decomposition
is right: the milestones, their order, their independence, and their size. Step 0 parts 0A,
0B, 0C, and 0F have already run against the epic's end state.

Read the epic file in full, then:

```bash
"$BIN/obsidian-workflow" epic-get --slug "$EPIC_SLUG"
"$BIN/workflow-state" --epics
```

`epic-get` returns the milestones with their derived status. A milestone that has already
shipped is a fact, not an option; review only what is still ahead, and check that what shipped
still supports it.

## The four questions

Each is its own decision when the answer is not obvious. Number them E1 to E4; options get
letters as usual.

### E1. Right milestones?

- Each milestone maps to a user-visible or operator-visible outcome. A milestone that is a
  layer ("the backend part", "the UI part") instead of a vertical slice is a smell: nothing is
  demonstrable until the last one lands, and the riskiest integration is deferred to the end.
- Nothing essential is missing: walk the end state from 0C and check that every capability it
  needs is owned by exactly one milestone.
- Nothing is duplicated: two milestones that touch the same table, endpoint, or component need
  an explicit reason.
- The Deferred and Out of scope sections are honest. Anything the end state needs that no
  milestone delivers is either a new milestone or a written deferral with a TODOS.md entry.

### E2. Right order?

- Dependencies point backward only. Draw the milestone dependency graph (template below) and
  check that it is acyclic.
- The riskiest unknown is retired earliest. If M4 holds the integration that could sink the
  epic, ask why it is not M1 or M2.
- Nothing ships that a later milestone must undo. A schema shape, an API contract, or a UI
  affordance that M2 introduces and M5 replaces is wasted work and a migration risk.
- Locked decisions are actually locked by the time a child needs them. A decision the epic
  leaves open but M1 depends on is an open question for this review, now.

### E3. Each shippable alone?

- Every milestone leaves the base branch releasable: behind a flag if the feature is
  incomplete, but deployable, with its own rollback.
- For each milestone boundary: what is live, what is half-live, and what is the exact
  reversal order if the next milestone is delayed by a month?
- A milestone that only makes sense if the next one ships within days is two halves of one
  milestone, or the epic needs a flag strategy it does not have.

### E4. Sizes right?

- Each milestone fits one plan or one quickfix, per the sizing table in `WORKFLOW.md`. A
  `quickfix` milestone with a schema, route, dependency, or new UI surface is mis-sized.
- Too big becomes two milestones. Epics are one level deep; never propose a sub-epic.
- Sizes are stated on both scales (human / AI-assisted).

## Locked decisions

Read the epic's "Locked architecture and decisions" section as the contract every child
inherits verbatim. For each decision ask: is it actually a decision (one clear choice), is it
one the children need, and is it right? A wrong locked decision is the most expensive kind of
finding in an epic review; raise it here, once, as its own question. A decision that is really
an open question moves to Open Questions and is resolved now or assigned to the milestone that
must resolve it.

## Required diagrams

Milestone dependency graph:

```
  M1 schema ──▶ M2 sync service ──▶ M3 settings UI
                       │
                       └──────────▶ M4 notifications
```

End-state architecture: the system after the last milestone ships, with each new component
annotated by the milestone that introduces it. This is the diagram Section 1 would produce for
a feature plan, drawn once for the whole epic.

## Outputs

Write into the epic file, in place, with `CEO review E<n>: decision` breadcrumbs:

- Changes to the milestone table (added, split, merged, reordered, resized). Sync the
  registry for every changed milestone; for an added or removed milestone, re-register the
  epic with the complete milestones JSON:

```bash
"$BIN/obsidian-workflow" milestone-set --slug "$EPIC_SLUG" --milestone M3 \
  --set title="..." --set depends_on='["M1","M2"]'
"$BIN/obsidian-workflow" epic-register --slug "$EPIC_SLUG" --path "$_PLAN_FILE" \
  --milestones-json "$MILESTONES_JSON"        # only when milestones were added or removed
```

- Changes to Locked architecture and decisions.
- NOT in scope, What already exists, and Dream state delta, at epic level.
- The two diagrams above.
- Unresolved decisions, by E-number.

Then update the milestone table in `$DOCS_DIR/IMPLEMENTATION_PLAN.md` (step 10 of the skill)
so the roadmap matches the epic, and continue at step 7 of the skill.
