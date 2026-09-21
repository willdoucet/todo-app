---
name: final-review
description: >-
  Independent second code review with fresh context, ideally in a different model family or
  harness, run after /review-implementation is clean and before /ship. Imports the whole
  review-implementation procedure as its baseline and executes every section again with its
  own judgment: scope and plan-completion audit, structural categories with the project's
  checklist, coverage diagram and gap tests, fix-first, blocking documentation staleness,
  adversarial subagent, review-log entry. Fixes in place. Never commits, never flips the plan
  to shipped, never checks a note box. Use when asked for a "final review", "second opinion",
  "second review", "fresh-eyes review", "independent review", or "shipping gate".
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# Final review

A second reviewer who has not seen the first review's reasoning. Runs the complete
`/review-implementation` procedure again on the same diff, fixes what it finds, logs
`final-review`, and hands the branch to `/ship`. Two clean reviews from two contexts are the
shipping gate; this skill is the second of them.

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
- `review-implementation/SKILL.md` in full, and every file under
  `review-implementation/references/`.

## Use when

- `/review-implementation` has logged a result for this plan and `workflow-state --next`
  names `/final-review`.
- The user wants an independent second opinion on a branch before shipping, in this or another
  harness.

## Do not use when

- `/review-implementation` has not run. Run it first; the dashboard needs both.
- On the base branch or with no diff against it.
- The user wants the plan to ship. That is `/ship`, which runs after this review is clean.

## Procedure

### 1. Ground, refuse the base branch, check independence

Follow the preamble. Refuse when `ON_BASE=1`, exactly as `/review-implementation` does.

Then resolve the plan (`_shared/plan-discovery.md`; baseline step 2 reads it in full) and read
who did the first review of that file, not of whatever plan the branch holds:

```bash
"$BIN/review-read" --plan "$(basename "$_PLAN_FILE")" --json | python3 -c 'import json,sys; e=(json.load(sys.stdin).get("reviews") or {}).get("review-implementation") or {}; d=e.get("disposition",""); h,m=(e.get("harness","not logged"),e.get("model","unknown")) if d!="resolved" else ("unknown","unknown"); print("first review:", h, m, e.get("status",""), d)'
echo "this review: $HARNESS"
```

Compare the entry's `harness` with `$HARNESS` from `ctx` and its `model` with the model you
are running as (say which you are; if you cannot tell, treat it as unknown). If both match,
print one line and continue:

```
WARNING: same harness and model as the first review (<harness>/<model>); independence is
reduced. Continuing. A different model family or harness gives a stronger second opinion.
```

Never refuse on a match. If there is no `review-implementation` entry for this plan, print
"first review not logged for this plan; the dashboard stays NOT CLEARED until it is" and
continue.

### 2. Import the baseline

Read `review-implementation/SKILL.md` in full, plus its references. Every section of it is part
of this skill unless the table in step 3 overrides it. Do not skip, summarize away, or weaken
any of it. In particular, execute all of these, by their baseline step numbers:

| Baseline step | What you must do here |
|---|---|
| 1 | Base-branch refusal and diff presence; stop without logging when there is nothing to review |
| 2 | Plan resolution with the unconditional metadata read; the summary file |
| 3 | Read the documentation set, `LESSONS.md`, `REVIEW_CHECKLIST.md` |
| 4 | Full diff acquisition, every changed file read in full |
| 5 | Scope drift and plan completion audit against `$_PLAN_FILE` and `$SUMMARY_FILE` |
| 6 | Two-pass structural review with the project's concrete checks |
| 7 | Conditional design check and design-source-of-truth reconciliation |
| 8 | Coverage diagram, gap tests in the project's test pattern, regression rule |
| 9 | Fix-first: auto-fix, one question per ASK item, verification of claims |
| 10 | TODOS capture, one question per TODO |
| 11 | Documentation staleness, blocking |
| 12 | Auto-scaled adversarial subagent with the tool-map fallback |
| 13 | Review-log entry and the plan's REVIEW REPORT row |
| Completion | Summary format, registry sync, dashboard and next step |

The baseline's rules hold: read the full diff before commenting; fix first, not read-only; be
terse; only flag real problems; never commit, push, or open a pull request.

### 3. Overrides

Where the baseline names `/review-implementation` as its own identity, read `/final-review`:

| Baseline | This skill |
|---|---|
| Header `Pre-landing review: N issues ...` | `Final review: N issues ...` |
| `review-log --skill review-implementation` | `review-log --skill final-review` |
| Adversarial entry `--skill adversarial-subagent --field tier=...` | same, plus `--field pass=final` |
| Subagent resolution `resolved_by=review-implementation` | `resolved_by=final-review` (this pass's own skill; impl's pass is earlier than this subagent run, so naming it is rejected) |
| REVIEW REPORT row `Implementation Review` | row `Final Review` |
| Sync row `review-implementation` (`impl-reviewed`) | sync row `final-review` (`final-reviewed`) |

Everything else, including the blocking documentation check and the never-commit rule, applies
unchanged.

### 4. Run the baseline with fresh judgment

Do not read the first review's findings, its fix list in the summary, or its log fields until
your own pass is complete. Then compare: findings both reviews raised, findings only the first
raised (confirm they were fixed), findings only you raised. Print that comparison after the
adversarial synthesis. The point of this skill is a second set of eyes on the same surface,
not a re-read of the first report.

When the first review left `issues_open`, treat each open item as a finding to resolve now,
through the same fix-first flow, and say which of them you closed. A `resolved` disposition
means a later record cleared it; its provenance is unknown, so the independence warning above
does not apply.

### 5. Persist

```bash
"$BIN/review-log" --skill final-review --status STATUS --plan "$(basename "$_PLAN_FILE")" \
  --field issues_found=N --field critical=N --field informational=N \
  --field model=<your model, when known>
```

`STATUS` is `clean` only when nothing remains unresolved, no critical gap is open, and the
documentation check passed; otherwise `issues_open`. The words are defined once in
`_shared/obsidian-sync.md` → Review log. Skip the entry if the review stopped in baseline
step 1. If this pass closed the first review's open items, log a resolution for it after your
own entry, per `_shared/dashboard.md` → "When the next step names a review that ran with
issues open". Update the `Final Review` row of `## REVIEW REPORT` in `$_PLAN_FILE` per
`_shared/plan-footer.md`, in place, preserving the frontmatter.

A review that overrules something the plan states (a premise, a step, a success criterion, a
decision an earlier review recorded) edits that text in place with a breadcrumb naming itself,
says so in its REVIEW REPORT row, and passes the same sentence as `--field concern=` on its own
entry: a plan review cannot usefully re-run on an implementing plan, so the record is the
control. Declaring `--rereview <skill>` is optional at the ship stage and stays in its stage
(QA, the design audit, the other code review); never declare `rereview=adversarial-subagent`
from the invocation that just logged that subagent's run: a demand dated at or after a run
always reads as outstanding (`>=`), so the subagent would read stale the moment it finished.

## Completion

Report one status per the completion protocol, then:

```
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT

INDEPENDENCE: <harness>/<model> vs first review <harness>/<model> — independent | same (warned)
FINAL REVIEW: N issues (X critical, Y informational); fixed A, skipped B by user choice
AGREEMENT: F findings shared with the first review, U unique to this pass, C first-review items confirmed fixed
COVERAGE: P/Q paths tested (R%); gap tests written: [files]
DOCUMENTATION: current | STALE — run /update-docs
ADVERSARIAL: tier, N findings | skipped (small diff) | unavailable
OPEN CONCERNS: [list or none]
```

Then the change description. Then, on DONE and DONE_WITH_CONCERNS, sync per
`_shared/obsidian-sync.md` with the `final-review` row: `workflow_status` unchanged,
`--append review_status=final-reviewed`. BLOCKED and NEEDS_CONTEXT follow the protocol's
table. This review does not set `shipped` and does not check a note box; `/ship` does both.
Never commit.

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
