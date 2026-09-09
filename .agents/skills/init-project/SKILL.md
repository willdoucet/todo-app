---
name: init-project
description: >-
  Bootstrap a project that has just run `framework init`: the documentation set in the docs
  directory, a refined config.json, AGENTS.md at the repo root, and the vault README. Two modes,
  auto-detected then confirmed. New: a builder-mode discovery interview, a layer-by-layer tech
  stack decision with current versions from web search, then every doc generated from the
  templates as a blueprint of the intended system. Adopt: survey the existing code, detect the
  stack from manifests and lockfiles, draft every doc from the code, then reconcile with
  /update-docs --full. Resumable; never overwrites a doc that already has project content
  without asking; writes no application code. Use when asked to "init project", "initialize
  the project", "bootstrap the docs", "set up the framework docs", "adopt this repo", or
  "generate the starter docs".
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: utility
---

# Init project

Turns a freshly initialized framework install into a project the pipeline can run on. Produces
a filled documentation set in `$DOCS_DIR`, a refined `.agents/config.json`, `AGENTS.md` at the
repo root, and the vault README. It writes no application code: the first code lands through
`/office-hours "Phase 1"`.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/docs-contract.md`
- `_shared/dashboard.md`

## Use when

- `framework init` has run and `$DOCS_DIR` holds untouched templates or nothing.
- An existing codebase is adopting the framework and needs its docs written from the code.
- A previous run stopped partway. The skill resumes from whatever docs already have content.

## Do not use when

- The docs already describe the project and only drifted. Use `/update-docs --full`.
- You want to design one feature. Use `/office-hours`.
- `.agents/config.json` is missing. Tell the user to run `framework init` first and stop.

## Procedure

### 1. Ground and detect the mode

Follow the preamble. On a fresh project the docs it names are templates or missing; say so in
one line and continue, because this skill creates them. `$ARGUMENTS` may carry `--new` or
`--adopt` to force a mode.

```bash
[ -f "$REPO_ROOT/.agents/config.json" ] || echo "No .agents/config.json — run 'framework init' first"
cd "$REPO_ROOT"
# Application code = tracked or untracked files outside hidden dirs and root-level meta files.
git ls-files --cached --others --exclude-standard \
  | grep -vE '^(\.[^/]+/|AGENTS\.md|CLAUDE\.md|README\.md|LICENSE.*|\.gitignore|\.editorconfig)' \
  | head -20
```

No output means **new**. Anything else means **adopt**. Confirm with one question, showing the
files that decided it. Then check the base branch:

```bash
[ "$ON_BASE" = "1" ] && echo "On $BASE_BRANCH"
```

This skill writes files and never commits. When `ON_BASE=1`, ask one question: create branch
`init-project` (recommended, so the generated docs land through a reviewable pull request) or
proceed on the base branch (acceptable only for a repo with no history yet). Re-run `ctx` after
creating a branch.

### 2. Inventory what already exists

Both modes are resumable. Classify every doc before generating anything:

```bash
TPL="$REPO_ROOT/.agents/templates"
for doc in PRD APP_FLOW TECH_STACK FRONTEND_GUIDELINES FRONTEND_STRUCTURE BACKEND_STRUCTURE \
           IMPLEMENTATION_PLAN LESSONS TODOS development-commands REVIEW_CHECKLIST; do
  f="$REPO_ROOT/$DOCS_DIR/$doc.md"
  if   [ ! -f "$f" ]; then echo "$doc: missing"
  elif cmp -s "$f" "$TPL/docs/$doc.md" || grep -qE '\{\{[^}]+\}\}' "$f"; then echo "$doc: template"
  else echo "$doc: project"; fi
done
[ -f "$REPO_ROOT/AGENTS.md" ] && { cmp -s "$REPO_ROOT/AGENTS.md" "$TPL/AGENTS.md" && echo "AGENTS.md: template" || echo "AGENTS.md: project"; }
[ -f "$VAULT_DIR/README.md" ] && echo "vault README: present"
python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); print("config:", c["project_name"], c["default_branch"], c.get("layout"), c.get("modules"))' "$REPO_ROOT/.agents/config.json"
```

Placeholders are the double-brace markers the templates use; if a template header declares a
different marker, use that instead. Rules:

- `missing` and `template` docs are generated in this run.
- `project` docs are read, used as input, and left alone. If a later step would change one,
  ask one question first (keep / merge / regenerate). Never overwrite silently.
- Present the inventory as a table and say which steps below will be skipped.

### 3. Mode: new

Follow steps N1 to N7. Skip to step 4 for adopt.

#### N1. Discovery interview

Builder mode: an enthusiastic, opinionated collaborator whose job is to find the most exciting
version of the idea, then pin down exactly what v1 is. Ask one question at a time in the shared
format; a discovery question's options are the two or three answers you can infer plus a
free-text option. Read `references/interview.md` for the question bank and technique. Cover,
in order: what it is, who it is for (named personas), the core value, the "aha", must-have v1
features versus explicitly out of scope, constraints (solo, learning goals, budget, hosting
preference, mobile), scale expectations, data sensitivity and auth needs, project shape,
deployment intent, and look and feel.

Project shape: `web-split` (separate backend and frontend directories) is the only shape the
framework supports today. Say so when you reach that question; if the user needs another shape,
record it in `LESSONS.md` under Decisions and stop with `NEEDS_CONTEXT`.

Keep asking until no assumption is left. Then present the `ASSUMPTIONS I'M MAKING` block from
the preamble covering every answer you inferred rather than heard, and wait for correction.

#### N2. Tech stack decision

One question per layer, in this order: backend language and framework; ORM, database, and
migrations; background jobs; frontend framework and build tool; styling; state and data
fetching; testing per layer; containerization and command policy; CI; hosting and deploy
targets; object storage; auth approach.

For each layer, read the option archetypes in `references/stack-decision.md`, then **web
search** for the current leading candidates in each archetype and their stable versions. Never
quote a version from memory; state the search date next to every version. Present two or three
options with pros, cons, fit for this project, `Completeness: X/10`, and a `Teaches:` line when
the user declared learning goals, then `RECOMMENDATION`. The user may pick the option that
teaches more over the one that ships faster; honor it and record why under Decisions.

After the last layer, present the whole stack as one table (layer, choice, version, search
date) and ask one confirmation question.

#### N3. Config refinements

Edit `.agents/config.json` with python3, never by hand. Read `references/config-refinements.md`
for the field guide and the doc-map rule patterns, then:

```bash
python3 - "$REPO_ROOT/.agents/config.json" <<'PY'
import json, sys
path = sys.argv[1]
cfg = json.load(open(path, encoding="utf-8"))
cfg["project_name"] = "<slug>"
cfg["default_branch"] = "<branch>"
cfg["layout"] = {"backend_dir": "<backend_dir>", "frontend_dir": "<frontend_dir>"}
cfg["doc_map"]["rules"] = [ ... ]                     # paths rewritten to the chosen layout
cfg["design_watched_files"] = [ ... ]
cfg["modules"] = {"learning": False, "design_sync": False, "learning_summaries": False}
with open(path, "w", encoding="utf-8") as fh:
    json.dump(cfg, fh, indent=2, sort_keys=True, ensure_ascii=False)
    fh.write("\n")
PY
eval "$("$BIN/ctx")"                                   # config still loads
"$BIN/doc-guard" --explain "<frontend_dir>/src/pages/Example.tsx"   # one probe per rule
```

Modules are one question each: `learning` (the optional learning module), `design_sync` (only
when the project has a design tool to sync with), `learning_summaries` (only when `learning` is
on). Recommend off unless the interview surfaced a reason.

#### N4. Generate the docs

Read `references/doc-blueprints.md`. It says what each doc must contain and the quality bar:
docs are **blueprints of the intended system**, not stubs. Schema with columns and types,
endpoints with methods and payloads, pages with routes, design tokens with values, directory
layout with file names, as decided in N1 and N2. Fill every placeholder in the template at
`$REPO_ROOT/.agents/templates/docs/<DOC>.md`; if a template section has nothing to say for this
project, write one line saying why rather than deleting it.

Generate in this order, because each feeds the next: `TECH_STACK`, `PRD`, `BACKEND_STRUCTURE`,
`APP_FLOW`, `FRONTEND_GUIDELINES`, `FRONTEND_STRUCTURE`, `IMPLEMENTATION_PLAN`,
`development-commands`, `REVIEW_CHECKLIST`, `LESSONS`, `TODOS`. Fixed rules:

- `PRD` links to `TECH_STACK` and `BACKEND_STRUCTURE` instead of duplicating stack or schema.
- `IMPLEMENTATION_PLAN` has phases only, never steps. Phase 1 is "Project skeleton" (repo
  layout, containers, CI, a hello-world endpoint and page, both test harnesses) with
  `Status: not-started`; then one phase per v1 feature in the order the interview settled.
- `LESSONS` is the template's generic rules plus the Decisions recorded during N1 and N2.
- `TODOS` is empty under its format header.
- `development-commands` holds the exact commands for the chosen stack and the command policy
  (for example containers-only) if the user wants one; ask that as one question.
- `REVIEW_CHECKLIST` is assembled by concatenating one snippet per chosen technology:

```bash
ls "$REPO_ROOT/.agents/templates/checklists/"
```

Say which snippets exist for the chosen stack. For each technology without a snippet, ask one
question: draft one now (recommended) or leave a marked gap. A drafted snippet goes both into
the doc and, offered as a follow-up, into the templates directory.

For each blueprint doc (`PRD`, `APP_FLOW`, `TECH_STACK`, `FRONTEND_GUIDELINES`,
`FRONTEND_STRUCTURE`, `BACKEND_STRUCTURE`, `IMPLEMENTATION_PLAN`, `development-commands`),
present the outline of decisions it encodes as one question before writing it, write it, then
move on. `LESSONS`, `TODOS`, and `REVIEW_CHECKLIST` are mechanical and need no question beyond
the snippet gaps above.

#### N5. AGENTS.md

Generate `$REPO_ROOT/AGENTS.md` from `$REPO_ROOT/.agents/templates/AGENTS.md`. Fill: the
project overview (two sentences from the PRD), the doc table (every doc with its one-line
purpose, linked into `$DOCS_DIR`), the command policy with a link to `development-commands.md`,
the routing summary (quickfix versus office-hours versus epic, as in `WORKFLOW.md`), the
principles, the guardrails including the secrets rule (never dump an environment unfiltered,
never paste a secret value into the conversation, filter on the remote side), and the
session-start line telling every harness to run `.agents/bin/workflow-state` first. Link to the
docs; do not duplicate them.

#### N6. Vault README

```bash
[ -f "$VAULT_DIR/README.md" ] || cp "$REPO_ROOT/.agents/templates/harness/vault-README.md" "$VAULT_DIR/README.md"
```

Fill its placeholders (project name, vault path, task format) when you copied it. Leave an
existing README alone.

#### N7. Hand-off

Write no application code, even a hello-world. Tell the user the first feature is Phase 1 of
`IMPLEMENTATION_PLAN.md`, started with `/office-hours "Phase 1"`, and go to Completion.

### 4. Mode: adopt

#### A1. Survey the codebase

Read `references/codebase-survey.md`. Delegate the survey to a subagent when the harness has
one (fall back to doing it inline in a clearly separated section): directory tree, manifests
and lockfiles, entrypoints, routers or controllers, models and migrations, pages and routes,
background jobs, CI, container files, env examples, existing README and docs, test layout and
runners, scripts. The survey returns facts with file paths, not opinions.

Read any existing README, changelog, TODO or roadmap file, and any prior agent rules file in
full. They are inputs to the docs and to `AGENTS.md`.

#### A2. Short interview

Ask only what the code cannot tell you, one question at a time in the shared format: who it is
for (personas), the core value, roadmap intent (what is next, what is deferred), non-goals,
and the command policy. Use `references/interview.md`, section "Adopt". Then present the
`ASSUMPTIONS I'M MAKING` block for everything you inferred from the code and wait.

#### A3. Detect the stack and refine the config

Build the stack table from manifests, with versions from lockfiles (never from the manifest's
range and never from memory); the detection table is in `references/codebase-survey.md`. Ask
one question per uncertain layer only. Then apply the config edit from N3 with these
differences: `layout` and every `doc_map` rule must match the real tree, and anything
ambiguous (two candidate route directories, a monorepo, generated code) is one question. Probe
every rule with `doc-guard --explain` against a real file.

#### A4. Draft each doc from the code

Read `references/doc-blueprints.md`. Same order as N4. For each doc: present the outline you
derived from the survey as one question, write the doc, then present the result as one
question (approve or list corrections). Every fact carries a file path in the draft so the
user can check it; drop the paths where the blueprint says the doc links rather than lists.

`IMPLEMENTATION_PLAN` starts with `## 1. Current State` listing what exists and known gaps,
followed by phases for known upcoming work drawn from the README, TODO files, or issues, each
with a status line. `LESSONS` keeps the template's generic rules and adds anything the existing
docs or rules file already taught. `TODOS` absorbs existing TODO files in the doc's own format,
one question per item that is unclear. `REVIEW_CHECKLIST` follows the snippet rule from N4.

#### A5. Reconcile

Invoke `/update-docs --full` (or follow its `SKILL.md` inline per the tool map). It audits every
doc against the whole tree and edits in place. Apply what it finds. If it reports drift in a
doc you just wrote, that is a survey miss: fix the doc and note the class of miss in
`LESSONS.md` so the next adoption catches it.

#### A6. AGENTS.md and vault README

As N5 and N6. When a prior rules file exists, fold its command policy, principles, and
guardrails into `AGENTS.md`; ask one question before removing or shrinking the old file.

### 5. Verify

Before reporting, prove the result works:

```bash
eval "$("$BIN/ctx")" && "$BIN/workflow-state"
grep -rlE '\{\{[^}]+\}\}' "$REPO_ROOT/$DOCS_DIR" "$REPO_ROOT/AGENTS.md" || echo "no placeholders left"
"$BIN/doc-guard" --staged --dry-run
```

Read every generated doc once more end to end. Each must be consistent with the others: the
same table names in `PRD`, `BACKEND_STRUCTURE`, and `APP_FLOW`; the same versions in
`TECH_STACK` and `development-commands`; the same phases in `IMPLEMENTATION_PLAN` and the PRD
roadmap. Fix inconsistencies in place.

## Completion

Report `DONE` when every doc in the inventory is `project`, `AGENTS.md` and the vault README
exist, and the config loads. Report `DONE_WITH_CONCERNS` with the list when a checklist snippet
is a marked gap, a doc was kept at the user's request with known drift, or `/update-docs
--full` was unavailable. `NEEDS_CONTEXT` when the project shape is unsupported or the interview
could not close an assumption. Include the change description from the completion protocol,
listing every file written. Remind the user that nothing is committed. Then:

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
