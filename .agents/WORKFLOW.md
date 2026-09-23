# Workflow

The one canonical description of how work moves through this project. Every skill's
"next step" is computed from the same state this document describes, so if this file and a
skill ever disagree, this file wins and the skill has a bug.

## Session start

Every session begins by running the status helper. Claude Code does it through a hook; the
first line of `AGENTS.md` tells every other harness to do it by hand.

```bash
.agents/bin/workflow-state          # banner: branch, plan, epic, stage, reviews, next step
.agents/bin/workflow-state --next   # just the next step
```

## Two tiers, one intake model

Where a task comes from is independent of how heavy the process is.

**Intake** is any of: an Obsidian note ref (`Notes/Ideas.md#^task-id`), an Obsidian note path
(every unchecked task in it, one batch plan), a phase or milestone name from
`IMPLEMENTATION_PLAN.md`, an epic milestone (`<epic file>#M3`), or a plain description.

**Tier** is decided by size:

| Work | Tier | Skill |
|---|---|---|
| Bug fix, copy or content change, config, small refactor, patch or minor dependency bump. Roughly three files or fewer. No schema, route, dependency, or new UI surface. | Quickfix | `/quickfix` |
| A feature, a new page, a schema or API change, a major dependency bump, a large refactor, anything that needs a design decision | Feature | `/office-hours` |
| Work that needs several features shipped in sequence | Epic | `/office-hours`, confirm epic mode |
| Production incident | Quickfix on a hotfix branch | `/quickfix` |
| An item from `TODOS.md` | Whichever fits | Reference it by title |

If a quickfix grows past the threshold, the skill escalates it to office-hours and keeps the
same task id. If a feature turns out to be small, office-hours can hand it to quickfix.

## The feature pipeline

Required steps in bold. Every skill ends by running `workflow-state --next` and presenting the
result. Nothing here is remembered by the agent; it is computed from the registry, the review
log, and the plan's frontmatter.

| Step | Skill | Runs when | Produces |
|---|---|---|---|
| Design doc | **/office-hours** | Always | Plan file with frontmatter, registry entry, branch |
| Scope review | /plan-ceo-review | Scope is in question. Required for epics. | Plan edited in place, review-log entry |
| Engineering review | **/plan-eng-review** | Always. The shipping gate. | Plan edited in place, test artifact, review-log entry |
| Adversarial review | /plan-adversarial-review | Plan has risk tags (auth, infra, data, payments). Prefer a different model family. | Plan edited in place, review-log entry |
| Design review | /plan-design-review | Plan has UI scope | Plan edited in place, mockups or prototype, review-log entry |
| Implementation | **/execute-plan** | Always | Code, summary file, docs updated via `/update-docs`. Never commits. |
| Code review | **/review-implementation** | Always. Doc staleness blocks. | Fixes in place, tests, review-log entry. Never commits. |
| Browser QA | /qa | Test artifact lists pages | QA report, fixes in place, regression tests. Never commits. |
| Live design audit | /design-review | UI scope | Graded audit, design baseline, fixes in place |
| Second opinion | **/final-review** | Always. Fresh context, prefer a different model. | Fixes in place, review-log entry |
| Ship | **/ship** | Always | Tests, `/update-docs`, commits, push, PR, registry shipped, note box checked, roadmap row |

Merging the pull request is manual.

```
intake ──► route by size
              │
   ┌──────────┴───────────┐
   ▼                      ▼
/quickfix            /office-hours
   │                      │
   │              [/plan-ceo-review]
   │                      │
   │               /plan-eng-review
   │                      │
   │          [/plan-adversarial-review]
   │                      │
   │            [/plan-design-review]
   │                      │
   │                /execute-plan ──► /update-docs
   │                      │
   │           /review-implementation
   │                      │
   │              [/qa] [/design-review]
   │                      │
   │                /final-review
   │                      │
   └──────────────► /ship ──► /update-docs, commit, push, PR
```

## Epics

An epic is a phase too big for one plan. Office-hours offers epic mode when it sees more than
one branch's worth of work or sequencing dependencies between parts. The epic file lives under
`plans/epics/<slug>/` and **never executes**. It defines milestones; each milestone is an
ordinary feature plan or a quickfix whose frontmatter names `parent_epic` and `milestone`.

Rules:

1. Every milestone, however small, is its own plan or quickfix.
2. Children reference the parent by milestone id, never by line number. Office-hours copies the
   milestone's locked decisions into the child's "Inherited constraints" section.
3. Status is derived. A milestone's status is its child's status from the registry. The epic
   ships when the last milestone ships. A milestone can be marked `subsumed` with a reason.
4. One level deep. A milestone too big for one plan becomes two milestones.
5. Epics always get CEO review.

Start a milestone from the epic:

```
/office-hours .agents/plans/epics/<slug>/<slug>-epic-<ts>.md#M3
/quickfix     .agents/plans/epics/<slug>/<slug>-epic-<ts>.md#M1
```

The phase entry in `IMPLEMENTATION_PLAN.md` carries the milestone table. Ship keeps it current.

## Backlogs

| Backlog | Role | Feeds |
|---|---|---|
| `docs/IMPLEMENTATION_PLAN.md` | Roadmap. Feature-sized phases in intended order, each with a status line and a plan link. Never step-level detail. | Pick next work here. |
| The Obsidian vault | Capture. Ideas, bugs, polish, in your own words. See the vault README for the task format. | `/quickfix` or `/office-hours` with a note ref. |
| `docs/TODOS.md` | Deferred engineering items surfaced during reviews, with enough context to resume cold. | Promoted into a phase or a quickfix when chosen. |

## State

Every plan carries frontmatter the helpers read and write. Skills set these through
`obsidian-workflow plan-metadata-set`; never edit them by hand.

| Key | Values |
|---|---|
| `plan_kind` | `feature`, `epic` |
| `plan_mode` | `single-task`, `batch-note`, `feature`, `quickfix`, `epic` |
| `implementation_status` | `not-started`, `implementing`, `ready-for-review`, `partially-shipped`, `shipped`, `blocked`, `needs-context`, `abandoned` |
| `workflow_status` | `planning`, `plan-approved`, `ceo-reviewed`, `eng-reviewed`, `adversarial-reviewed`, `design-reviewed`, `implementing`, `ready-for-review`, `partially-shipped`, `shipped`, `blocked`, `needs-context`, `abandoned`, `escalated` |
| `review_status` | list of completed reviews: `ceo-reviewed`, `eng-reviewed`, `adversarial-reviewed`, `design-reviewed`, `impl-reviewed`, `qa-done`, `design-audited`, `final-reviewed` |
| `ui_scope` | `true` when the plan changes anything a user sees |
| `ship_parts` | the pull requests a plan ships as, in order (`["PR1a", "PR1b", "PR2"]`); unset when it ships as one |
| `shipped_parts` | one record per part `/ship` landed (`part`, `pr`, `commit`, `shipped_at`), written by `obsidian-workflow ship-record` |
| `risk_tags` | list drawn from `auth`, `infra`, `data`, `payments`, `security`, `migration` |
| `parent_epic`, `milestone` | set on epic children |
| `registry_key` | the registry entry this plan belongs to |
| `supersedes` | the plan this one replaces |

Registry entries live one per file under `state/registry/entries/`. Keys: `Notes/File.md#^task-id`
and `Notes/File.md#batch` for vault-sourced work (paths relative to the vault root),
`plan:<safe-branch>` for freeform features, `quickfix:<slug>`, `epic:<slug>`.

A plan that ships in parts keeps one plan file for every part. `/ship` records each part with
`obsidian-workflow ship-record`, which computes it from `ship_parts`: a part that is not the last
leaves the plan `partially-shipped` (no `completed`, no note box, the roadmap row still
`implementing`), and `workflow-state --next` names `/execute-plan` for the next part. The last
part ships the plan as usual.

The review log is `state/review-log.jsonl`. A review is current when it was logged against the
current plan file, and, for the implementation review, adversarial subagent, QA, design audit
and final review, dated after the plan's last partial ship (the `ship` entry with
`partial: true`): each part runs its own. Plan reviews count for every part. Age is informational only. Every entry's `status` is one of `clean`,
`issues_open`, `resolved`, `done`, defined once in `skills/_shared/obsidian-sync.md` → Review
log; `review-log` refuses any other word, and `workflow-state` gates on their dispositions: a
review that ran and did not pass blocks its stage until it is re-run or resolved, while a
review that never ran is merely optional. A review that a later review sent back (`--rereview`
on the declarer's entry) reads `stale` and blocks until it runs again; see
`skills/_shared/dashboard.md` → "When your review changes what an earlier review approved".

## Artifacts at completion

| Work | Plan file | Summary | Quickfix log | Registry | Roadmap row | Note box | Commit and PR |
|---|---|---|---|---|---|---|---|
| Feature plan | yes | yes | no | yes | phase row | if from a note | yes |
| Milestone via plan | yes | yes | no | yes, with parent | milestone row | no | yes |
| Milestone via quickfix | no | no | yes | yes, with parent | milestone row | no | yes |
| Standalone quickfix | no | no | yes | yes | no | if from a note | yes |

`workflow-state --history` lists recent completions across all of them.

## Documentation

Every code area has exactly one owning doc section, declared in `config.json` under `doc_map`.

1. `/update-docs` writes. Called by execute-plan on completion, by quickfix and ship before
   committing, and standalone. `--full` audits every doc against the whole tree.
2. `/review-implementation` gates. `doc-guard --worktree` fails when a changed area on the
   branch, committed or not, has an untouched owning doc.
3. `doc-guard` backstops. A commit-msg hook and a CI job refuse commits that touch a mapped path
   without staging the owning doc. Escape with a trailer, recorded in history:

```
Docs: n/a - internal rename, no documented surface changed
Docs: later                                   # feature branches only; the PR must resolve it
```

## Harness invocation

| Harness | Invoke a skill | Rules file | Skills directory |
|---|---|---|---|
| Claude Code | `/name args` | `CLAUDE.md` imports `AGENTS.md` | `.claude/skills`, a symlink |
| Codex | `$name args` | `AGENTS.md` | `.agents/skills` natively |
| Grok Build | `/name args` | `AGENTS.md` | `.grok/skills`, a symlink |
| Cursor | `/name args` | `AGENTS.md` | `.agents/skills` natively |

Skills are written against a canonical tool vocabulary; see `skills/_shared/tool-map.md`.
All state is in the repo, so any step can run in any harness.

## Vocabulary

- **safe branch**: the branch name with `/` replaced by `-`; names the plan folder.
- **plan file**: `plans/features/<safe-branch>/<safe-branch>-plan-<YYYYMMDD-HHMMSS>.md`; the
  timestamp is UTC (`ctx`'s `TIMESTAMP`).
- **summary file**: the plan's sibling `-summary.md`, the running execution log.
- **test artifact**: `plans/testing/<safe-branch>-test-artifact.md`, written by eng review.
- **epic file**: `plans/epics/<slug>/<slug>-epic-<YYYYMMDD-HHMMSS>.md`, the timestamp in UTC.
- **quickfix log**: `plans/quickfixes/LOG.md`, one block per completed quickfix.
- **doc map**: the path-to-doc ownership table in `config.json`.
- **ready-for-review**: execute-plan finished; reviews may begin.
- **partially-shipped**: a declared part landed as its own pull request; the plan continues
  with the next part through `/execute-plan`.
- **shipped**: committed, pushed, pull request open, registry updated, note box checked.
