---
name: update-docs
description: >-
  Keeps the documentation set current with the code. Default mode diffs the branch against the
  base branch plus the working tree, maps every changed path to its owning doc section through
  the doc map, and edits those sections surgically: factual drift (endpoints, tables, columns,
  routes, components, dependencies, env vars, commands, phase and milestone status) is applied
  without asking; narrative rewrites, PRD scope changes, removals, and contradictions stop for
  one question each. --full audits every doc against the whole tree. Never regenerates a doc,
  never commits; ends with a doc sync report and a DOC IMPACT line that callers turn into the
  Docs: trailer. Called by /execute-plan, /quickfix, and /ship, and standalone. Use when asked
  to "update docs", "update the docs", "sync docs", "sync the documentation", "docs are
  stale", "doc sync", "audit the docs", or "full doc audit".
metadata:
  version: "1.0.0"
  tier: utility
---

# Update docs

Reconciles the documentation set in `$DOCS_DIR` with what the code now does. Produces edited
doc sections, an updated `AGENTS.md` when commands or structure changed, a doc map that covers
every top-level directory, a staged index the doc guard has already checked, and a doc sync
report whose last line is the `DOC IMPACT` verdict other skills paste into commits. It edits;
it never regenerates, and it never commits.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/docs-contract.md`
- `_shared/dashboard.md`

References in this directory, loaded when the procedure reaches them:
`references/change-classification.md`, `references/doc-checks.md`,
`references/report-format.md`.

## Use when

- `/execute-plan` ticked its last step, or `/quickfix` and `/ship` are about to commit.
- Code changed outside a skill and the doc guard, `/review-implementation`, or the user says
  the docs are stale.
- `--full`: a project was just adopted through `/init-project`, or drift is suspected across
  the whole doc set rather than on one branch.

## Do not use when

- The change is a narrative decision (scope, acceptance criteria, product direction) made in a
  review. `/plan-ceo-review` and `/office-hours` write those with the user's decisions in hand.
- A doc does not exist yet. `/init-project` writes the set; this skill only edits it.
- The vault or the plan file needs updating. Those belong to `obsidian-workflow`, never to
  this skill.

## Procedure

### 1. Ground and pick the mode

Follow the preamble. Read `_shared/docs-contract.md` in full: it is the ownership table this
skill enforces. Then read `$ARGUMENTS`:

| Form | Meaning |
|---|---|
| none | Default mode: reconcile the docs with this branch's diff and working tree |
| `--full` | Audit every doc against the whole tree (see "Full audit" below) |
| `--correction "<text>"` | Append one row to the Corrections Log in `LESSONS.md` |
| `--bug "<text>"` | Append one row to the Bug Log in `LESSONS.md` |
| `--decision "<text>"` | Append one entry under `## Decisions` in `LESSONS.md` |

The three `LESSONS.md` forms are repeatable and combine with either mode. A calling skill
passes them; this skill never invents one.

Load the doc map. It is the single input for ownership; do not guess owners from file names:

```bash
python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["doc_map"], indent=1))' "$REPO_ROOT/.agents/config.json"
```

Default mode on the base branch (`ON_BASE=1`) has nothing to diff against: if the working tree
is clean, print `DOC IMPACT: none - on the base branch with no changes` and go to Completion.
`--full` runs on any branch because it commits nothing; `/init-project` calls it there.

### 2. Build the change set

The review surface is everything that differs from the base branch, committed or not,
including untracked files:

```bash
cd "$REPO_ROOT"
git fetch origin "$BASE_BRANCH" --quiet 2>/dev/null || true
{ git diff "$BASE_BRANCH" --name-status; git ls-files --others --exclude-standard | awk '{print "A\t" $0}'; } | sort -u
git diff "$BASE_BRANCH" --stat
```

For every changed path, find its owner and group paths by `(doc, section)`:

```bash
"$BIN/doc-guard" --explain "$path"     # -> owner and section, "exempt", or "unmapped"
```

Deleted paths still matter: a removed route file means a removed endpoint, which the doc must
lose. Keep them in the set even though the guard ignores deletions.

Now read the diff for each group (`git diff "$BASE_BRANCH" -- <paths>`, plus the full file
for anything new) and classify it with `references/change-classification.md`: endpoints,
tables and columns, routes and pages, components, dependencies with versions, env vars,
commands and services, CI jobs. Facts only, with the file and line that proves each one.

Gather the completion signals, which decide roadmap status:

```bash
[ -n "$PLAN_FILE" ] && "$BIN/obsidian-workflow" plan-metadata-get "$PLAN_FILE"
[ -f "$SUMMARY_FILE" ] && grep -nE '^- \[' "$SUMMARY_FILE"
"$BIN/workflow-state" --history 5
```

When `parent_epic` is set in the metadata, also run
`"$BIN/obsidian-workflow" epic-get --slug "$PARENT_EPIC"` and note the milestone id, its
derived status, branch, and any pull request recorded on it. When no plan resolves (a
standalone run on a branch without one), skip the roadmap step; say so in the report.

### 3. Reconcile each owning section

For each `(doc, section)` in the change set:

1. List the doc's headings and read the section, from its heading to the next heading of the
   same or higher level:

   ```bash
   grep -n '^#' "$DOCS_DIR/$DOC"
   ```

   If the section named in the doc map does not exist in the doc, stop and ask one question:
   add the heading to the doc, or fix the map entry. Section names are how this skill and the
   staleness gate find their target; a missing one is a config bug, not a doc bug.
2. Compare the section against the facts from step 2 using the per-doc checks in
   `references/doc-checks.md`. Every fact is either already described, described wrongly, or
   missing; every described thing the diff removed is stale.
3. Decide with this gate. It is the whole point of the skill; do not soften it.

| Apply without asking | Stop and ask, one question each |
|---|---|
| Add, remove, or rename an endpoint, table, column, index, route, page, component, hook, service, job, storage key | Rewrite a paragraph of narrative, rationale, or philosophy |
| Add, remove, or bump a dependency, with its version from the manifest | Change PRD scope, a user story, acceptance criteria, business rules, or non-goals |
| Add, remove, or rename an env var, command, service, port, CI job | Remove a documented feature or flow that the diff does not clearly delete |
| Mark a phase or milestone row `implementing` or `shipped` with branch, plan link, pull request, and date | Two docs contradict each other and the diff does not settle which is right |
| Fix a cross-reference or link that points at a moved or renamed thing | Anything under `## Decisions` in `LESSONS.md` |
| Fix a table of contents that no longer matches the headings | A section the map names is missing from the doc |
| Update a file inventory or directory tree to match the directories | A change the docs describe as intentionally not done |

Ask in the shared format, one decision per question, with the recommended option first.
Never batch two docs into one question. Never proceed on a guess; a declined question is
recorded as `asked (declined)` in the report and the section is left as it was.

### 4. Editing rules

- Edit in place with the edit tool. Never write a whole doc; never regenerate a section from
  scratch when a targeted change will do. The docs are the project's memory and a rewrite
  loses what the diff did not touch.
- Match the doc's existing shape: the same table columns, the same status vocabulary, the
  same heading level. The blueprint shapes are in `references/doc-checks.md`.
- **One fact, one doc.** When a fact you are updating also appears in another doc, keep it in
  the owner from the ownership table and turn the other copy into a link to the owner. Do not
  update both.
- Dates come from `date +%F`. Roadmap rows carry the branch, the plan path relative to the
  repo, the pull request URL when one exists, and the date.
- Placeholders such as `{{...}}` left by a template are drift; fill them from the tree or, if
  there is nothing to say, replace them with one line saying why.
- Never touch plan files, the registry, the review log, or the vault. Never edit
  `## Decisions` in `LESSONS.md` without a `--decision` argument from the caller.

### 5. AGENTS.md

`AGENTS.md` at the repo root is updated when commands, project structure, dependencies, env
vars, or build and test procedures changed. It links to the docs and does not repeat them: a
new command goes into `development-commands.md` and `AGENTS.md` keeps its one-line pointer,
unless the pointer itself is now wrong. If `AGENTS.md` has a doc table and a doc was added or
renamed, fix the row.

### 6. Unmapped areas

`doc-guard --explain` prints `unmapped` for a path no rule or exempt entry covers, and the
staged dry run prints a `note: unmapped area` line per top-level directory. For each such
directory, ask one question: map it (to which doc and which existing section), or exempt it.
Then edit the config with python3, never by hand:

```bash
python3 - "$REPO_ROOT/.agents/config.json" <<'PY'
import json, sys
path = sys.argv[1]
cfg = json.load(open(path))
# One of the two lines below, with the user's answer filled in:
cfg["doc_map"]["rules"].append({"paths": ["<dir>/**"], "doc": "<DOC>.md", "section": "<Section>"})
# cfg["doc_map"]["exempt"].append("<dir>/**")
open(path, "w").write(json.dumps(cfg, indent=2) + "\n")
PY
"$BIN/doc-guard" --explain "<dir>/<any file>"
```

A mapped section must exist in its doc; if the user chose a new section, add the heading in
the same edit and describe the area there.

### 7. LESSONS rows from the caller

Only when `--correction`, `--bug`, or `--decision` was passed. Read the table header in
`$DOCS_DIR/LESSONS.md` and format the row to its columns with today's date; append it to the
end of that table. A `--decision` entry goes under `## Decisions` as a dated bullet with a link
to `$PLAN_FILE` when one resolves. Do not merge, reword, or move existing rows. Narrative
sections of `LESSONS.md` are never auto-edited; a canonical rule is the caller's to write.

### 8. Verify and stage

```bash
cd "$REPO_ROOT"
grep -rlE '\{\{[^}]+\}\}' "$DOCS_DIR" AGENTS.md 2>/dev/null || echo "no placeholders left"
git add -A
"$BIN/doc-guard" --staged --dry-run
```

Staging is not committing; the callers of this skill either commit next (`/quickfix`, `/ship`)
or leave the index staged for review (`/execute-plan`). Read the dry-run output:

- `would pass`, or `touch no documented areas`: the guard is satisfied.
- `would block without a Docs: trailer` naming a doc you did not touch: either the section
  genuinely needed nothing (say so; the caller adds `Docs: n/a - <reason>`) or you missed it.
  Re-check that doc against step 3 before deciding it is the former.
- `note: unmapped area`: go back to step 6.

Re-read every section you edited once, end to end, as a reader who has not seen the diff.

### 9. Report

Print the doc sync report from `references/report-format.md`: one row per `(doc, section)`
you visited, then the guard result, then the final line, which is exactly one of:

```
DOC IMPACT: updated <n> docs
DOC IMPACT: none - <one-line reason>
```

`<n>` counts distinct files edited under `$DOCS_DIR` plus `AGENTS.md`. The reason after
`none -` is what callers paste after `Docs: n/a - `, so keep it to one line that a reader of
the git log will understand.

## Full audit

`--full` replaces step 2 with an inventory of the whole tree and runs steps 3 through 9 for
every doc, not only the ones the diff touched.

```bash
cd "$REPO_ROOT"
"$BIN/doc-guard" --inventory
```

The inventory lists every tracked file under its owning `(doc, section)`, with the unmapped
files last; the top-level directories among the unmapped ones are what step 6 must resolve.

Then, for each doc in the ownership table, walk its sections with the full-audit column of
`references/doc-checks.md`: endpoints against the route files the map assigns to that section,
tables and columns against models and migrations, pages against the router, dependencies
against the manifests, env vars against the example env files, commands and services against
the container and CI files, file inventories against the directories, phase and milestone
status against `"$BIN/workflow-state" --history` and `--epics`, tables of contents against
headings, and every cross-reference against the file it names. The same gate applies: facts
are fixed without asking; narrative, scope, removals, and contradictions get one question
each. Docs that describe things the tree does not have are the most common finding; a
removal is always a question.

The report lists every doc, including the ones with no change, so the reader can see the audit
covered the set.

## Completion

Report one status per the completion protocol, with the change description:

- **DONE**: every visited section reconciled or explicitly declined, the guard output read,
  the report printed.
- **DONE_WITH_CONCERNS**: a question was declined leaving known drift, a mapped section is
  missing from its doc, or a doc in the ownership table does not exist. List each.
- **NEEDS_CONTEXT**: the config does not load, or the change set cannot be built (no base
  branch reachable).
- **BLOCKED**: `$DOCS_DIR` has no doc set; point at `/init-project`.

This skill never commits, never runs the registry sync block, and never writes to the vault.
The `DOC IMPACT` line is the last line of the report; callers depend on it verbatim. Then:

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
