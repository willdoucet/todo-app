---
name: review-implementation
description: >-
  First code-level review after /execute-plan, before anything ships. Diffs the branch against
  the base branch, audits scope drift and plan completion against the plan and its summary,
  applies stack-neutral structural categories (data safety, concurrency, trust boundaries,
  conditional side effects, enum completeness, error handling, efficiency) using the project's
  concrete checks from REVIEW_CHECKLIST.md, draws a test-coverage diagram and writes the gap
  tests, fixes what it finds in place (auto-fix or ask), runs an adversarial subagent sized to
  the diff, captures TODOs, and blocks on stale documentation. Use when asked to "review this
  PR", "review the implementation", "pre-landing review", "review my diff", or "check my diff".
  Never commits; never flips the plan to shipped.
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# Review implementation

The first of two code reviews between implementation and shipping. Reads the whole diff, finds
the structural problems tests do not catch, fixes them in place, writes the missing tests, and
records a review-log entry the dashboard reads. The second review is `/final-review`, in fresh
context; shipping is `/ship`.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/plan-discovery.md`
- `_shared/obsidian-sync.md`
- `_shared/docs-contract.md`
- `_shared/plan-footer.md`
- `_shared/dashboard.md`

References in this directory, loaded when the procedure reaches them:
`references/review-categories.md`, `references/plan-completion-audit.md`,
`references/coverage-diagram.md`, `references/adversarial-prompts.md`.

## Use when

- `/execute-plan` finished and the plan is `ready-for-review`.
- The user asks to review the diff on a feature branch before it ships.
- The user asks for a thorough, paranoid, or "run all passes" review; that raises the
  adversarial tier regardless of diff size.

## Do not use when

- On the base branch, or there is no diff against it. Nothing to review.
- The work is a quickfix; `/quickfix` reviews itself and ships in one session.
- A second, independent opinion is wanted; that is `/final-review`.

## Procedure

### 1. Ground, refuse the base branch, confirm there is a diff

Follow the preamble, including `REVIEW_CHECKLIST.md`. Then:

```bash
[ "$ON_BASE" = "1" ] && echo "Nothing to review — on $BASE_BRANCH"
git fetch origin "$BASE_BRANCH" --quiet 2>/dev/null || true
git diff "$BASE_BRANCH" --stat
```

Stop on the base branch or with an empty diff. Do not write a review-log entry when stopping
here. Execute-plan never commits, so most of the diff is usually uncommitted:
`git diff "$BASE_BRANCH"` (working tree against base) is the review surface. Use
`"$BASE_BRANCH"...HEAD` only when you specifically want committed work.

### 2. Resolve the plan, its frontmatter, and the summary

Follow `_shared/plan-discovery.md` including its metadata step. Read `$_PLAN_FILE` in full,
then the summary file (`$SUMMARY_FILE`, or `${_PLAN_FILE%.md}-summary.md` when `_PLAN_FILE` is
outside `$PLAN_DIR`). The summary's step notes and `## Update-docs conclusion` are evidence for
steps 5 and 11. An explicit plan path from the user is authoritative over anything remembered
from conversation.

If no plan resolves, say "No plan file detected" and run the review without the plan-completion
audit; scope drift then relies on commit messages, the pull request body, and `TODOS.md`.

### 3. Read the documentation set

Read, in `$DOCS_DIR`: `PRD.md`, `APP_FLOW.md`, `TECH_STACK.md`, `FRONTEND_GUIDELINES.md`,
`FRONTEND_STRUCTURE.md`, `BACKEND_STRUCTURE.md`, `IMPLEMENTATION_PLAN.md`, `LESSONS.md`,
`REVIEW_CHECKLIST.md`, `development-commands.md`, and `TODOS.md` if present. These are the
source of truth for the problem statement, constraints, and chosen approach. If a doc
disagrees with the codebase in a way this branch did not cause, flag it (see something, say
something) and ask what to do; do not silently rewrite it.

### 4. Get the full diff

```bash
git diff "$BASE_BRANCH" --stat
git diff "$BASE_BRANCH"
git log "$BASE_BRANCH"..HEAD --oneline
gh pr view --json body -q .body 2>/dev/null || true
```

Read the entire diff before commenting. For every changed file, read the full file, not just
the hunks. Do not flag anything the diff already addresses.

### 5. Scope drift and plan completion audit

Did they build what was asked, nothing more, nothing less?

1. Establish the **stated intent** from the plan (or, without one, from commit messages, the
   pull request body, and `TODOS.md`). The pull request usually does not exist yet; that is
   the common case.
2. Extract the plan's actionable items and classify each against the diff as DONE, PARTIAL,
   NOT DONE, or CHANGED, following `references/plan-completion-audit.md`. Cross-check with the
   summary's boxes: a `[✓]` step with no evidence in the diff is a finding, not a pass.
3. Compare the changed files with the intent. Scope creep: unrelated files, unplanned features
   or refactors, "while I was in there" changes. Missing requirements: NOT DONE items, stated
   requirements without tests, partial implementations.
4. Print the `PLAN COMPLETION AUDIT` block and the `Scope Check` block from the reference
   before the main review begins.
5. Audit the plan reviews' declarations: for each earlier gating review on this plan whose
   latest run declared `none` (its `review-read` row shows `rereview=[]`), read the breadcrumbs
   it left in the plan against the domains of the reviews that ran before it (the test in
   `_shared/dashboard.md` → "When your review changes what an earlier review approved"); an
   undeclared reversal you find is yours to declare, and this review cannot demand a plan
   review (a demand stays in its stage), so record it as your own `--field concern=` in step
   13 and edit the overruled plan text in place with a breadcrumb naming yourself.

Informational: this step never blocks by itself. NOT DONE items become findings in step 9.

### 6. Two-pass structural review

Read `references/review-categories.md`. Pass 1 is critical: data and migration safety,
concurrency and background-job idempotency, trust boundaries and authorization, enum and value
completeness. Pass 2 is informational: conditional side effects and error handling, magic
values and string coupling, dead code and consistency, test gaps, view and accessibility,
query and render efficiency, dependency and bundle impact.

The categories are stack-neutral by design. The concrete checks for this project's stack live in
`$DOCS_DIR/REVIEW_CHECKLIST.md`; apply every entry there that matches a changed file, and cite
the entry in the finding.

For each finding:

```
[CRITICAL|INFORMATIONAL] file:line — problem in one line
  Fix: recommended fix in one line
```

**Enum and value completeness reads outside the diff.** When the diff introduces a new enum
value, status, tier, or type constant, search for every file referencing sibling values and
read them to confirm the new value is handled. Within-diff review is insufficient here.

**Search before recommending.** For concurrency, caching, auth, or framework-specific fixes,
verify the pattern is current for the versions in `TECH_STACK.md`, check for a built-in
before recommending a workaround, and verify signatures against current docs. If web search is
unavailable, say so and proceed with in-distribution knowledge.

### 7. Design check (conditional)

```bash
git diff "$BASE_BRANCH" --name-only | grep -E '\.(jsx|tsx|vue|svelte|css|scss|html)$' | head -20
```

No matches: skip silently. Otherwise this is a static check; the live, graded audit is
`/design-review`, which the dashboard lists when the plan has `ui_scope`.

1. Calibrate against `$DOCS_DIR/FRONTEND_GUIDELINES.md`. Patterns it blesses are not findings.
   Without it, use universal design principles.
2. Read each changed frontend file in full.
3. Classify: mechanical CSS fixes (removed focus outlines, `!important`, sub-16px inputs on
   mobile) are AUTO-FIX; design judgment is ASK; intent-based guesses are "Possible — verify
   visually".
4. **Reconcile with the plan's `## Design Source of Truth`** when present. Prototype bundle:
   compare `$(dirname "$_PLAN_FILE")/prototype/` with the implemented page. Mockups: compare
   each mockup with its component. Flag material divergence as ASK: layout, information
   architecture, interaction states (loading, empty, error, success, partial), responsive
   behavior at the documented breakpoints. Token-level differences (exact spacing, shade,
   weight) belong to the guidelines check above, not here. If the section records a
   **Design system pin SHA**, compare it with `"$BIN/design-sync-check" --pin-sha`; when they
   differ, add one INFORMATIONAL note that token drift may be intentional design-system
   evolution. A non-zero exit means no current SHA: note the helper's message instead.
5. Report under a `Design Review` header. These findings enter the same fix-first flow.

### 8. Test coverage diagram and gap tests

Follow `references/coverage-diagram.md`: trace every changed code path and user flow, check
each branch against an existing test, score quality with stars, print the diagram, then
generate tests for the gaps. The goal is every path covered.

Rules that do not bend:

- **Regression rule.** When the audit finds code that worked before and the diff broke, write
  the regression test immediately. No question, no skipping.
- Generated tests follow the project's existing test layout, fixtures, and naming. Find the
  nearest existing test for the same module and match it.
- Run new tests with the commands from `$DOCS_DIR/development-commands.md`, read the output,
  and quote it. A test you did not run is a gap, not coverage.
- Test-only diffs skip this step: "No new application code paths to audit."

### 9. Fix-first

Every finding gets an action. Print the header:
`Pre-landing review: N issues (X critical, Y informational)`.

1. **Classify.** AUTO-FIX: mechanical, one correct answer (missing import, unused variable,
   typo, missing type annotation, a simple unit test for a pure function). ASK: judgment,
   architecture, trade-offs, anything where the fix could go several ways, tests needing new
   infrastructure, tests for ambiguous behavior.
2. **Apply every AUTO-FIX** and print one line each:
   `[AUTO-FIXED] file:line problem → what you did`.
3. **Ask about each ASK item separately**, in the shared question format, one decision per
   question: severity, the problem in plain English, the recommended fix,
   `A) Fix as recommended  B) Skip`, with a recommendation. Ask them back to back; do not
   combine two findings into one question.
4. **Apply the approved fixes** and print what changed. Then re-run the affected tests.

**Verification of claims.** Before the final output: a claim that a pattern is safe cites the
line proving it; "handled elsewhere" cites the handling code; "tests cover this" names the
file and test. Never "likely" or "probably". "This looks fine" is not a finding; cite evidence
or flag it unverified.

Keep edits limited to review findings and approved ASK items. Never revert unrelated user
changes. Never commit, push, or open a pull request.

### 10. TODOS capture

Read `$DOCS_DIR/TODOS.md`. Note which open items this branch closes ("addresses TODO:
<title>") and which provide context for findings. For work this branch surfaces that should
be deferred, write a TODO in the format that file's own header defines (What, Why, Context,
Effort, Priority P0–P4, Depends on). Ask one question per candidate TODO before writing it,
never batched, never skipped silently. Completed items move to the file's Completed section.

### 11. Documentation staleness (blocking)

Two checks, both required.

```bash
"$BIN/doc-guard" --range "$BASE_BRANCH..HEAD"
git status --porcelain | grep -q . && { git add -A; "$BIN/doc-guard" --staged --dry-run; }
```

The range covers committed work; the staged pass covers the uncommitted working tree that
execute-plan leaves behind (staging is not committing; `/ship` stages everything anyway).

Then reason about it independently of the helper. For every changed non-exempt path, find its
owning doc section (`"$BIN/doc-guard" --explain <path>`) and check whether that doc changed in
this diff and whether the change actually describes the new behavior. Also check `AGENTS.md`
when commands, structure, dependencies, or env vars changed. Compare with the summary's
`## Update-docs conclusion`; a "no doc impact" conclusion that the map contradicts is stale.

If a mapped area changed and its owning doc did not, or the doc changed without describing the
new surface: the verdict is **NOT CLEARED**, the review-log status is `issues_open`, and the
completion summary says "run `/update-docs`, then re-run `/review-implementation`". Stale
docs are the one finding this review does not fix itself; `/update-docs` owns the edit.

### 12. Adversarial subagent (auto-scaled)

```bash
read DIFF_INS DIFF_DEL < <(git diff "$BASE_BRANCH" --numstat | awk '{i+=$(1); d+=$(2)} END {print i+0, d+0}')
DIFF_TOTAL=$((DIFF_INS + DIFF_DEL)); echo "DIFF_SIZE: $DIFF_TOTAL"
```

- Under 50 lines: skip, print "Small diff (N lines) — adversarial subagent skipped", no log
  entry.
- 50–199: medium tier. 200 and up: large tier. An explicit request for a thorough or
  paranoid review forces the large tier.
- When `adversarial-subagent` reads `failed` or `stale` on this plan (`review-read`), run the
  subagent whatever the diff size, at the medium tier or above, and log its entry: only a new
  subagent entry clears a stale one (`resolved` is refused for it), so skipping here would
  leave `--next` naming this review with no way out. If the subagent is unavailable then,
  stop with `BLOCKED` instead of continuing without it.

Dispatch a subagent with the tier's prompt from `references/adversarial-prompts.md`. It has
fresh context and no bias from the structured review; that independence is the point. Without
a subagent tool, follow the tool map: do the pass yourself in a clearly separated section and
say it lacks fresh context, or prefer switching harness.

Present findings under `ADVERSARIAL REVIEW (subagent):`. FIXABLE findings enter the fix-first
flow of step 9; INVESTIGATE findings are informational. Then print the synthesis block from the
reference (agreed by both passes, unique to structured, unique to adversarial); agreed findings
are fixed first. If the subagent fails or times out: "Adversarial subagent unavailable.
Continuing without adversarial review."

```bash
"$BIN/review-log" --skill adversarial-subagent --status STATUS --plan "$(basename "$_PLAN_FILE")" \
  --field tier=medium|large --field issues_found=N
```

`STATUS` is `clean` with no findings, otherwise `issues_open`. A failed subagent entry gates
like any other tier: after fixing its findings, either re-run the subagent (a new entry) or
resolve it in step 13, after this review's own entry (the command is there; run earlier,
`review-log` rejects it because the resolver has no passed entry yet).

### 13. Persist the result and update the plan footer

```bash
"$BIN/review-log" --skill review-implementation --status STATUS --plan "$(basename "$_PLAN_FILE")" \
  --field issues_found=N --field critical=N --field informational=N \
  --field model=<your model, when known>
```

`STATUS` is `clean` only when no findings remain unresolved after fix-first and the
adversarial pass, no critical gap is open, and step 11 passed. Otherwise `issues_open`. The
words are defined once in `_shared/obsidian-sync.md` → Review log. Counts are what remains
unresolved, not what was found. Skip this entry entirely if the review stopped in step 1.

Then, when the subagent's entry from step 12 is `issues_open` and this review itself logged
`clean` (every finding fixed or decided), resolve it, naming where each finding was closed.
If this review logged `issues_open`, leave the subagent failed: a failed resolver cannot
vouch. After your own entry, never before:

```bash
"$BIN/review-log" --skill adversarial-subagent --status resolved --plan "$(basename "$_PLAN_FILE")" \
  --field resolved_by=review-implementation --field note="<commit or file per finding>"
```

Update the `Implementation Review` row of `## REVIEW REPORT` in `$_PLAN_FILE` per
`_shared/plan-footer.md`: status and a one-line findings summary. Edit in place; preserve the
frontmatter.

A review that overrules something the plan states (a premise, a step, a success criterion, a
decision an earlier review recorded) edits that text in place with a breadcrumb naming itself,
says so in its REVIEW REPORT row, and passes the same sentence as `--field concern=` on its own
entry: a plan review cannot usefully re-run on an implementing plan, so the record is the
control. Declaring `--rereview <skill>` is optional at the ship stage and stays in its stage
(QA, the design audit, the other code review); never declare `rereview=adversarial-subagent`
from the invocation that just logged that subagent's run: a demand dated at or after a run
always reads as outstanding (`>=`), so the subagent would read stale the moment it finished.

If the user corrected you, add a Corrections Log row to `LESSONS.md`. A repeatable class of
bug found here becomes a new entry in `REVIEW_CHECKLIST.md`.

## Completion

Report one status per the completion protocol, then this summary:

```
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT

SCOPE CHECK: CLEAN | DRIFT DETECTED | REQUIREMENTS MISSING — plan items N done / M partial / K not done
STRUCTURAL REVIEW: N issues (X critical, Y informational); fixed A, skipped B by user choice
COVERAGE: P/Q paths tested (R%); gap tests written: [files]
DOCUMENTATION: current | STALE — run /update-docs
ADVERSARIAL: tier, N findings (agreed F, unique U) | skipped (small diff) | unavailable
TODOS: closed [titles] / added [titles] / none
OPEN CONCERNS: [list or none]
```

Then the change description. Then, on DONE and DONE_WITH_CONCERNS, sync per
`_shared/obsidian-sync.md` with the `review-implementation` row: `workflow_status` unchanged,
`--append review_status=impl-reviewed`. BLOCKED and NEEDS_CONTEXT follow the protocol's table.
This review never sets `shipped` and never checks a note box; `/ship` does both after
`/final-review`. Never commit.

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
