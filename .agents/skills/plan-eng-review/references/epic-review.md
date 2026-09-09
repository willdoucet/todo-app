# Epic engineering review

Loaded by plan-eng-review step 7 when `plan_kind` is `epic`. An epic never executes; each
milestone becomes a feature plan or a quickfix with its own eng review. So this review does
not inspect any milestone's internals. It reviews the things only the epic can get wrong:
sequencing, the dependency map, and rollout and rollback at every milestone boundary. No test
artifact is written; each child writes its own.

```bash
"$BIN/obsidian-workflow" epic-get --slug "$EPIC_SLUG"
"$BIN/workflow-state" --epics
```

Milestones that have already shipped are facts. Review only what is ahead, but check that
what shipped still supports what is planned.

## The three sections

Number issues per section as usual; options get letters.

### E1. Sequencing

- Dependencies point backward only; the graph is acyclic. Draw it (template below).
- The riskiest unknown is retired earliest. Name the milestone that could sink the epic and
  ask why it is not first or second.
- Nothing ships that a later milestone must undo: a schema shape, an API contract, a UI
  affordance, or a flag that M2 introduces and M5 replaces.
- Make the change easy, then make the easy change: refactoring milestones precede the
  behavioral ones that need them, and no milestone mixes both.
- Every locked decision a child depends on is actually locked, not an open question in the
  epic. An open question a milestone needs answered is assigned to the milestone that must
  answer it, or resolved now.

### E2. Dependency map

For every pair of milestones that touch the same table, endpoint, component, job, or
configuration:

```
  SHARED THING            | TOUCHED BY   | CONTRACT BETWEEN THEM
  ------------------------|--------------|--------------------------------------------
  items.status column     | M1, M3       | M1 adds nullable; M3 backfills and enforces
  /api/sync endpoint      | M2, M4       | M2 defines the response shape; M4 adds a field
```

Every row needs a stated contract. A shared thing with no contract is a finding: two children
will make incompatible choices. Also list external dependencies (services, packages, infra)
and which milestone introduces each; a new dependency is an innovation token, spent knowingly.

### E3. Rollout and rollback between milestones

For each milestone boundary:

```
  AFTER MILESTONE | LIVE                | HALF-LIVE (flagged or dormant) | REVERSAL ORDER
  ----------------|---------------------|--------------------------------|--------------------
  M1              | new column, unused  | —                              | drop column
  M2              | sync job, flag off  | job code, flag                 | flag off → remove job → M1
```

- Every milestone leaves the base branch deployable, with its own rollback, even if the next
  milestone is a month away.
- Old and new code run together during each deploy: what breaks at each boundary?
- Flags: which milestone introduces each, which retires it, and what state production is in
  if the epic stalls between them.
- Observability per milestone: what tells you M2 is working before M3 exists?

## Required diagrams

Milestone dependency graph, written into the epic:

```
  M1 schema ──▶ M2 sync service ──▶ M3 settings UI
                       │
                       └──────────▶ M4 notifications
```

End-state architecture: the system after the last milestone, with each new component
annotated by the milestone that introduces it.

## Outputs

Write into the epic file in place, with `Eng review E<n>: decision` breadcrumbs:

- Changes to milestone order, dependencies, sizes, or branches, then sync the registry:

```bash
"$BIN/obsidian-workflow" milestone-set --slug "$EPIC_SLUG" --milestone M3 \
  --set depends_on='["M1","M2"]'
```

- The dependency map and the rollout table, as sections in the epic.
- The two diagrams.
- NOT in scope and What already exists at epic level; Unresolved decisions by E-number.
- The workflow flags (step 10 of the skill) on the epic file, from the union of its
  milestones, so the epic's own dashboard routes correctly.

Then update the milestone table in `$DOCS_DIR/IMPLEMENTATION_PLAN.md` to match, and continue
at step 8 of the skill.
