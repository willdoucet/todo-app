---
name: execute-plan
description: >-
  Implements a reviewed feature plan step by step on its own branch. Reads the plan's frontmatter
  before anything else, marks it implementing, keeps a running summary file with one box per
  step, verifies each step's behavior against the plan and the eng-review test artifact,
  consumes the design source of truth and the adversarial summary, runs /update-docs when the
  last step lands, and leaves the plan in ready-for-review. Never commits and never checks a
  note box. Resumes safely, including a plan that ships in parts (partially-shipped) whose
  earlier part merged.
  Use when asked to "execute the plan", "implement the plan", "start implementation",
  "continue implementation", "resume the plan", or "pick up where we left off". Refuses epics
  and the base branch.
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# Execute plan

Turns a reviewed plan into working code, one step at a time, with proof at each step. Produces
the code, a running summary file beside the plan, updated docs through `/update-docs`, and a
plan whose status is `ready-for-review`. It does not commit, push, or touch a note box; those
belong to `/ship`.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/plan-discovery.md`
- `_shared/obsidian-sync.md`
- `_shared/docs-contract.md`
- `_shared/dashboard.md`

## Use when

- A feature plan has passed `/plan-eng-review` (and `/plan-design-review` when it has UI scope)
  and `workflow-state --next` names `/execute-plan`.
- Implementation started earlier and needs to continue, on this branch or after a merged
  part of a plan that ships in parts: the plan reads `partially-shipped` and `--next` names
  this skill.
- The plan is `blocked` or `needs-context` and the blocker is now resolved.

## Do not use when

- The file is an epic (`plan_kind: epic`). Epics never execute; start a milestone with
  `/office-hours <epic file>#Mx`.
- There is no plan yet. Use `/office-hours`.
- The change is small enough for `/quickfix`.
- The plan is already `shipped`. Supersede it with a new plan through `/office-hours`. A plan
  that ships in parts reads `partially-shipped` between its pull requests, never `shipped`
  until its last declared part ships (`ship_parts`, recorded by `/ship`).

## Procedure

### 1. Ground and refuse the base branch

Follow the preamble. Then:

```bash
[ "$ON_BASE" = "1" ] && echo "On $BASE_BRANCH — a branch is required"
```

If on the base branch, ask the user (one question) to create the branch named in the plan's
registry entry, or to name one. Create it and re-run `ctx`. Never implement on the base branch.

Then the gate. `--next` must name this skill and the review log must be whole; read both from
the JSON, never from the banner text or a substring of a reason:

```bash
"$BIN/workflow-state" --next --json | python3 -c '
import json, sys
d = json.load(sys.stdin); n = d.get("next") or {}
ok = d.get("unreadable") == 0 and n.get("skill") == "/execute-plan"
print("cleared for implementation" if ok else "NOT CLEARED: " + str(n.get("skill")) + " — " + str(n.get("reason")))
sys.exit(0 if ok else 1)'
```

A non-zero exit means stop with `NEEDS_CONTEXT`, naming what `--next` named (a review that ran
with issues open, or the unreadable-log reason). Never start implementation past an open
review; "optional" governs only a review that never ran.

### 2. Resolve the plan and read its frontmatter before anything else

Follow `_shared/plan-discovery.md`, including its metadata step. The first concrete command
after resolution is `plan-metadata-get "$_PLAN_FILE"`; run it before reading the plan body,
before creating the summary, before touching code.

Why this is unconditional: four consecutive runs of this skill once skipped the sync because the
wording made it conditional on "noticing" a flag in the plan, and twelve task boxes were
orphaned with the plan frozen at `not-started`. You cannot notice a flag without running the
command.

Copy the metadata output verbatim into the summary file (step 6) so later runs can audit what
was seen.

Refuse, and write nothing (the status table in the completion protocol is for feature plans
that are in progress), when:

- `plan_kind` is `epic`: print "Epics never execute; start a milestone with
  `/office-hours <epic file>#Mx`" and report `NEEDS_CONTEXT`.
- `implementation_status` is `shipped`: print "This plan shipped; supersede it through
  `/office-hours`" and report `NEEDS_CONTEXT`. `/ship` writes `shipped` only for the part
  that completes the plan; `partially-shipped` is not refused. When a plan meant to ship in parts
  reads `shipped` after its first pull request, it was shipped before its parts were declared:
  say so, and ask whether to supersede it through `/office-hours` or have the operator restore
  its status and declare `ship_parts`.

If `parent_epic` is set, run `epic-get` per plan-discovery and read the child's
`## Inherited constraints` section. Those are the contract. If a step would break one, stop
and ask before writing code.

### 3. Mark implementation started

Run the sync block from `_shared/obsidian-sync.md` with the `execute-plan, start` row
(`STATUS_VALUE=implementing`, no review value). Idempotent; run it on every start and resume.

### 4. Read the documentation set and LESSONS

Read, in `$DOCS_DIR`: `PRD.md`, `APP_FLOW.md`, `TECH_STACK.md`, `FRONTEND_GUIDELINES.md`,
`FRONTEND_STRUCTURE.md`, `BACKEND_STRUCTURE.md`, `IMPLEMENTATION_PLAN.md`, `LESSONS.md`,
`development-commands.md`, `REVIEW_CHECKLIST.md`. What each owns, and when each is updated,
is in `_shared/docs-contract.md`.

`LESSONS.md` is not optional. It exists because mistakes were made and caught; skipping it
means repeating them. Before each step, ask "does this step touch an area a lesson covers?"
and follow the rule when it does. Add to it when a step teaches something new.

### 5. Read the plan body and its companions

Read `$_PLAN_FILE` in full. Then:

**Test artifact.** `$TEST_ARTIFACT` is the file `/plan-eng-review` wrote, possibly extended by
`/plan-adversarial-review`:

```bash
[ -f "$TEST_ARTIFACT" ] && echo "Test artifact: $TEST_ARTIFACT" || echo "Test artifact: none"
```

When present, it is the primary guide for what to test (critical paths, key interactions, edge
cases), where (affected pages and routes), and in what order (critical paths first). Prefer its
specs over ad-hoc test decisions. When a step introduces behavior the artifact does not cover,
write the test anyway and record the gap in the summary.

**Adversarial summary.** If the plan has a `## Adversarial Review Summary` section, treat it as
source of truth for failure handling, rollout assumptions, and test expectations.

**Design source of truth.** If the plan has a `## Design Source of Truth` section, parse its
**Approach** field:

- *Prototype bundle.* Verify the offline bundle exists at `$(dirname "$_PLAN_FILE")/prototype/`.
  Missing is a warning, not a block; the plan may still be implementable from text. Read the
  bundle's `README.md` when present: it carries the handoff prompt and design rationale and is
  authoritative for information architecture, layout, and interaction. Print the live URL and
  the handoff prompt so they are at hand while coding. If the section records a
  **Design system pin SHA**, compare it with the current SHA of the watched design files:

  ```bash
  "$BIN/design-sync-check" --pin-sha
  ```

  If they differ, warn once: the prototype's tokens may lag `FRONTEND_GUIDELINES.md`;
  `/review-implementation` reconciles. A non-zero exit means no current SHA: print the
  helper's message as the warning instead and skip the comparison.
- *HTML mockups.* Verify each listed mockup exists. Read each before implementing its component;
  it is the authoritative visual reference for that component.
- *None.* Record the rationale and continue.

If the section is absent, the plan predates the convention. Continue; do not create it.

When `modules.design_sync` is `true` in `$REPO_ROOT/.agents/config.json`, also run
`"$BIN/design-sync-check"`. Exit 0 is silent; exit 1 (drift) and exit 2 (no marker) print the
helper's output as a soft warning. Neither blocks.

### 6. Summary file: create or reconcile

`$SUMMARY_FILE` is the plan's sibling `-summary.md`. When `_PLAN_FILE` came from an explicit
argument rather than `ctx`, the summary is that file's sibling: `${_PLAN_FILE%.md}-summary.md`.

**Create** when it does not exist:

```markdown
# <plan title> — execution summary

- Plan: <_PLAN_FILE>
- Branch: <BRANCH>
- Started: <TIMESTAMP>
- Metadata: <plan-metadata-get output, one line>

## Steps
- [ ] Step 1 — <objective from the plan>
- [ ] Step 2 — <objective>

## Step notes

## Doc impact

## Update-docs conclusion

## Completion
```

Boxes appear only under `## Steps`. The session banner counts every `[ ]`, `[✓]`, and `[✗]`
in this file to show progress, so a box anywhere else miscounts. A finished step reads
`- [✓] Step 1 — objective (2026-09-09T14:32:00Z)`; a failed one `- [✗] ... (<utc-timestamp>) — reason`.

**Reconcile** when the file exists. Read it and compare its boxes with reality before doing
anything. Signals that the boxes are behind: the registry entry
(`"$BIN/obsidian-workflow" registry-get "$REGISTRY_KEY"`) carries a commit or pull request;
`implementation_status` is `ready-for-review` or `partially-shipped`; the plan's
`shipped_parts` records a part; the plan body says an earlier pull request merged; or steps
the summary shows open are already on the base branch:

```bash
git log "$BASE_BRANCH" --oneline -n 20
git diff "$BASE_BRANCH"...HEAD --stat
```

When any signal fires, list every step with the box you believe is right and the evidence
(file present on base, commit message, diff hunk), and ask one question in the shared format:
confirm this list, or tell me which steps are actually done. Tick the confirmed steps with a
`(reconciled <utc-date>)` note before continuing. This is what makes multi-PR plans resumable;
guessing here makes the second pull request redo or skip work.

**The next part** of a plan that ships in parts (`implementation_status` was
`partially-shipped` before step 3 ran; the `Parts:` line of the banner names it). First confirm
the last recorded part's pull request merged; its URL is the last `pr` in `shipped_parts`:

```bash
gh pr view "$LAST_PART_PR" --json state -q .state
```

Anything but `MERGED`, or no `gh`, is one question before any code: this part's commits would
otherwise land in the open pull request of the last one. Then append this part's steps under
`## Steps`, after the boxes of the parts that shipped, each objective prefixed with the part's
label (`- [ ] Step 10 — PR1b: <objective>`); earlier boxes stay as they are.

### 7. Surface assumptions

Write the `ASSUMPTIONS I'M MAKING` block from the preamble for the whole plan, and stop for
correction. Include anything the plan leaves ambiguous, every inherited constraint you intend
to rely on, and the test commands you will use from `development-commands.md`.

### 8. Step loop

For each open step, in plan order:

1. **Announce** the step number and objective.
2. **Cross-reference LESSONS.** Scan `LESSONS.md` for the step's domain. Ten seconds here
   saves a rework cycle.
3. **Read the test artifact entries for this step** and the design reference for any component
   it touches.
4. **Implement the step completely.** Follow the plan; when a better path appears, say so and
   ask before deviating on anything the reviews locked.
5. **Verify the behavior the plan specified**, not that it compiles or renders. UI work: open
   the page, confirm the interaction, the states (loading, empty, error), and the documented
   breakpoints. Backend work: hit the endpoint or run the job and read the response shape and
   the persisted result. Run the step's tests with the commands from
   `development-commands.md`. Quote the evidence.
6. **Pause and explain**: files created or modified with paths, key decisions and rationale,
   deviations from the plan and why.
7. **Update the summary**: tick the box with `<utc-timestamp>`; under `## Step notes` add a
   subsection with files, decisions, deviations, verification evidence, and any test-artifact
   gap. Under `## Doc impact`, note which doc sections this step affects per
   `_shared/docs-contract.md` (new endpoint, route, dependency, token, command). Do not edit the
   docs per step; `/update-docs` applies them once at completion. `AGENTS.md` follows the same
   rule.

If a step fails or cannot be completed: mark it `[✗]` with the error, write what you tried,
stop, and report `BLOCKED` with a suggested way around. Do not skip ahead to later steps.

Never commit during the loop. Never check a note box.

### 9. Finish: docs, full suite, summary

When the last box is ticked:

1. **Invoke `/update-docs`** (no skill tool: read `update-docs/SKILL.md` and follow it inline).
   It diffs the branch against `$BASE_BRANCH`, walks the doc map, and edits the owning docs.
   Record its conclusion verbatim under `## Update-docs conclusion`: the docs it changed, or
   "no doc impact" with the reason and trailer it gave you. `/review-implementation` blocks on
   stale docs, so a skipped or hand-waved update surfaces immediately.
2. **Run the full test suites** exactly as `development-commands.md` says. Paste the pass and
   fail counts into `## Completion`. A red suite is `BLOCKED`, not `DONE`.
3. **Complete the summary**: completion `<utc-timestamp>`, what was built in a few sentences, test
   results, test-artifact gaps, and every deviation from the plan.
4. If the user corrected you at any point, add a Corrections Log row and the canonical rule to
   `LESSONS.md`. First-principles insights go under `## Decisions`.

## Completion

Report one status per the completion protocol, with the change description.

- **DONE** and **DONE_WITH_CONCERNS**: run the sync block from `_shared/obsidian-sync.md` with
  the `execute-plan, done` row (`STATUS_VALUE=ready-for-review`); add `--set reason="..."
  --set reason_by=execute-plan` for concerns. Write the same status line into `## Completion` of the summary.
- **BLOCKED** and **NEEDS_CONTEXT**: set `implementation_status` and `reason` only, per the
  protocol's table. The summary keeps its open boxes.
- **ABANDONED**: `"$BIN/obsidian-workflow" abandon "$REGISTRY_KEY" --reason "..."`.

If the sync fails, the implementation stands. Report `DONE_WITH_CONCERNS`, put the error in the
summary, and say the state did not sync.

Never `note-update --check`. Never commit. Then:

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
