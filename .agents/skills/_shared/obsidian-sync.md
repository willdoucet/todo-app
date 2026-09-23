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
| ship | `shipped` (+ `implementation_status=shipped`, `completed=<utc-date>`); `partially-shipped` for a declared part that is not the last. Written by `obsidian-workflow ship-record`, not this block | none |

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

- Only `/ship` and `/quickfix` check task boxes (`note-update --check`). No review does, and
  `/ship` does not after a partial ship: the task is the whole plan's.
- Whenever you write a `reason`, in both commands, say who is writing it: `--set reason="..."
  --set reason_by=<your skill>` (`operator` when the user dictated it). The helper stamps the
  UTC time itself (`reason_at`), and the banner prints `Reason:  /<skill> (<utc-date>): <text>` until
  someone replaces it, so a reader can tell a standing note from a stale one. New text written
  without `reason_by` clears the old author; `--set reason=` clears all three. Each command
  stamps its own write, so the registry's `reason_at` can trail the plan's by a second; the
  plan's frontmatter is the one the banner and the dashboard read. The author and the time are
  written only with their text: both commands refuse `reason_by` or `reason_at` in a call with
  no `--set reason=`, and `--append` on any of the three, and write nothing.
- On `DONE_WITH_CONCERNS`, run the same update and add `--set reason="..."`, and, if your skill
  logs a review entry, pass the same text as `--field concern="..."` on your own entry (never
  on another review's entry, such as the subagent's), so the banner shows it with your name
  until your review runs again without one.
- On `BLOCKED` or `NEEDS_CONTEXT`, set `implementation_status` and `reason` only. Do not mark
  progress as reviewed.
- Batch plans sync every promoted task together. Completion is all or nothing.
- If the sync fails, do not discard your work. Report `DONE_WITH_CONCERNS` and say the state did
  not sync.

## Review log

After the completion summary, persist the result. The helper fills in timestamp, branch,
commit, and harness. Name the plan: left out, the entry goes to the branch's current plan,
which is not the file you reviewed when the skill was given an explicit plan path:

```bash
"$BIN/review-log" --skill SKILL_NAME --status STATUS --plan "$(basename "$_PLAN_FILE")" --field key=value ...
```

Reads follow the writes: `"$BIN/review-read" --plan "$(basename "$_PLAN_FILE")"`. A bare read is the
branch's current plan, and a declaration answered from the wrong plan's empty history is wrong.

`STATUS` is one of four words, each with one meaning in every skill. `review-log` rejects any
other word; a locally edited skill that still writes an old one gets an error naming these four.

| Status | Meaning | Disposition | Written by |
|---|---|---|---|
| `clean` | Nothing the review found is left open: it found nothing, or every finding was fixed in place, recorded in the plan as a decided and accepted limitation, or deferred to TODOS.md with the user's approval. Counts (`found`, `fixed`, `deferred`, `critical_gaps_open`, …) carry the detail | passed | every review |
| `issues_open` | Something the review found is neither fixed nor decided | failed | every review |
| `resolved` | A later record closing a failed review's open items; see `_shared/dashboard.md` → "When the next step names a review that ran with issues open" | resolved | `review-log`, on behalf of a resolver other than the review itself |
| `done` | The step completed; no findings semantics | passed | `ship` only |

A review is **ok** when its disposition is `passed` or `resolved`. Never `fixed`, `skipped`,
`pass`, `cleared`, or `issues_found`. A passed or resolved review reads `stale` when a later
review of the same stage declared it must run again (`--rereview <skill> --rereview-note
"…"` on the declarer's own entry; the four plan reviews must pass `--rereview`, `none` when
nothing changed); only its own run clears that, per `_shared/dashboard.md` → "When your
review changes what an earlier review approved". Add `--field model=<name>` when you know which model you
are. Entries written before this vocabulary are read through a compatibility map and never
rewritten; the REVIEW REPORT row carries the same word the entry does (`_shared/plan-footer.md`).
