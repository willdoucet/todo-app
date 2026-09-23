# Skill authoring conventions

Every skill in this directory follows these rules. A framework test enforces the mechanical ones.

## Frontmatter

Agent Skills standard. Nothing harness-specific.

```yaml
---
name: quickfix                         # must equal the directory name; lowercase, digits, hyphens
description: >-                        # at most 1024 characters; include the trigger phrases
  ...
disable-model-invocation: true         # only on manual-only skills
metadata:
  version: "1.0.0"
  tier: quickfix | feature | epic | utility | module
---
```

No `allowed-tools`, no top-level `version`, no tool names in the description.

`disable-model-invocation: true` on every skill that writes code, edits plans, commits, or
changes registry state. That is all of them except `update-docs`, which other skills invoke and
so must stay model-invocable.

## Body

1. `# Title` and one paragraph on what the skill produces.
2. `## Read first`: the `_shared` blocks this skill uses, by path. Always `preamble.md`,
   `question-format.md`, `completion-protocol.md`, `tool-map.md`; plus whichever apply.
3. `## Use when` and `## Do not use when`.
4. `## Procedure`: numbered steps. Shell in fenced blocks using `$BIN`, `$_PLAN_FILE`, and the
   `ctx` exports. Canonical tool verbs only (read, edit, shell, ask the user, subagent, web
   search, invoke skill).
5. `## Completion`: what to write, which status values, then the dashboard and next step.
6. Long rubrics, checklists, and templates go in `references/` and are loaded when reached.

## Hard limits

- SKILL.md at most 500 lines. Move detail to `references/`.
- Never copy a `_shared` block. A heading that matches one of them fails the test.
- Never hardcode a project name, vault name, directory such as `backend/`, a framework such as
  FastAPI or React, a test command, a base branch, or a harness tool name. Stack specifics come
  from `$DOCS_DIR/REVIEW_CHECKLIST.md`, `$DOCS_DIR/development-commands.md`, and `AGENTS.md`.
- Never edit plan frontmatter, registry files, or notes by hand. Use `$BIN/obsidian-workflow`.
- Never compute the next step in prose. Run `$BIN/workflow-state --next`.
- No bare positional (`$` then a digit) anywhere in a skill, a reference, a `_shared` block or
  `WORKFLOW.md`. A harness that passes invocation arguments into the skill body (Claude Code
  does) replaces each one with a word the user typed before the agent reads the snippet, and
  the rewritten `awk` still runs. Write `$(1)` in `awk`; the test fails on the bare form.
- No optional flag through `${VAR:+--flag "$VAR"}` in a skill, a reference, a `_shared` block
  or `WORKFLOW.md`. Bash word-splits it into the flag and the value; zsh (macOS's default
  shell, and the one an agent's shell tool runs there) passes it as one argument, which the
  helper refuses as a stray positional. Build an array in the same block and pass it quoted:
  `ARGS=(); [ -n "$X" ] && ARGS+=(--flag "$X"); cmd "${ARGS[@]}"`. The lint fails on
  `${VAR:+-` and `${VAR+-`, and every block that passes an array is run under both shells.
- Every `review-log` and `review-read` call names the plan it is about, with
  `--plan "$(basename "$_PLAN_FILE")"` (`review-read --all` takes none). Left out, both follow
  the branch's current plan, which is not the file a skill was handed by path.
- Mutating skills refuse to run on the base branch.
- Every question is one decision, in the shared format.
