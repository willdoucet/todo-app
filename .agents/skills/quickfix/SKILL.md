---
name: quickfix
description: >-
  Tier-one path for small changes: bug fixes, copy and content changes, config, small
  refactors, patch or minor dependency bumps. Roughly three files or fewer, no schema, route,
  dependency, or new UI surface. Takes an Obsidian note ref, an epic milestone ref, or a plain
  description. States assumptions, reproduces bugs with a failing test first, implements,
  verifies, updates docs, commits on its own branch, pushes, opens the pull request, and records
  completion. Use when asked to "quickfix", "quick fix", "small fix", "hotfix", "just change",
  or when a task is clearly too small for a plan. Escalates to /office-hours when it grows.
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: quickfix
---

# Quickfix

One session, one branch, one small change, fully recorded. Produces a commit, a pull request, a
registry entry, a line in the quickfix log, updated docs, and a checked note box when the task
came from Obsidian.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/docs-contract.md`

## Use when

- The change is small: about three files, no schema, route, dependency, or new user-facing
  surface. Bug fixes, copy, config, a patch or minor version bump, a contained refactor.
- A production incident needs a hotfix.
- An epic milestone was sized `quickfix` by office-hours.

## Do not use when

- The task needs a design decision, touches data shape or public API, or adds a page. Use
  `/office-hours`.
- The note path has several unchecked tasks meant to ship together. That is a batch plan
  through `/office-hours`. Quickfix is single-task only.

## Procedure

### 1. Ground

Follow the preamble. Then confirm you are not on the base branch:

```bash
[ "$ON_BASE" = "1" ] && echo "On $BASE_BRANCH — a branch is required"
```

If on the base branch, ask the user (one question) to create `quickfix/<slug>` from the base
branch, or to name a branch. Create it and re-run `ctx`. Never commit to the base branch.

### 2. Intake

`$ARGUMENTS` is one of:

| Form | Example | Handling |
|---|---|---|
| Note ref | `Bugs.md#^login-redirect-loop` | Single task. `parse-task` then `ensure-task-id`. Slug is the task id. |
| Note path | `Bugs.md` | Ambiguous. `parse-task <path>` and ask which one task to take. If the user wants all of them together, stop and point at `/office-hours`. |
| Epic milestone | `.agents/plans/epics/<slug>/<file>.md#M1` | Read the milestone via `epic-get`. Slug is `<epic-slug>-m1`. Inherit its locked decisions. |
| Roadmap phase | `Phase 4.2` | Read the phase entry in `IMPLEMENTATION_PLAN.md`. Slug from its title. |
| Free text | "square the corners on primary buttons" | Slug from the text, at most five words. |

```bash
"$BIN/obsidian-workflow" parse-task "$NOTE_REF"
"$BIN/obsidian-workflow" ensure-task-id "$NOTE_REF"
```

Stop on any non-`ok` status and show the helper's message. Never reuse a reserved id.

### 3. Size gate

Before touching code, estimate: files to change, whether a schema, route, dependency, or new UI
surface is involved. If any of those is true, or more than about three files, ask one question:

```
RECOMMENDATION: Choose A because this touches <schema|route|...>, which needs a reviewed plan.
A) Escalate to /office-hours with this same task (human: ~1 day / AI-assisted: ~1 hour)
B) Proceed as a quickfix anyway
```

On escalate, if the task was registered already run `"$BIN/obsidian-workflow" escalate --slug "$SLUG"`,
then invoke `/office-hours` with the same intake argument and stop.

### 4. Register

```bash
QF_ARGS=()
[ -n "$NOTE_REF" ] && QF_ARGS+=(--note-ref "$NOTE_REF")
[ -n "$PARENT_EPIC" ] && QF_ARGS+=(--parent-epic "$PARENT_EPIC" --milestone "$MILESTONE")
"$BIN/obsidian-workflow" quickfix-register --slug "$SLUG" --title "$TITLE" --branch "$BRANCH" \
  "${QF_ARGS[@]}"
```

### 5. Read what the change touches

Identify the likely files. For each, find the owning doc and read that section:

```bash
"$BIN/doc-guard" --explain path/to/file
```

Read `$DOCS_DIR/REVIEW_CHECKLIST.md` for the technologies involved. Read the test commands in
`$DOCS_DIR/development-commands.md`.

### 6. Assumptions

Write the `ASSUMPTIONS I'M MAKING` block from the preamble and wait for correction. For a bug,
include the reproduction you expect to write.

### 7. Implement

- **Bugs first get a failing test** that reproduces the behavior. Then fix. Then the test passes.
  No fix without a regression test.
- Follow every applicable entry in `LESSONS.md`.
- Keep the diff surgical. If the change grows past the gate in step 3, stop and escalate.

### 8. Verify

Run the relevant test suites exactly as `development-commands.md` says, and exercise the behavior
itself: hit the endpoint, load the page, run the command. Quote the evidence in the summary.
"It compiles" is not verification.

### 9. Docs and lessons

Invoke `/update-docs` (or follow its SKILL.md inline per the tool map). It diffs the branch
against `$BASE_BRANCH`, walks the doc map, and edits the owning docs. Capture its conclusion:
either docs changed, or "no doc impact" with a reason.

If this was a bug, add a Bug Log row to `LESSONS.md`. If the user corrected you at any point,
add a Corrections Log row and the canonical rule.

### 10. Commit, push, pull request

```bash
git add -A
"$BIN/doc-guard" --staged --dry-run
```

Commit with a conventional message. When update-docs concluded there is no doc impact, add the
trailer it gave you:

```
fix(auth): stop redirect loop on expired refresh token

Docs: n/a - behavior fix only, documented flow unchanged
```

Push the branch. Open the pull request against `$BASE_BRANCH` with the tool available
(`gh pr create` when present; otherwise push and print the compare URL for the user). The PR
body: what and why, the test that proves it, files touched, the doc-update conclusion, and the
intake source.

### 11. Record

Append one block to `$PLANS_DIR/quickfixes/LOG.md` (create the file with a `# Quickfix log`
heading if absent):

```markdown
## 2026-09-09 — login-redirect-loop
- Source: Bugs.md#^login-redirect-loop
- What: stop the redirect loop when the refresh token has expired
- Why: users with a stale cookie bounced between /auth and / forever
- Files: frontend/src/lib/auth/session.js, frontend/src/lib/auth/session.test.js
- Tests: session.test.js::redirects once on expired refresh
- Docs: no doc impact (documented flow unchanged)
- Branch: quickfix/login-redirect-loop · PR: <url>
```

Then mark it complete. This checks the note box, moves the task to the note's Completed section,
and updates the epic milestone when there is one:

```bash
"$BIN/obsidian-workflow" quickfix-complete --slug "$SLUG" --commit "$(git rev-parse --short HEAD)" --pr "$PR_URL"
```

Commit the log and registry as `chore(workflow): record quickfix <slug>` and push again.

## Completion

Report `DONE` or `DONE_WITH_CONCERNS` with the change description from the completion protocol.
`BLOCKED` and `NEEDS_CONTEXT` leave the branch in place and set the registry status with a
reason; the note box stays unchecked. Then:

```bash
"$BIN/workflow-state" --next
```
