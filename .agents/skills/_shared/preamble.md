# Preamble

Read this before any skill procedure. It is short on purpose.

## Ground the session

```bash
eval "$("$(git rev-parse --show-toplevel)/.agents/bin/ctx")"
BIN="$REPO_ROOT/.agents/bin"
"$BIN/workflow-state"
```

`ctx` exports `REPO_ROOT`, `PROJECT`, `BRANCH`, `SAFE_BRANCH`, `BASE_BRANCH`, `ON_BASE`,
`DOCS_DIR`, `PLANS_DIR`, `STATE_DIR`, `VAULT_DIR`, `PLAN_DIR`, `PLAN_FILE`, `SUMMARY_FILE`,
`TEST_ARTIFACT`, `HARNESS`, `TIMESTAMP`. Use these everywhere. Never re-derive them with inline
shell, and never use a branch or path remembered from conversation history.

Every date or time you write is UTC and comes from a command, never from what you believe
the date is: `date -u +%F` for a date, `date -u +%FT%TZ` for a date-time, or `ctx`'s
`TIMESTAMP` for a filename slug. Skills and references name two slots for these:
`<utc-date>` is the output of `date -u +%F`; `<utc-timestamp>` is the output of
`date -u +%FT%TZ`. Dates already written in records and filenames are never rewritten.

Then read, in this order:

1. `AGENTS.md` at the repo root.
2. `$DOCS_DIR/LESSONS.md`. Not optional. Cross-reference every step you take against it and add
   to it when you learn something.
3. `$DOCS_DIR/REVIEW_CHECKLIST.md` if the skill reviews or writes code.
4. Any other docs the skill names.

## Ethos in brief

Full text in `_shared/ethos.md`.

- **Boil the lake.** Completeness is near free. Recommend the complete option over the shortcut.
  Score every option `Completeness: X/10` where 10 is all edge cases, 7 is the happy path, 3 is a
  shortcut that defers real work. Show effort on both scales: `(human: ~X / AI-assisted: ~Y)`.
- **Search before building.** Tried-and-true, new-and-popular, first principles. Search, then
  build the complete version of the right thing. Record first-principles insights in
  `LESSONS.md` under Decisions.
- **See something, say something.** Flag anything that looks wrong in one sentence: what you
  noticed and its impact.

## Assumptions

Before anything non-trivial, state your assumptions and stop for correction:

```
ASSUMPTIONS I'M MAKING:
1. ...
2. ...
→ Correct me now or I'll proceed with these.
```

When you see an inconsistency or an ambiguous requirement, stop, name it, and ask. Do not pick
an interpretation and hope.

## Verification and scope

Never mark anything complete without proving it works: run the commands, read the output,
exercise the behavior. Touch only what the task asks for. Do not remove comments you do not
understand, clean up orthogonal code, or delete things that seem unused without asking.

## Mutating skills and the base branch

Skills that write code or commit (`/execute-plan`, `/quickfix`, `/ship`, `/qa`,
`/design-review`, `/review-implementation`, `/final-review`) refuse to run when `ON_BASE=1`.
Offer to create a branch instead. Naming: `<task-id>` for note-sourced work, `quickfix/<slug>`
for quickfixes, the milestone's branch name for epic children.
