---
name: plan-adversarial-review
description: >-
  Red-team pass on a plan after engineering review. Assumes the plan is smart and still wrong in
  a few expensive ways: inverts its premises, reads it as a rushed implementer, hunts silent
  failures, attacks rollout and rollback, finds bugs that escape the proposed tests, probes trust
  boundaries and abuse cases, and asks what the team will regret in three months. Fixes the plan
  and the test artifact in place instead of writing a critique. Prefer running it in a different
  model family or harness from the one that ran eng review. Use when asked for an "adversarial
  review", "hostile review", "red-team the plan", "stress-test the plan", or when the plan
  carries risk tags (auth, infra, data, payments, security, migration).
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# Plan Adversarial Review

The hostile follow-up to `/plan-eng-review`. Produces a plan that is harder to misimplement,
harder to break silently, easier to test, and easier to roll back: the plan file edited in place,
the test artifact hardened in place, a provenance section recording which harness and model did
the attacking, and a review-log entry. It never writes code and never starts execution work.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/plan-discovery.md`
- `_shared/obsidian-sync.md`
- `_shared/plan-footer.md`
- `_shared/dashboard.md`

## Use when

- The plan's `risk_tags` is non-empty (`auth`, `infra`, `data`, `payments`, `security`,
  `migration`). That is what puts this review on the dashboard; say so when you start.
- The user asks for an adversarial, hostile, or red-team review of a plan.
- Eng review has already run. This review builds on it; it does not replace it.
- The plan is an epic. The attack surface is the sequencing and the rollback story between
  milestones, not any single milestone's internals.

## Do not use when

- Eng review has not run. Warn and ask one question whether to proceed anyway; the usual
  answer is to run `/plan-eng-review` first.
- You are being asked to implement. This skill edits the plan and the test artifact only.
- The question is scope or strategy. That is `/plan-ceo-review`.

## Procedure

### 1. Ground and resolve the plan

Follow the preamble, then plan discovery, then read the plan's metadata. A path the user
supplies is authoritative, in any form; if the user corrects the path mid-review, drop the
previous `_PLAN_FILE` immediately and use the corrected one for every later read, edit, and log.

From the metadata note `plan_kind`, `risk_tags`, `parent_epic`, and `milestone`.

- `risk_tags` empty: say in one line that this review is optional for this plan, then continue
  if the user asked for it.
- `plan_kind` is `epic`: read the epic and its milestone progress. Every pass below applies to
  the seams between milestones: what ships first, what a half-finished sequence looks like in
  production, and whether each milestone can be reverted without the ones after it.

```bash
"$BIN/obsidian-workflow" epic-get --slug "$EPIC_SLUG"
"$BIN/workflow-state" --epics
```

- `parent_epic` set: read the parent's milestone section. The child's "Inherited constraints"
  are the contract. Attack whether the child actually honors them; do not relitigate them.

### 2. Check the eng review's provenance

Prefer a different model family or harness from the one that ran eng review. A second pass by
the same model in the same harness tends to find the same things.

```bash
"$BIN/review-read" --json | python3 -c '
import json, sys
e = (json.load(sys.stdin).get("reviews") or {}).get("plan-eng-review") or {}
d = e.get("disposition", "none")
h, m = (e.get("harness", "unknown"), e.get("model", "unknown")) if d != "resolved" else ("unknown", "unknown")
print("eng_status=%s eng_disposition=%s eng_harness=%s eng_model=%s" % (e.get("status", "none"), d, h, m))'
echo "this_harness=$HARNESS"
```

- `eng_status=none`: eng review has not been logged against this plan file. Warn and ask one
  question whether to proceed.
- `eng_harness` equals `$HARNESS` and `eng_model` equals the model you are: warn in one line
  ("same harness and model as eng review; a different family would find more") and continue.
- `eng_disposition=resolved`: the latest eng entry is a resolution record, not a run, so its
  provenance is unknown; treat it as a different family and continue.
- Keep all four values. They go into the provenance section in step 10.

Then list every earlier review with its disposition:

```bash
"$BIN/review-read"
```

For every earlier review whose disposition is `failed` or `stale`, read its open items and
decide as you go: if this review closes a failed one, say where in the plan you closed it and
note it for completion; a stale one (a later review declared it must run again) you cannot
close for them, so run it again if it is yours and carry it forward if it is not; if a failed
one stays open, carry it forward in your own summary so the next review sees it. Never leave a
failed or stale review unmentioned.

Then audit the declarations before yours: for each earlier gating review on this plan whose
latest run declared `none` (its `review-read` row shows `rereview=[]`), read the breadcrumbs it
left in the plan against the domains of the reviews that ran before it (the test in
`_shared/dashboard.md` → "When your review changes what an earlier review approved"); an
undeclared reversal you find is yours to declare: pass `--rereview <the review it overtook>
--rereview-note "…"` at completion, naming the review that made the change, and add it to that
review's REVIEW REPORT row.

### 3. Locate the test artifact by its exact path

```bash
[ -f "$TEST_ARTIFACT" ] && echo "Test artifact: $TEST_ARTIFACT" || echo "Test artifact: none at $TEST_ARTIFACT"
```

Read that exact path. The testing directory may be ignored by version control or by the
harness's search index, so a search tool returning nothing does not prove the artifact is
absent; only the direct read does. If the file is missing at that path, ask the user for it. A
user-supplied artifact path is authoritative under the same rule as the plan path.

### 4. Required reads

- `$_PLAN_FILE` in full, including any `## REVIEW REPORT`, `## Open Questions`,
  `## Failure Modes`, `## Rollout`, `## Deployment`, `## Rollback`, `## NOT in scope`, and
  `## What already exists` sections.
- `plan-eng-review/SKILL.md` and every file under `plan-eng-review/references/` (sibling
  directory of this skill). That is the baseline rubric. Do not mechanically repeat it; your job
  is to find what a strong eng review still misses.
- `$DOCS_DIR/REVIEW_CHECKLIST.md`: the project's concrete checks for each category in step 6.
- `$DOCS_DIR/PRD.md`, `APP_FLOW.md`, `TECH_STACK.md`, `FRONTEND_GUIDELINES.md`,
  `FRONTEND_STRUCTURE.md`, `BACKEND_STRUCTURE.md`, `IMPLEMENTATION_PLAN.md`, `LESSONS.md`.
- `$TEST_ARTIFACT`, when present.

### 5. Frame the attack

Read `references/passes.md` now. Answer its framing questions privately before touching the
plan: where you would attack first, which assumption is doing the most work, what a tired
engineer misreads on a Friday evening, what breaks under mixed versions, and what passes review
yet still hurts a user. Those answers drive the passes.

### 6. Inherited coverage, applied hostile

Every check from the eng review's architecture and code-quality sections is minimum coverage
here. The adversarial posture adds pressure; it does not drop checks. For each category, read
the matching entries in `REVIEW_CHECKLIST.md` and ask how it fails under mixed versions, stale
state, partial rollout, retries, or operator error, then how a rushed implementer taking the
narrowest defensible path would leave it brittle.

| Category | Hostile question |
|---|---|
| Component boundaries and coupling | Which boundary leaks first when one side is redeployed alone? |
| Data flow and bottlenecks | Where does partial, stale, or duplicated data enter, and who notices? |
| Single points of failure | What is the one thing that, when it is slow rather than down, takes the feature with it? |
| Security architecture (auth, data access, API boundaries) | Which check is assumed by the caller and never re-done by the callee? |
| Migration safety | Can old code run against the new schema, and new code against the old, for the whole rollout? |
| Background-job idempotency | What happens to an in-flight job with the old payload shape, and to a duplicate delivery? |
| Query and render efficiency | Which loop becomes an N-plus-one when the list is a thousand long instead of ten? |
| Module structure and DRY | Which two places must change together and are not marked as such? |
| Error handling | Which "handle errors" sentence has no stated user-visible behavior? |
| Diagrams | Which existing diagram in a touched file becomes a lie after this change? |

Fix obvious gaps inline. If the fix changes product behavior or scope, ask the user. If the
plan lacks enough detail for two competent engineers to build the same thing, that is a gap;
add the detail directly.

### 7. Run the seven passes, in order

The full checklist for each pass is in `references/passes.md`. Each pass ends in edits, not
notes.

| Pass | Posture | Leaves behind |
|---|---|---|
| 1 Premise inversion | Invert the three to five load-bearing assumptions | Handling for each inverted premise, in the smallest correct place |
| 2 Hostile implementer | Read as someone taking the narrowest defensible interpretation | Ambiguous nouns and vague directives replaced with stated behavior |
| 3 Silent-failure hunt | Ask how each flow fails without a crash | Explicit failure handling, user-visible behavior, observability, tests |
| 4 Rollout and reversal | Treat deploy and rollback as hostile environments | A concrete rollback sequence; flags where reversibility is poor |
| 5 Test escape | Assume a bug is trying to slip past the proposed tests | The missing tests, in the plan and in the test artifact |
| 6 Trust boundary and abuse | The feature works for good users; make it work under messy input | Only the fixes that materially reduce risk |
| 7 Future regret | What will the team hate in three months? | A smaller shape if overbuilt; operational detail if underbuilt |

On an epic, pass 4 is the center of gravity: for each milestone boundary, write down what is
live, what is half-live, and the exact reversal order. On an epic child, passes 1 and 4 must
also test the inherited constraints, not only the child's own text.

Ask the user only when a finding carries a real decision with meaningful tradeoffs, one
decision per question in the shared format. Everything else is fixed directly.

### 8. Editing rules

1. Fix the relevant section inline. Leave a short breadcrumb next to each change, for example
   `Adversarial review: rollback sequence added`.
2. When a finding changes plan-wide understanding, update the core sections it touches too:
   `## Constraints`, `## Premises`, `## Success Criteria`, `## Open Questions`,
   `## NOT in scope`, `## What already exists`, test sections, rollout and rollback sections.
3. When no section exists to hold a fix, add the smallest reasonable new one.
4. Preserve readability. Do not spray notes everywhere.
5. Preserve every frontmatter key. Never check a task box.

### 9. Harden the test artifact

When a pass changes test expectations and `$TEST_ARTIFACT` exists, edit it under the merge
discipline in `references/test-artifact-merge.md`: read it in full first, make surgical edits,
never collapse a numbered critical path into a summary bullet. Keep it a QA contract (pages,
interactions, edge cases, critical paths), not an implementation dump. Mark additions with a one-
line note naming this skill, `$HARNESS`, and your model.

### 10. Write the provenance section

Add or update `## Adversarial Review Summary` at the end of the plan using the template in
`references/provenance.md`. Harness and model are fields inside the section, never part of the
heading. It records what changed and what remains; it is not a substitute for fixing the plan.

### 11. Fold decisions and update the footer

Every user decision goes into the plan in place per the plan-footer block. Then update the
`Adversarial Review` row of the plan's review table with a status and a one-line findings
summary, keeping the table's structure intact for downstream skills.

### 12. Deferred concerns and lessons

For each remaining concern the user chose not to fix now, ask one question whether to record it
in `$DOCS_DIR/TODOS.md` in that file's own format. Never batch, never skip silently. Any
first-principles insight from the passes goes to `$DOCS_DIR/LESSONS.md` under `## Decisions`.

## Completion

Report exactly one status from the completion protocol, with the change description. Then:

```text
OPEN ADVERSARIAL CONCERNS:
- [severity] [concern]        (or: none)
```

On `DONE` or `DONE_WITH_CONCERNS`, run the obsidian-sync block with `STATUS_VALUE` and
`REVIEW_VALUE` both `adversarial-reviewed`. On `BLOCKED` or `NEEDS_CONTEXT`, set only
`implementation_status` and `reason`.

Then declare and persist the result, with counts.

Before logging, from this session's `review-read` output, for each earlier gating review that
has a run on this plan, answer whether this review changed what that review approved (the test
in `_shared/dashboard.md` → "When your review changes what an earlier review approved"). Pass
`--rereview <skill> --rereview-note "<what changed>"` for each yes, and `--rereview none` only
when every answer is no; `review-log` refuses the entry without one or the other. A demand
adds `· re-review demanded by …` to that review's REVIEW REPORT row.

```bash
"$BIN/review-log" --skill plan-adversarial-review --status "$STATUS" --plan "$(basename "$_PLAN_FILE")" \
  --rereview none \
  --field mode=RED_TEAM --field passes=7 \
  --field fixed=N --field remaining=N --field model=<your model>
```

`STATUS` is `clean` when every finding was folded into the plan or recorded there as a decided,
accepted limitation (`fixed=N` and `remaining=N` carry the detail); otherwise `issues_open`. The
words are defined once in `_shared/obsidian-sync.md` → Review log. Then, per `_shared/dashboard.md` → "When the next step names a review that ran with issues
open", log one `resolved` entry for each earlier failed review this review closed, **after**
your own entry above (the resolver's latest entry must be passed and not earlier than the
failure).

Then:

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```

Present both per the dashboard block. If the passes materially changed architecture, state
handling, or rollout assumptions, say so in one line so the user can decide whether eng review
should look again; do not list next steps yourself.
