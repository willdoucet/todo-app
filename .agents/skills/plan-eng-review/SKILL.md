---
name: plan-eng-review
description: >-
  Eng manager-mode plan review and the shipping gate. Locks in the execution plan: scope
  challenge, architecture, code quality, test coverage, performance, diagrams, edge cases, and
  failure modes, one issue at a time with an opinionated recommendation. Writes the test
  artifact that execute-plan, adversarial review, and QA consume, confirms the ui_scope and
  risk_tags flags the workflow routes on, and folds every decision into the plan in place. On
  an epic it reviews sequencing, the dependency map, and rollout and rollback between
  milestones. Use when asked to "review the architecture", "engineering review", "eng
  review", or "lock in the plan". Suggest it when the user has a plan or design doc and is
  about to start coding.
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# Engineering plan review

The required review before implementation. Produces the plan edited in place (decisions folded
in with `Eng review N:` breadcrumbs, REVIEW REPORT row updated), the test artifact at
`$TEST_ARTIFACT`, confirmed `ui_scope` and `risk_tags` in the plan's frontmatter, TODOS
captured, and a review-log entry. Never writes code.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/plan-discovery.md`
- `_shared/obsidian-sync.md`
- `_shared/plan-footer.md`
- `_shared/dashboard.md`
- `_shared/docs-contract.md`

## Use when

- A plan exists and the user is about to start coding. Every feature plan gets this review; it
  is what `workflow-state` counts as the shipping gate.
- The user asks to review the architecture, lock in the plan, or check test coverage.
- The plan is an epic (`plan_kind: epic`): review the milestone sequencing, the dependency map,
  and rollout and rollback between milestones, not any milestone's internals.
- A prior eng review is stale because the plan changed materially (scope expansion, an
  adversarial pass that changed rollout assumptions). Rerun it; the log keeps every run.

## Do not use when

- There is no plan yet. Run `/office-hours` first.
- The question is whether the scope is right at all. That is `/plan-ceo-review`.
- The plan is implementing or shipped. Code review is `/review-implementation`.

## Posture

Review thoroughly before any code changes. For every issue, explain the concrete tradeoffs,
give an opinionated recommendation, and ask before assuming a direction.

**Engineering preferences.** Map every recommendation to one of these.

- DRY: flag repetition aggressively.
- Well-tested is non-negotiable; too many tests beats too few.
- Engineered enough: not fragile or hacky, not prematurely abstract.
- More edge cases handled, not fewer; thoughtfulness over speed.
- Explicit over clever.
- Minimal diff: the fewest new abstractions and files touched.

**Diagrams.** ASCII diagrams are valued highly: data flow, state machines, dependency graphs,
processing pipelines, decision trees. Use them liberally in the plan. For complex designs,
embed them in code comments in the layer they describe: data layer (relationships, state
transitions), API layer (request flow), service layer (pipelines), shared behaviors (what a
mixin or middleware does to its host), and tests with non-obvious setup. Diagram maintenance
is part of the change: a stale diagram actively misleads. Flag any stale diagram you meet,
even outside the plan's scope.

**How great eng managers think.** The fifteen cognitive patterns in
`references/cognitive-patterns.md` are the instincts behind this review, not extra checklist
items. Read them once now; apply them throughout and cite one when it drives a recommendation.

**Priority under context pressure:** Step 0 > test diagram > opinionated recommendations >
everything else. Never skip Step 0 or the test diagram.

## Procedure

### 1. Ground

Follow the preamble, then plan discovery including the metadata read. Then:

```bash
[ "$ON_BASE" = "1" ] && echo "On $BASE_BRANCH — switch to the plan's branch first"
```

If on the base branch, stop and ask (one question) which branch holds the plan; re-run `ctx`.

Read `$DOCS_DIR/REVIEW_CHECKLIST.md`: it holds the project's concrete checks for the
categories the sections below name. Read `$DOCS_DIR/development-commands.md` for the test
layers and their commands; the test review refers to them by name.

Capture `PLAN_KIND`, `PLAN_MODE`, `REGISTRY_KEY`, `PARENT_EPIC`, `MILESTONE`, `UI_SCOPE`,
`RISK_TAGS`, and the source fields from the metadata output.

### 2. Route by plan kind

- `plan_kind: epic`: capture the slug, run Step 0 (parts 1, 2, 4, and 5) against the epic as
  a whole, then go to step 7 (epic review). No test artifact is written for an epic.
- `parent_epic` set: read the parent and treat the child's "Inherited constraints" section as
  the contract.

```bash
"$BIN/obsidian-workflow" epic-get --slug "$PARENT_EPIC"
```

  Check that the child does not violate an inherited constraint: every locked decision it
  touches is honored, its scope stays inside the milestone's stated scope, and its done-when
  criteria are the milestone's. A violation is a Step 0 finding: stop and ask whether to
  change the child or escalate to the epic. Never relitigate the constraint inside the child.
- Anything else: the full procedure.

### 3. Design doc check and retrospective

Read `AGENTS.md`, then `$DOCS_DIR/PRD.md`, `APP_FLOW.md`, `TECH_STACK.md`,
`FRONTEND_GUIDELINES.md`, `FRONTEND_STRUCTURE.md`, `BACKEND_STRUCTURE.md`,
`IMPLEMENTATION_PLAN.md`, `LESSONS.md`, and `TODOS.md`. They are the source of truth for the
problem statement, constraints, and chosen approach. `LESSONS.md` is the record of prior
mistakes and guardrails: check explicitly for repeat failures before implementation begins.

Retrospective:

```bash
git log --oneline "$BASE_BRANCH"..HEAD
```

Prior commits that suggest a previous review cycle (review-driven refactors, reverts) mean the
plan re-touches an area that was already trouble once. Note what changed, whether this plan
touches the same areas, and review those areas more aggressively. A recurring problem area is
an architectural smell; surface it in Section 1.

When a question needs outside knowledge, use web search; if it is unavailable, say "Search
unavailable, proceeding with in-distribution knowledge only." When first-principles reasoning
shows the conventional approach is wrong, name it and record it in `$DOCS_DIR/LESSONS.md`
under `## Decisions`.

### 4. Step 0: scope challenge

Answer before reviewing anything:

1. **Existing code leverage.** What existing code already partially or fully solves each
   sub-problem? Can we capture outputs from existing flows rather than build parallel ones?
2. **Minimum set.** What is the minimum set of changes that achieves the stated goal? Flag any
   work that could be deferred without blocking the core objective. Be ruthless about scope
   creep.
3. **Complexity check.** More than 8 files touched, or more than 2 new classes or services, is
   a smell. Challenge whether the same goal can be met with fewer moving parts.
4. **TODOS cross-reference.** Are any deferred items in `TODOS.md` blocking this plan? Can any
   be bundled into this change without expanding scope? Does this plan create new work that
   should become a TODO?
5. **Completeness check.** Is the plan doing the complete version or a shortcut? Where a
   shortcut saves human-hours but only minutes AI-assisted, recommend the complete version.
   Boil the lake.

If the complexity check triggers, ask one question: explain what is overbuilt, propose a
minimal version that achieves the core goal, and offer A) reduce, B) proceed as planned.
Record the answer as `MODE`: `SCOPE_REDUCED` or `FULL_REVIEW`. If it does not trigger, present
the Step 0 findings and continue; `MODE` is `FULL_REVIEW`.

Once the user accepts or rejects a reduction, commit fully. Do not re-argue for smaller scope
in later sections, and do not silently drop planned components.

### 5. The four review sections

The full rubric per section is in `references/review-sections.md`; read it now. Work one
section at a time, in order, at most eight top issues per section. After each section, stop:
one question per genuine decision (see "Asking about an issue"). Start the next section only
when every issue in this one is resolved or recorded as unresolved.

1. **Architecture.** System design and component boundaries; the dependency graph and
   coupling; data-flow patterns and bottlenecks; scaling and single points of failure;
   security architecture (auth, data access, API boundaries); migration safety and
   background-job idempotency where the plan touches them; which flows deserve diagrams in
   the plan or in code comments; one realistic production failure per new codepath or
   integration point and whether the plan accounts for it.
2. **Code quality.** Organization and module structure by layer (data, API, service, UI,
   shared); DRY violations, aggressively; error-handling patterns and missing edge cases,
   called out explicitly; technical-debt hotspots; over- and under-engineering against the
   preferences; new dependencies in any layer; operational scripts the plan needs; whether
   existing ASCII diagrams in touched files are still accurate.
3. **Tests.** Draw the coverage diagram and write the test artifact (step 6) before asking
   any test question. Every item in the diagram gets a test in the layer it lives in, using
   the layers and commands `development-commands.md` names. Prompt or LLM changes: which eval
   suites, cases, and baselines, then one question to confirm the eval scope.
4. **Performance.** Query efficiency (a query per row, eager loading, an index for every new
   query); memory bounds; caching and its invalidation; slow or high-complexity paths; render
   efficiency where there is UI; background-job sizing.

Every category above has concrete, stack-specific checks in `REVIEW_CHECKLIST.md`. Apply them
where the category appears and cite the entry in the finding.

### 6. Test coverage diagram and test artifact

Inside Section 3, first draw the coverage diagram: every new UX flow, data flow, codepath,
branching outcome, background job, integration, and error path, with what is new about each.
For each item name the test type, the layer, whether the plan has it, and the happy, failure,
and edge tests. The format is in `references/review-sections.md`.

Then write the test artifact. Its format and rules are in `references/test-artifact.md`; read
it now.

```bash
mkdir -p "$(dirname "$TEST_ARTIFACT")"
[ -f "$TEST_ARTIFACT" ] && echo "Existing artifact: $TEST_ARTIFACT (merge, do not replace)"
```

If the artifact exists (a rerun, or an adversarial pass already extended it), read it in full
and edit in place: update stale expectations, add what the diagram surfaced, never collapse a
numbered critical path into a summary bullet. The artifact is consumed by `/execute-plan`
(what to test, where, in what order), `/plan-adversarial-review` (which hardens it in place),
and `/qa` (its primary input). It holds what a tester needs to know, not implementation
detail.

### 7. Epic review (epics only)

Replace steps 5 and 6 with `references/epic-review.md`; read it now. It reviews sequencing,
the milestone dependency map, and rollout and rollback at every milestone boundary, and
produces the dependency graph and the end-state architecture diagram. Then continue at step 8.

### Asking about an issue

On top of the shared question format:

- One issue, one question. Describe it concretely, with file and line references.
- Two or three options, including "do nothing" where reasonable. One sentence per option:
  effort on both scales, risk, maintenance burden. The user should pick in under five seconds.
- One sentence mapping the recommendation to a named engineering preference.
- Number issues, letter options: `3A`, `3B`. Mark findings **CRITICAL GAP**, **WARNING**, or
  **OK**.
- Escape hatch: no issues, say so; obvious fix, state it and move on. A question is for a
  genuine decision with real tradeoffs.
- If the user does not answer or moves on, record the issue under "Unresolved decisions".
  Never silently default.

### 8. Required outputs

Write each into `_PLAN_FILE`; templates in `references/output-templates.md`.

- **NOT in scope.** Work considered and deferred, one-line rationale each.
- **What already exists.** Existing code and flows that partly solve sub-problems, and
  whether the plan reuses them or rebuilds them.
- **Diagrams.** ASCII diagrams in the plan for every non-trivial data flow, state machine, or
  pipeline; plus the list of implementation files that should carry inline diagram comments,
  by layer. Epics: the milestone dependency graph and end-state architecture.
- **Failure modes.** For each new codepath in the coverage diagram, one realistic production
  failure (timeout, nil reference, race, stale data) and whether a test covers it, error
  handling exists, and the user sees a clear error or nothing. No test, no handling, and
  silent is a **CRITICAL GAP**.
- **Unresolved decisions.** "Decisions that may bite you later", by issue number.

### 9. TODOS

Write to `$DOCS_DIR/TODOS.md` in the format its own header defines. One question per TODO,
never batched, never skipped silently. For each: What, Why, Pros, Cons, Context (enough to
resume cold in three months), Effort (S/M/L/XL, both scales), Priority (P0 to P4), Depends
on. Then: A) add to TODOS.md, B) skip, not valuable enough, C) build it now in this plan. A
TODO without context is worse than none: it records that an idea was captured while losing
the reasoning.

### 10. Confirm the workflow flags

`workflow-state --next` decides whether design review and adversarial review are on the path
from two frontmatter keys. The reviewed plan is the last word on both, so confirm them now.

- `ui_scope`: `true` when anything a user sees changes (a page, component, copy, layout,
  interaction). Compare the stored value with what the review found.
- `risk_tags`: drawn only from `auth`, `infra`, `data`, `payments`, `security`, `migration`.
  A migration, an auth path, or an external dependency the review surfaced adds its tag.

When the stored values match the review, say so in one line. When they differ or are unset,
ask one question with your recommendation, then set them:

```bash
"$BIN/obsidian-workflow" plan-metadata-set "$_PLAN_FILE" \
  --set ui_scope="$UI_SCOPE" --set risk_tags="$RISK_TAGS_JSON"
```

### 11. Fold in the decisions

Per `_shared/plan-footer.md`: edit `_PLAN_FILE` in place, one targeted edit per decision
(directory layout, config blocks, code examples, success criteria, next steps, open
questions, deferred), each with an `Eng review N: decision` breadcrumb. Preserve every
frontmatter key. Update the Eng Review row of the REVIEW REPORT with a one-line findings
summary; if the plan lacks the footer, add it from the shared template.

### 12. Completion summary

Fill in the completion summary from `references/output-templates.md` (Step 0 outcome,
inherited constraints, issues per section, test diagram and gaps, artifact path, NOT in
scope, What already exists, diagrams, failure modes and critical gaps, TODOS, flags,
unresolved decisions, lake score) and present it. Epics use the epic variant.

## Completion

Sync state per `_shared/obsidian-sync.md` with `STATUS_VALUE=eng-reviewed` and
`REVIEW_VALUE=eng-reviewed`, then log the review:

```bash
"$BIN/review-log" --skill plan-eng-review --status "$STATUS" \
  --field mode="$MODE" --field unresolved="$UNRESOLVED" --field critical_gaps="$CRITICAL_GAPS" \
  --field model="<your model>" ${PLAN_KIND:+--field plan_kind="$PLAN_KIND"}
```

`STATUS` is `clean` when unresolved decisions and critical gaps are both zero, otherwise
`issues_open`. `MODE` is `FULL_REVIEW` or `SCOPE_REDUCED`. The `model` field lets the
adversarial review choose a different model family.

Report `DONE` or `DONE_WITH_CONCERNS` with the change description from the completion
protocol. `BLOCKED` and `NEEDS_CONTEXT` set `implementation_status` and `reason` only. If the
user decides in Step 0 to drop the plan, report `ABANDONED` and run
`"$BIN/obsidian-workflow" abandon "$REGISTRY_KEY" --reason "..."`.

This review is the shipping gate: nothing is cleared for implementation until it is logged
`clean` against the current plan file. Then the dashboard and next step per
`_shared/dashboard.md`:

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
