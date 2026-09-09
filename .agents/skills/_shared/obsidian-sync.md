# Obsidian and registry sync

Every plan-bound skill updates state at its end through the helper. Never edit frontmatter,
registry files, or note files by hand. The block below is parameterized by `STATUS_VALUE` and
`REVIEW_VALUE`; each skill supplies its own:

| Skill | `STATUS_VALUE` (workflow_status) | `REVIEW_VALUE` (appended to review_status) |
|---|---|---|
| office-hours | `plan-approved` | none |
| plan-ceo-review | `ceo-reviewed` | `ceo-reviewed` |
| plan-eng-review | `eng-reviewed` | `eng-reviewed` |
| plan-adversarial-review | `adversarial-reviewed` | `adversarial-reviewed` |
| plan-design-review | `design-reviewed` | `design-reviewed` |
| execute-plan, start | `implementing` (+ `implementation_status=implementing`) | none |
| execute-plan, done | `ready-for-review` (+ `implementation_status=ready-for-review`) | none |
| review-implementation | unchanged | `impl-reviewed` |
| qa | unchanged | `qa-done` |
| design-review | unchanged | `design-audited` |
| final-review | unchanged | `final-reviewed` |
| ship | `shipped` (+ `implementation_status=shipped`, `completed=<date>`) | none |

```bash
"$BIN/obsidian-workflow" plan-metadata-set "$_PLAN_FILE" \
  --set workflow_status=STATUS_VALUE \
  --append review_status=REVIEW_VALUE          # omit when REVIEW_VALUE is none

"$BIN/obsidian-workflow" registry-upsert "$REGISTRY_KEY" \
  --set plan_path="$_PLAN_FILE" \
  --set workflow_status=STATUS_VALUE \
  --append review_status=REVIEW_VALUE          # omit when REVIEW_VALUE is none

# Note-sourced plans only: scrub stale managed lines from the note. Never checks a box.
case "$PLAN_MODE" in
  batch-note)  "$BIN/obsidian-workflow" note-update "$SOURCE_NOTE_PATH" --task-ids-json "$SOURCE_TASKS_JSON" ;;
  single-task) "$BIN/obsidian-workflow" note-update "$SOURCE_NOTE_REF" ;;
esac
```

`$REGISTRY_KEY` comes from the plan's frontmatter. `$SOURCE_TASKS_JSON` is the `source_tasks`
value verbatim; the helper accepts objects or plain ids.

Rules:

- Only `/ship` and `/quickfix` check task boxes (`note-update --check`). No review does.
- On `DONE_WITH_CONCERNS`, run the same update and add `--set reason="..."`.
- On `BLOCKED` or `NEEDS_CONTEXT`, set `implementation_status` and `reason` only. Do not mark
  progress as reviewed.
- Batch plans sync every promoted task together. Completion is all or nothing.
- If the sync fails, do not discard your work. Report `DONE_WITH_CONCERNS` and say the state did
  not sync.

## Review log

After the completion summary, persist the result. The helper fills in timestamp, branch, plan
filename, commit, and harness:

```bash
"$BIN/review-log" --skill SKILL_NAME --status STATUS --field key=value ...
```

`STATUS` is `clean` when there are no unresolved decisions and no critical gaps, otherwise
`issues_open`. Skills that fix in place (`qa`, `design-review`, `plan-adversarial-review`) log
`issues_found` with a count. Add `--field model=<name>` when you know which model you are.
