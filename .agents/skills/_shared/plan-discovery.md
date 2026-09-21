# Plan discovery

Run after the preamble in every skill that operates on a plan.

```bash
eval "$("$(git rev-parse --show-toplevel)/.agents/bin/ctx")"
BIN="$REPO_ROOT/.agents/bin"

# Resolution order: explicit argument > registry > newest plan on this branch > the epic whose branch this is.
_RESOLVED=$("$BIN/obsidian-workflow" resolve-plan ${PLAN_ARG:+--plan-path "$PLAN_ARG"} ${NOTE_REF:+--note-ref "$NOTE_REF"})
_PLAN_FILE=$(printf '%s' "$_RESOLVED" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("plan_path",""))')
_PLAN_KIND=$(printf '%s' "$_RESOLVED" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("kind",""))')
echo "Plan file: ${_PLAN_FILE:-none} (kind: ${_PLAN_KIND:-unknown})"
```

Rules:

- If no plan resolves, stop and ask the user for the path. Never invent a filename.
- `_PLAN_KIND` is what the plan is, `feature` or `epic`: its frontmatter `plan_kind`, else where
  the file lives, the rule `workflow-state` reads it with. It is the answer wherever a skill
  asks whether `plan_kind` is `epic`: a file under the epics folder whose frontmatter has no
  `plan_kind` is still an epic, and on an epic's own branch the epic is what resolves.
- `resolve-plan` never returns a summary file. If you somehow hold a `-summary.md` path, use the
  sibling without the suffix.
- Read the plan in full before doing anything else.
- The base branch is `$BASE_BRANCH` from `ctx`. Use it in every `git diff`, `git log`, and
  `gh pr` command. Do not fall back to `main` or `master` by assumption.
- Store `_PLAN_FILE` and use it for every subsequent read and edit. Edit that file in place.
  Never create a sibling with a suffix such as `-reviewed`.

## Metadata

Immediately after resolving the plan, read its frontmatter. This is unconditional; you cannot
notice a flag without running the command.

```bash
"$BIN/obsidian-workflow" plan-metadata-get "$_PLAN_FILE"
```

Capture from the output: `plan_kind`, `plan_mode`, `registry_key`, `source_note_path`,
`source_note_ref`, `source_task_id`, `source_tasks`, `parent_epic`, `milestone`, `ui_scope`,
`risk_tags`, `implementation_status`, `review_status`. Preserve every key when you edit the plan.

If `_PLAN_KIND` (or the frontmatter `plan_kind`) is `epic`, the only skills that may run against
it are office-hours (milestone intake) and the plan reviews. Execute-plan, quickfix, and ship
refuse an epic file.

## Epic children

When `parent_epic` is set, read the parent's milestone section for context:

```bash
"$BIN/obsidian-workflow" epic-get --slug "$PARENT_EPIC"
```

Do not relitigate decisions the epic locked. The child's "Inherited constraints" section is the
contract; if the child needs to break one, stop and ask.
