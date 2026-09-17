---
name: plan-ceo-review
description: >-
  CEO/founder-mode plan review. Rethink the problem, find the 10-star product, challenge
  premises, and expand scope when it makes a better product. Four modes: SCOPE EXPANSION
  (dream big), SELECTIVE EXPANSION (hold scope, cherry-pick expansions), HOLD SCOPE (maximum
  rigor), SCOPE REDUCTION (strip to essentials). Required for epics, where it reviews the
  milestone decomposition instead of implementation detail. Use when asked to "think bigger",
  "expand scope", "strategy review", "rethink this", "CEO review", or "is this ambitious
  enough". Suggest it for big product changes, new user-facing features, or scope decisions.
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# CEO plan review

Rethinks a plan from the founder's chair: is this the right problem, the right scope, the right
trajectory? Picks one of four scope modes with the user, then reviews with maximum rigor in
that mode. Produces the plan edited in place (decisions folded in with breadcrumbs, REVIEW
REPORT row updated), TODOS captured, PRD and roadmap brought into sync, and a review-log entry.
Never writes code.

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

- Scope is in question: a greenfield feature, a big product or business change, a new
  user-facing surface, or the user asks whether the plan is ambitious enough or overbuilt.
- The plan is an epic (`plan_kind: epic`). CEO review is required before any milestone starts.
- The user says "think bigger", "go big", "cathedral", "strip this down", or "rethink this".

## Do not use when

- There is no plan yet. Run `/office-hours` first.
- The question is architecture, tests, or performance on an accepted scope. That is
  `/plan-eng-review`, the shipping gate; this review is optional for feature plans.
- The plan is already implementing or shipped. A scope change now is a new plan.

## Posture

You are not here to rubber-stamp the plan. You are here to make it extraordinary, catch every
landmine before it explodes, and make sure it ships at the highest standard. Your posture
depends on the mode the user picks in Step 0; once picked, commit to it and never drift.

**Prime directives**

1. Zero silent failures. Every failure mode is visible to the system, the team, and the user.
2. Every error has a name: the exception class, its trigger, what catches it, what the user
   sees, whether it is tested. A catch-all handler is a smell; call it out.
3. Data flows have shadow paths: nil input, empty input, upstream error. Trace all four.
4. Interactions have edge cases: double-click, navigate away mid-action, slow connection,
   stale state, back button. Map them.
5. Observability is scope, not an afterthought. Dashboards, alerts, and runbooks are
   first-class deliverables.
6. Diagrams are mandatory. ASCII art for every new data flow, state machine, pipeline,
   dependency graph, and decision tree.
7. Everything deferred is written down in `$DOCS_DIR/TODOS.md` or it does not exist.
8. Optimize for the six-month future. If this plan creates next quarter's nightmare, say so.
9. You may say "scrap it and do this instead." Table the fundamentally better approach now.

**Engineering preferences** (map every recommendation to one of these)

- DRY: flag repetition aggressively.
- Well-tested is non-negotiable; too many tests beats too few.
- Engineered enough: not fragile or hacky, not prematurely abstract.
- More edge cases handled, not fewer; thoughtfulness over speed.
- Explicit over clever. Minimal diff: the fewest new abstractions and files touched.
- Observability and security are not optional: new codepaths get logs or metrics and a
  threat model.
- Deployments are not atomic: plan for partial states, rollbacks, and feature flags.
- ASCII diagrams in code comments for complex designs, by layer: data layer (state
  transitions), service layer (pipelines), API layer (request flow), shared behaviors, and
  tests with non-obvious setup. Diagram maintenance is part of the change; a stale diagram is
  worse than none.

**Priority under context pressure:** Step 0 > system audit > exception and rescue map > test
diagram > failure modes > opinionated recommendations > everything else. Never skip the first
five.

## Procedure

### 1. Ground

Follow the preamble, then plan discovery including the metadata read. Then:

```bash
[ "$ON_BASE" = "1" ] && echo "On $BASE_BRANCH — switch to the plan's branch first"
```

If on the base branch, stop and ask (one question) which branch holds the plan; re-run `ctx`.

Then read the earlier reviews of this plan:

```bash
"$BIN/review-read"
```

For every earlier review whose disposition is `failed`, read its open items and decide as you
go: if this review closes one, say where in the plan you closed it and note it for completion;
if it stays open, carry it forward in your own summary so the next review sees it. Never leave
a failed review unmentioned.

Read `$DOCS_DIR/REVIEW_CHECKLIST.md`. It holds this project's concrete checks for the
categories the sections below name (migration safety, query efficiency, background-job
idempotency, render efficiency, and whatever else the stack needs). Apply them wherever a
section names the category; the sections themselves stay stack-neutral.

Capture `PLAN_KIND`, `PLAN_MODE`, `REGISTRY_KEY`, `PARENT_EPIC`, and the source fields from the
metadata output. When `parent_epic` is set, read the parent with `epic-get` and treat the
child's "Inherited constraints" section as locked: Step 0 may challenge how the child meets
them, never whether they apply. If the child breaks one, stop and ask.

### 2. System audit

Not the review; the context you need to review intelligently.

```bash
git log --oneline -30
git diff "$BASE_BRANCH" --stat
git stash list
```

Read `AGENTS.md`, then `$DOCS_DIR/PRD.md`, `APP_FLOW.md`, `TECH_STACK.md`,
`FRONTEND_GUIDELINES.md`, `FRONTEND_STRUCTURE.md`, `BACKEND_STRUCTURE.md`,
`IMPLEMENTATION_PLAN.md`, `LESSONS.md`, and `TODOS.md`. While reading PRD,
IMPLEMENTATION_PLAN, and TODOS:

- Note every TODO this plan touches, blocks, or unlocks.
- If the plan conflicts with anything in these docs, ask the user (one question) and resolve.
- Check whether deferred work from prior reviews relates to this plan; flag dependencies in
  both directions.
- Map known pain points (PRD, LESSONS) to this plan's scope.

Map: the current system state; what is in flight (open PRs, other branches, stashes); the
pain points most relevant to this plan; FIXME and TODO comments in files the plan touches.

**Retrospective.** Read the branch's git log for signs of a prior review cycle (review-driven
refactors, reverts). Note what changed and whether this plan re-touches those areas. Review
previously problematic areas more aggressively; a recurring problem area is an architectural
smell and gets surfaced as one.

**Taste calibration** (EXPANSION and SELECTIVE EXPANSION only). Name two or three files or
patterns in the codebase that are particularly well designed, as style references, and one or
two that are frustrating, as anti-patterns not to repeat.

Report the audit findings before Step 0. When a question needs outside knowledge, use web
search; if it is unavailable, say "Search unavailable, proceeding with in-distribution
knowledge only." When first-principles reasoning shows the conventional approach is wrong,
name it and record it in `$DOCS_DIR/LESSONS.md` under `## Decisions`.

### 3. Route by plan kind

- `plan_kind: epic`: run Step 0 parts 0A, 0B, 0C, and 0F against the epic's end state, then
  go to step 5 (epic decomposition) instead of the ten sections. Skip 0D and 0E.
- Anything else: Step 0 in full, then the ten sections in step 6.

### 4. Step 0: nuclear scope challenge and mode selection

**0A. Premise challenge.** Is this the right problem? Could a different framing be dramatically
simpler or more impactful? What is the real user or business outcome, and is the plan the most
direct path to it or a proxy? What happens if we do nothing: a real pain point or a
hypothetical one?

**0B. Existing code leverage.** Map every sub-problem to code that already solves it, partly or
fully. Can we capture outputs from existing flows instead of building parallel ones? Is the
plan rebuilding something that exists? If so, why is rebuilding better than refactoring?

**0C. Dream state.** Describe the ideal system twelve months out and whether the plan moves
toward it or away from it:

```
  CURRENT STATE            THIS PLAN                12-MONTH IDEAL
  [describe]      --->     [describe delta]  --->   [describe target]
```

**0D. Mode-specific analysis.** Run the analysis for the mode you expect to recommend. The
full checklist per mode is in `references/mode-guide.md`; read it now.

- EXPANSION: the 10x check, the platonic ideal, at least three delight opportunities.
- SELECTIVE EXPANSION: the HOLD SCOPE analysis, plus a list of expansion candidates, each
  scored on value, effort on both scales, and whether it changes the architecture.
- HOLD SCOPE: the complexity check (more than 8 files or more than 2 new classes or services
  is a smell) and the minimum set of changes that achieves the stated goal.
- REDUCTION: the ruthless cut, and "must ship together" separated from "nice to ship
  together".

**0E. Temporal interrogation** (EXPANSION, SELECTIVE EXPANSION, HOLD SCOPE). Which decisions
the implementer will hit must be resolved now, in the plan?

```
  HOUR 1 (foundations):    What does the implementer need to know?
  HOUR 2-3 (core logic):   What ambiguities will they hit?
  HOUR 4-5 (integration):  What will surprise them?
  HOUR 6+ (polish/tests):  What will they wish they had planned for?
```

Surface these as questions now, one per decision, never as "figure it out later".

**0F. Mode selection.** One question, four options, with your recommendation and why:

- A) SCOPE EXPANSION: good could be great. Propose the ambitious version, then review that.
  Push scope up. Build the cathedral.
- B) SELECTIVE EXPANSION: the core scope is right. Hold it, then cherry-pick expansions one
  question at a time; each accepted one joins the plan, each declined one becomes a TODO.
- C) HOLD SCOPE: the scope is right. Review it with maximum rigor and make it bulletproof.
  Do not silently reduce or expand.
- D) SCOPE REDUCTION: overbuilt or wrong-headed. Propose the minimal version that achieves
  the core goal, then review that. Be ruthless.

Defaults: greenfield feature, EXPANSION; bug fix, hotfix, or refactor, HOLD SCOPE; a sound
core with a few tempting adjacencies, SELECTIVE EXPANSION; more than 15 files, suggest
REDUCTION unless the user pushes back; "go big", "ambitious", "cathedral", EXPANSION without
asking. Epic children default to HOLD SCOPE; the epic already set the ambition.

Once selected, commit fully. Raise concerns once, here; after that, execute the mode
faithfully. In SELECTIVE EXPANSION, run the cherry-pick questions now, before Section 1, so
the scope under review is fixed.

### 5. Epic decomposition (epics only)

Replace the ten sections with the milestone review in `references/epic-review.md`. Read it
now. The four questions, each its own decision when the answer is not obvious:

1. Right milestones? Each maps to a user-visible or operator-visible outcome. Nothing is a
   layer ("the backend part") instead of a slice.
2. Right order? Dependencies point backward only; the riskiest unknown is retired earliest;
   nothing ships that a later milestone must undo.
3. Each shippable alone? Every milestone leaves the base branch releasable, behind a flag if
   needed, with its own rollback.
4. Sizes right? Each fits one plan or one quickfix. Too big becomes two milestones; epics are
   one level deep.

Then continue at step 7.

### 6. The ten review sections

The full rubric, tables, and diagram templates are in `references/review-sections.md`. Read
it now. Work one section at a time, in order. After each section, stop: one question per
genuine decision (see "Asking about an issue" below). If a section has no issues, or a fix is
obvious, say so and move on. Never start the next section with an issue unresolved.

1. **Architecture.** Component boundaries and the dependency graph; all four paths of every
   data flow; state machines with their impossible transitions; coupling before and after;
   what breaks first at 10x and 100x; single points of failure; security architecture per
   endpoint and mutation; one realistic production failure per integration point; rollback
   posture. Required diagram: the system with new components against existing ones.
2. **Exception and rescue map.** For every new codepath that can fail: what goes wrong, the
   exception class, whether it is caught, the rescue action, what the user sees. Catch-alls
   are a smell; message-only logging is insufficient; every rescue retries, degrades visibly,
   or re-raises with context. Each GAP gets a rescue action and a user-visible outcome. LLM
   calls get the malformed, empty, invalid-structure, and refusal cases.
3. **Security and threat model.** Attack surface; validation of every new input across nil,
   empty, wrong type, too long, unicode, and injection; authorization and object-reference
   scoping; secrets; new dependencies and their track record; data classification; injection
   vectors including prompt injection; audit logging. Each finding: likelihood, impact,
   mitigated or not.
4. **Data flow and interaction edge cases.** The shadow-path diagram per data flow; the
   interaction table (double submit, stale session token, deploy mid-action, navigate away,
   timeout, retry in flight, zero and ten thousand results, mid-page changes, partial job
   failure, duplicate job, backed-up queue). Every unhandled cell is a gap with a fix.
5. **Code quality.** Fit with existing patterns; DRY with file and line; naming; error
   handling patterns (Section 2 holds the specifics); missing edge cases; over- and
   under-engineering; any new function that branches more than five times.
6. **Tests.** The test coverage diagram (new UX flows, data flows, codepaths, background
   work, integrations, error paths); per item the test type, whether the plan has it, and
   the happy, failure, and edge tests. Test ambition: the 2am-Friday test, the hostile-QA
   test, the chaos test. Pyramid shape, flakiness risk, load tests. Prompt or LLM changes:
   which eval suites, cases, and baselines, per `AGENTS.md` and the review checklist.
7. **Performance.** Query efficiency (related data loaded up front, an index for every new
   query); memory bounds; caching; background-job sizing and retries; the three slowest new
   paths with estimated p99; connection pressure on database, cache, queue, and HTTP pools.
8. **Observability.** Structured logs at entry, exit, and each branch; the metric that says
   it works and the one that says it is broken; trace propagation; alerts; day-one dashboard
   panels; whether a bug reported three weeks out can be reconstructed from logs alone; admin
   tooling and operational scripts; a runbook per failure mode.
9. **Deployment and rollout.** Migration safety (backward compatible, zero downtime, locks);
   feature flags; rollout order; explicit rollback steps; old and new code running together;
   environment parity; post-deploy checks for the first five minutes and the first hour;
   smoke tests.
10. **Long-term trajectory.** Debt introduced (code, operational, testing, documentation);
    path dependency; knowledge concentration; reversibility 1 to 5; fit with the ecosystem
    direction of the project's stack; the one-year question.

EXPANSION and SELECTIVE EXPANSION add to Sections 1, 8, 9, and 10: what would make this
beautiful, a joy to operate, routine to ship, and a platform for what comes next.

### Asking about an issue

On top of the shared question format:

- One issue, one question. Describe it concretely, with file and line references.
- Two or three options, including "do nothing" where reasonable. Each option in one line:
  effort on both scales, risk, maintenance burden.
- One sentence mapping the recommendation to a named engineering preference.
- Number issues, letter options: `3A`, `3B`. Mark findings **CRITICAL GAP**, **WARNING**, or
  **OK** for scannability.
- Escape hatch: no issues, say so; obvious fix, state it and move on. A question is for a
  genuine decision with real tradeoffs.
- If the user does not answer or moves on, record the issue under "Unresolved decisions".
  Never silently default.

### 7. Required outputs

Write each into `_PLAN_FILE`; templates in `references/output-templates.md`.

- **NOT in scope.** Work considered and deferred, one-line rationale each.
- **What already exists.** Existing code and flows that partly solve sub-problems, and
  whether the plan reuses them.
- **Dream state delta.** Where this plan leaves the system relative to the 12-month ideal.
- **Exception and rescue registry** (from Section 2). Feature plans only.
- **Failure modes registry.** `CODEPATH | FAILURE MODE | CAUGHT? | TEST? | USER SEES? | LOGGED?`.
  Any row with CAUGHT=N, TEST=N, and a silent user outcome is a **CRITICAL GAP**.
- **Diagrams.** All that apply: system architecture, data flow with shadow paths, state
  machine, error flow, deployment sequence, rollback flowchart. Epics: the milestone
  dependency graph and the end-state architecture.
- **Stale diagram audit.** Every ASCII diagram in files the plan touches: still accurate?
- **Unresolved decisions.** Listed by issue number, never defaulted.

### 8. TODOS

Write to `$DOCS_DIR/TODOS.md` in the format its own header defines. One question per TODO,
never batched, never skipped silently. For each: What, Why, Pros, Cons, Context (enough to
resume cold in three months), Effort (S/M/L/XL, both scales), Priority (P0 to P4), Depends
on. Then: A) add to TODOS.md, B) skip, not valuable enough, C) build it now in this plan.

Declined SELECTIVE EXPANSION candidates go through this step as vision items.

### 9. Delight opportunities (EXPANSION only)

At least five bonus chunks under thirty minutes each that make a user think "oh nice, they
thought of that". One question each: what it is, why it delights, effort. A) add to TODOS.md
as a vision item, B) skip, C) build it now.

### 10. PRD and roadmap sync

Compare the reviewed plan against `$DOCS_DIR/PRD.md` and `$DOCS_DIR/IMPLEMENTATION_PLAN.md`:

- Features in the plan but absent from the docs: add them. PRD gets the feature and its
  acceptance criteria; IMPLEMENTATION_PLAN gets a phase row (or, for an epic, the milestone
  table) with a status line and a link to `_PLAN_FILE`.
- Features that conflict with the docs: ask the user (one question), resolve, then update
  both docs and the plan.

These are narrative doc edits made with the user's decisions in hand; make them here rather
than through `/update-docs`.

### 11. Fold in the decisions

Per `_shared/plan-footer.md`: edit `_PLAN_FILE` in place, one targeted edit per decision,
with a `CEO review N: decision` breadcrumb. Preserve every frontmatter key. Update the CEO
Review row of the REVIEW REPORT with a one-line findings summary; if the plan lacks the
footer, add it from the shared template.

### 12. Completion summary

Fill in the completion box from `references/output-templates.md` (mode, audit, Step 0, one
row per section, registries, TODOS, delight, diagrams, stale diagrams, unresolved decisions)
and present it. Epics use the epic variant.

## Completion

Sync state per `_shared/obsidian-sync.md` with `STATUS_VALUE=ceo-reviewed` and
`REVIEW_VALUE=ceo-reviewed`, then log the review:

```bash
"$BIN/review-log" --skill plan-ceo-review --status "$STATUS" \
  --field mode="$MODE" --field unresolved="$UNRESOLVED" \
  --field critical_gaps_found="$CRITICAL_GAPS_FOUND" --field critical_gaps_open="$CRITICAL_GAPS_OPEN" \
  ${PLAN_KIND:+--field plan_kind="$PLAN_KIND"}
```

`STATUS` is `clean` when unresolved decisions and `critical_gaps_open` are both zero, otherwise
`issues_open`. The words are defined once in `_shared/obsidian-sync.md` → Review log.
`critical_gaps_found` is how many this review found, `critical_gaps_open` how many it leaves
open. `MODE` is one of `EXPANSION`, `SELECTIVE_EXPANSION`, `HOLD_SCOPE`, `REDUCTION`.
Then, per `_shared/dashboard.md` → "When the next step names a review that ran with issues
open", log one `resolved` entry for each earlier failed review this review closed, **after**
your own entry above (the resolver's latest entry must be passed and not earlier than the
failure).

Report `DONE` or `DONE_WITH_CONCERNS` with the change description from the completion
protocol. `BLOCKED` and `NEEDS_CONTEXT` set `implementation_status` and `reason` only. If the
user decides in Step 0 to drop the plan entirely, report `ABANDONED` and run
`"$BIN/obsidian-workflow" abandon "$REGISTRY_KEY" --reason "..."`.

Then the dashboard and next step per `_shared/dashboard.md`. Eng review remains the shipping
gate whatever this review decided; if scope expanded, add one line saying so, so that eng
review knows to validate the new architecture.

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
