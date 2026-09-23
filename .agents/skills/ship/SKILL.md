---
name: ship
description: >-
  Lands a reviewed feature branch; the only feature-tier skill that commits. Refuses the base
  branch, epics, and any plan the dashboard has not marked CLEARED TO SHIP; syncs with the
  base branch per the project's convention; runs the full test suites with no bypass; runs
  /update-docs; moves completed TODOS; makes conventional commits the doc guard has already
  passed; pushes; opens the pull request with the review dashboard, test evidence, and doc
  sync report in its body; records shipped in the plan, registry, note box, and roadmap row,
  or, for a declared part of a plan that ships in parts, partially-shipped with no box
  checked; logs the ship. Never merges, never deletes branches, never force-pushes; no version
  bump, no changelog, no external review services. Use when asked to "ship", "ship it", "land
  this", "open the PR", "create the pull request", or "push and open a PR".
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# Ship

Takes a branch that two clean code reviews have cleared and lands it: synced with the base
branch, tests green, docs current, committed in logical pieces the doc guard accepts, pushed,
and open as a pull request whose body carries the evidence. Then records the ship everywhere
the workflow reads state: plan frontmatter, registry, the note box, the roadmap row, the
review log. Merging the pull request is the human's job; this skill never merges and never
deletes a branch.

A plan may ship as more than one pull request under one plan file. Its frontmatter declares
the parts in order (`ship_parts`), and `ship-record` computes which part this pull request is.
A part that is not the last leaves the plan `partially-shipped`: no `completed` date, no note
box, the roadmap row still `implementing`, and the part's implementation and final reviews no
longer count, so the next part runs its own.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/plan-discovery.md`
- `_shared/obsidian-sync.md`
- `_shared/docs-contract.md`
- `_shared/dashboard.md`

References in this directory, loaded when the procedure reaches them:
`references/commit-plan.md`, `references/pr-body.md`, `references/learning-summary.md`.

## Use when

- `workflow-state --next` names `/ship`: `missing_to_ship` is empty (implementation and final
  review ok — passed or resolved — and no gating review of any tier is failed or stale).
- A hotfix branch must land before the second review can happen. One question, recorded.
- A previous ship was interrupted. Every step re-verifies; commits and a pull request that
  already exist are reused and updated, never duplicated.
- The next declared part of a plan that ships in parts is implemented and reviewed.

## Do not use when

- The work is a quickfix. `/quickfix` commits, pushes, and opens its own pull request.
- The file is an epic. Epics never ship; their milestones do.
- The plan is already `shipped`. Merge the pull request, or supersede the plan through
  `/office-hours`.
- The plan is `partially-shipped`. That part is recorded: merge its pull request, then
  `/execute-plan` continues with the next part.
- The reviews have not run. Run them; the gate here is not negotiable outside a hotfix.
- The user wants the pull request merged, the branch deleted, a version bumped, or a changelog
  written. None of those happen here.

## Procedure

### 1. Ground, refuse, and check the gate

Follow the preamble. Then:

```bash
[ "$ON_BASE" = "1" ] && echo "On $BASE_BRANCH — nothing to ship from the base branch"
```

On the base branch, stop with `NEEDS_CONTEXT`: there is no branch to land. Do not create one.

Follow `_shared/plan-discovery.md` including its metadata step; `plan-metadata-get` is the
first concrete command after resolution. Capture `plan_mode`, `registry_key`,
`source_note_path`, `source_note_ref`, `source_tasks`, `parent_epic`, `milestone`,
`implementation_status`, `ship_parts`. Refuse, with `NEEDS_CONTEXT` and nothing written, when:

- no plan resolves: "No plan on this branch. Quickfixes ship through `/quickfix`."
- `plan_kind` is `epic`: "Epics never ship; ship a milestone from its own branch."
- `implementation_status` is `shipped`: "Already shipped; merge the pull request."
- `implementation_status` is `partially-shipped`: "This part is recorded; merge its pull
  request, then `/execute-plan` continues with the next part."
- `implementation_status` is `implementing`, `blocked`, or `needs-context`: the reviews
  cannot be current. Name the status and the skill that resolves it.

When `parent_epic` is set, run `epic-get` per plan-discovery and note the milestone id, title,
and branch; they go into the pull request and the roadmap row.

Now the gate. Present the dashboard verbatim and read the verdict from the JSON, never from
memory:

```bash
"$BIN/workflow-state" --dashboard
VERDICT=$("$BIN/workflow-state" --dashboard --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["verdict"])')
MISSING=$("$BIN/workflow-state" --dashboard --json | python3 -c 'import json,sys; print(", ".join(json.load(sys.stdin).get("missing_to_ship") or []) or "none")')
echo "VERDICT: $VERDICT — missing: $MISSING"
```

`CLEARED TO SHIP` means `missing_to_ship` is empty: implementation and final review are ok
(passed or resolved) against this plan file, and no gating review of any tier is failed or stale. A
review that ran with issues open appears there as `<skill> (issues open)` and clears only by a
re-run or a `resolved` entry; one a later review sent back appears as `<skill> (re-review
demanded)` and clears only by running again (`_shared/dashboard.md`). Anything else: print the missing skills
and stop with `NEEDS_CONTEXT`, unless the branch name starts with `hotfix/`. Only then ask one question:

```
RECOMMENDATION: Choose A because the missing review is the shipping gate. Completeness: 10/10
A) Stop; run <missing skills> first (human: ~2 hours / AI-assisted: ~20 minutes)
B) Ship now under the hotfix override; recorded in the pull request body and the review log.
   Completeness: 4/10
```

If the user chooses B, set `HOTFIX_OVERRIDE=1`; steps 7 and 9 read it. Keep the dashboard
text; it is pasted into the pull request body.

Then the parts. Read them from the same JSON; `ship-record` computes the same answer at step 8:

```bash
"$BIN/workflow-state" --dashboard --json | python3 -c '
import json, sys
p = json.load(sys.stdin).get("parts") or {}
if p.get("problem"):
    print("PARTS: malformed: " + p["problem"]); sys.exit(1)
if not p.get("declared"):
    print("PARTS: none declared; this pull request completes the plan")
elif not p.get("next"):
    print("PARTS: every declared part is recorded; add this one to ship_parts"); sys.exit(1)
elif p.get("final"):
    print("PARTS: " + str(p["next"]) + " is the last part; this pull request completes the plan")
else:
    print("PARTS: " + str(p["next"]) + " is a partial ship; after it: " + ", ".join(p["remaining"][1:]))'
```

A non-zero exit is `NEEDS_CONTEXT`: repair `ship_parts` with `plan-metadata-set` first. When
nothing is declared but the plan or `$SUMMARY_FILE` describes the work as more than one pull
request (a "Scope of this run" section, part labels such as PR1 and PR2, "the first pull
request"), do not assume it completes the plan. Ask one question:

```
RECOMMENDATION: Choose A because the plan ships as <n> pull requests and this is <label>;
recording it as the whole plan marks the plan and its milestone shipped. Completeness: 10/10
A) Declare the parts <labels, in order> and ship <label> as a partial ship
B) This pull request completes the plan
```

On A, declare them and read the parts again:

```bash
"$BIN/obsidian-workflow" plan-metadata-set "$_PLAN_FILE" --set ship_parts="$SHIP_PARTS_JSON"
```

`SHIP_PARTS_JSON` is a JSON list of distinct labels, such as `["PR1a","PR1b","PR2"]`; the
helper refuses anything else and writes nothing.

Then survey what will land. Execute-plan never commits, so most of the work is usually
uncommitted; that is expected:

```bash
git status --porcelain
git log --oneline "$BASE_BRANCH"..HEAD
git diff "$BASE_BRANCH" --stat | tail -1
```

A clean tree with no commits ahead of the base is nothing to ship: stop with `NEEDS_CONTEXT`.

Finally write the `ASSUMPTIONS I'M MAKING` block from the preamble and stop for correction:
the plan and branch, the part (the `PARTS:` line), the sync convention you found (step 2), the
test commands you will run (step 3), the intended commit split (step 6), and the pull request
title.

### 2. Sync with the base branch

```bash
cd "$REPO_ROOT"
git fetch origin "$BASE_BRANCH" --quiet
SYNC_REF="origin/$BASE_BRANCH"; git rev-parse --verify --quiet "$SYNC_REF" >/dev/null || SYNC_REF="$BASE_BRANCH"
git log --oneline HEAD.."$SYNC_REF" | head -20          # what the base has that this branch lacks
grep -niE 'rebase|merge' "$REPO_ROOT/AGENTS.md" || echo "AGENTS.md names no sync convention"
```

Nothing listed means the branch is current; continue. Otherwise sync the way `AGENTS.md`
says. When it says nothing, ask one question, recommending merge because it never rewrites
history:

- **Merge:** `git merge --no-edit "$SYNC_REF"`. If git refuses because of local changes,
  `git stash push -u -m "ship: pre-sync"`, merge, then `git stash pop`.
- **Rebase:** `git rebase --autostash "$SYNC_REF"`, only when the branch has never been
  pushed (`git rev-parse --verify --quiet "origin/$BRANCH"` fails). A pushed branch is merged
  instead, and you say why: rewriting pushed history needs a force-push, which this skill
  never does.

On conflicts, stop. List them (`git diff --name-only --diff-filter=U`) and ask one question:
resolve them together now, file by file with your proposed resolution shown before each
`git add`, or abort (`git merge --abort` or `git rebase --abort`) and report `BLOCKED`. After a
resolution, finish the merge or `git rebase --continue`, re-run `ctx`, and show
`git log --oneline "$BASE_BRANCH"..HEAD`. A conflict inside a stash pop is handled the same
way.

### 3. Run the full test suites

Read `$DOCS_DIR/development-commands.md` and run every suite it lists, exactly as written and
through the command policy it states: unit, integration, end to end, lint, type check,
whatever the CI parity section names. Not a subset, not "the relevant ones". Quote the pass
and fail counts and the wall time per suite; they go into the pull request body.

A failure halts the ship with `BLOCKED` and the failing output. There is no bypass, no skip
list, no re-run until green without a fix. If the failure is a real bug and the fix is small,
fix it, re-run the whole set, and record the fix in the summary and the pull request body:
the reviewed diff changed, and the reader must know. Files the suites rewrite (snapshots,
baselines) are part of the diff; read them before they are committed.

### 4. Update the docs

Invoke `/update-docs` (no skill tool: read `update-docs/SKILL.md` and follow it inline per
the tool map). Answer its questions in the shared format as they come. It stages what it
changed and proves the guard passes. Capture its whole doc sync report for the pull request
and its last line verbatim:

```
DOC IMPACT: updated <n> docs
DOC IMPACT: none - <reason>
```

Record the report under `## Update-docs conclusion` in `$SUMMARY_FILE` when that section is
still empty or the report differs from what execute-plan recorded. If `/update-docs` returns
`BLOCKED` or `NEEDS_CONTEXT`, so does this ship.

### 5. Move completed TODOS

Read `$DOCS_DIR/TODOS.md`; its header defines the format and the Completed section. For each
open item, decide whether this branch completes it. Evidence that it does: the item's title
matches the plan's intake or a milestone; the plan's REVIEW REPORT or the summary says
"addresses TODO: <title>"; the diff changes what the item's What and Context describe. When
the evidence is clear, move the item to the Completed section with `<utc-date>`, the branch, and
a pull request placeholder you fill in at step 7, keeping its original text. When it is
unclear, ask one question per item: complete it, or leave it open. Never silently skip an
item, and never move one on a title match alone.

Stage the file when it changed. It is a doc; it rides with the commits in step 6.

### 6. Commit

Read `references/commit-plan.md`. It decides the split (one commit for one logical unit, a
few when the work has independently readable layers), the message format, and the trailer
rule: when `DOC IMPACT` was `none`, every commit that touches a mapped path carries
`Docs: n/a - <reason>` with the reason from step 4; when it was `updated`, the doc changes
ride in the commit whose code they describe.

Before every commit, prove the guard would accept it, then commit without `--no-verify`:

```bash
git add <paths of this group>
"$BIN/doc-guard" --staged --dry-run
git commit -F "$MSG_FILE"
git log --oneline "$BASE_BRANCH"..HEAD
```

A `would block` result naming a doc you did not touch is one of three things, in order of
likelihood: the doc changes are staged for a later group (move them here), `DOC IMPACT` was
`none` and the trailer is missing (add it), or `/update-docs` missed the doc (go back to step
4; that is a real gap). `Docs: later` is never used here: the pull request is where "later"
comes due, and this is the pull request.

Workflow files that changed before this step (`$PLANS_DIR`, `$STATE_DIR`) go into the last
work commit; step 9 commits what step 8 changes. The merge commit from step 2, if any, stays.

### 7. Push and open the pull request

```bash
git push -u origin "$BRANCH"
```

Never `--force`, never `--force-with-lease`. Then read `references/pr-body.md` and build the
body: summary, plan and summary paths, epic and milestone, the part, the dashboard from step 1
(with the hotfix override line when used), the test evidence from step 3, the doc sync report
from step 4, the TODOS moved in step 5, deviations from the plan, and the intake source.

```bash
gh auth status >/dev/null 2>&1 && gh pr view --json url,state -q 'select(.state == "OPEN") | .url' 2>/dev/null
```

With `gh` available: create the pull request against `$BASE_BRANCH` when no open one exists,
or update the open one's body; never open a second. Only an open pull request is this one: on
the next part of a plan that ships in parts, the branch's earlier pull request is merged, and
editing it would rewrite that part's record. Without `gh`: print the compare URL
from the reference and the body for the user to paste, and carry on with that URL, reporting
`DONE_WITH_CONCERNS` at the end because the pull request was not opened by this skill. Either
way, `PR_URL` is now set. Fill it into the TODOS rows from step 5.

### 8. Record shipped

`ship-record` is the `ship` row of `_shared/obsidian-sync.md`: it writes the plan frontmatter
and the registry entry in one call, and computes the part from `ship_parts`. On a partial
ship, set `NEXT_REASON` to what the next part needs before it starts, such as the operator
steps the plan places between the pull requests, or leave it empty; without it the plan's
reason is cleared, since it described the part that just shipped.

```bash
REASON_ARGS=(); [ -n "$NEXT_REASON" ] && REASON_ARGS=(--reason "$NEXT_REASON")   # an array: bash and zsh agree
SHIP_JSON=$("$BIN/obsidian-workflow" ship-record "$_PLAN_FILE" --pr "$PR_URL" \
  --commit "$(git rev-parse --short HEAD)" "${REASON_ARGS[@]}")
echo "$SHIP_JSON"
RECORDED=; PART=; PARTIAL=
eval "$(printf '%s' "$SHIP_JSON" | python3 -c '
import json, shlex, sys
d = json.load(sys.stdin); ok = d.get("status") == "ok"
print("RECORDED=" + ("1" if ok else ""), "PART=" + shlex.quote(d.get("part") or ""), "PARTIAL=" + ("1" if ok and not d.get("final") else ""))')"
```

`RECORDED` empty means the helper refused and wrote nothing: say why, check no box, and carry
on to report `DONE_WITH_CONCERNS`. `PARTIAL=1` is a part that does not complete the plan:
the plan and registry read `partially-shipped`, and no note box is checked, because the note
task is the whole plan's.

Note-sourced plans check their boxes now, and only now: after the part that completes the
plan. Compare the source tasks with the summary's deviations first: a task the plan dropped
stays unchecked, and if a batch dropped one, ask one question before checking any (batch
completion is all or nothing by design, so a dropped task means the plan should have been
adjusted).

```bash
if [ -n "$RECORDED" ] && [ -z "$PARTIAL" ]; then
  case "$PLAN_MODE" in
    batch-note)  "$BIN/obsidian-workflow" note-update "$SOURCE_NOTE_PATH" --task-ids-json "$SOURCE_TASKS_JSON" --check ;;
    single-task) "$BIN/obsidian-workflow" note-update "$SOURCE_NOTE_REF" --check ;;
  esac
fi
```

Read the state back before claiming it; a sync you did not read is a sync you do not know
happened:

```bash
"$BIN/obsidian-workflow" registry-get "$REGISTRY_KEY"
[ -n "$SOURCE_NOTE_REF" ] && "$BIN/obsidian-workflow" parse-task "$SOURCE_NOTE_REF"
```

Then the roadmap. Invoke `/update-docs` a second time: the registry now says `shipped`, so it
marks the phase row, or the milestone row of an epic child, `shipped` with `<utc-date>`, the plan
link, and `PR_URL`, and refreshes the epic's milestone count. This is the "Ship keeps it
current" rule from the workflow; the first run could not do it because the status was not yet
shipped. After a partial ship the registry says `partially-shipped`, and the row stays
`implementing` (`in-progress` on a phase) with the part's pull request added, never
`shipped`.

On the part that completes the plan, if `modules.learning_summaries` is `true` in
`$REPO_ROOT/.agents/config.json`, write the
plain-English summary from `references/learning-summary.md` to
`$VAULT_DIR/Learning/<plan-name> - Plain English Summary.md`, where `<plan-name>` is
`$(basename "$_PLAN_FILE" .md)`. Vault files are not committed by this skill.

If any command in this step fails, keep going through the rest, then report
`DONE_WITH_CONCERNS` naming exactly which state did not sync. The code is landed either way.

### 9. Log the ship, commit the record, push again

Log first so the entry rides in the commit:

```bash
SHIP_FIELDS=(--field pr="$PR_URL")
[ -n "$PART" ] && SHIP_FIELDS+=(--field part="$PART")
[ -n "$PARTIAL" ] && SHIP_FIELDS+=(--field partial=true)
[ -n "$HOTFIX_OVERRIDE" ] && SHIP_FIELDS+=(--field hotfix_override=true --field skipped_reviews="$MISSING")
"$BIN/review-log" --skill ship --status done --plan "$(basename "$_PLAN_FILE")" "${SHIP_FIELDS[@]}"
git add -A
"$BIN/doc-guard" --staged --dry-run
git commit -m "chore(workflow): record ship $(basename "$_PLAN_FILE" .md)${PART:+ ($PART)}"
git push
```

On a partial ship this entry is what closes the part's ship stage: from it on, the plan's
implementation review, adversarial subagent, QA, design audit, and final review read as not
yet run, and the next part runs them on its own diff. Until it is logged, `workflow-state`
refuses to move on and prints this command.

This commit holds the plan frontmatter, the registry entry, the review log, the roadmap row,
and the TODOS pull request links. It touches no mapped code, so the guard passes without a
trailer; if it does not, something from step 6 was left unstaged. Find it; do not bypass.

### 10. Finish

If the user corrected you at any point, add a Corrections Log row and the canonical rule to
`$DOCS_DIR/LESSONS.md` through `/update-docs --correction "..."` and include it in a second
`chore(workflow)` commit. Then report per Completion.

## Completion

Report one status per the completion protocol, with the change description:

- **DONE**: pushed, pull request open at `PR_URL`, plan and registry `shipped` (or
  `partially-shipped` after a part that does not complete the plan), note boxes checked when
  there were any and the plan is complete, roadmap row current, ship logged.
- **DONE_WITH_CONCERNS**: landed, but the pull request was not opened by this skill, a state
  sync failed, a TODOS decision was declined, or the hotfix override was used. List each.
- **BLOCKED**: a test suite failed, or a sync conflict was aborted. The branch is left as it
  was before the failing step; say exactly where.
- **NEEDS_CONTEXT**: refused at step 1. Nothing was written.
- **ABANDONED**: the user stopped the ship. `"$BIN/obsidian-workflow" abandon "$REGISTRY_KEY"
  --reason "..."` only if they also abandoned the plan; otherwise leave the state alone.

Then the summary block:

```
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | ABANDONED
BRANCH: <branch> -> <base branch>, synced by <merge | rebase | already current>
TESTS: <suite: N passed, M failed> ...
DOCS: <DOC IMPACT line>
COMMITS: <count> (<subjects>)
PR: <PR_URL>
PART: <label> (partial; next: <label>) | <label> (completes the plan) | whole plan
RECORDED: plan, registry, note box (<n> tasks | n/a | not yet: partial), roadmap row, review log
TODOS: completed [titles] | none
CONCERNS: [list or none]
```

Never merge the pull request. Never delete the branch. Then:

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```

`--next` prints "merge the PR" for a shipped plan, and `/execute-plan` with "<part> shipped
(<url>) — merge it, then continue with <next part>" after a partial ship; present it as the last
thing you say.
