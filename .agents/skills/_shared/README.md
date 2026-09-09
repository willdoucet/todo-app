# Shared skill blocks

Each file here is a block that used to be copy-pasted into several skills and drifted. There is
now exactly one copy. A skill's first step reads the blocks it needs; the skill body keeps only
its own procedure. A framework test fails if any SKILL.md contains one of these headings.

| Block | Read by | Purpose |
|---|---|---|
| `preamble.md` | every skill | Session grounding, ethos in brief, completeness, assumption surfacing |
| `ethos.md` | via preamble | Boil the Lake, Search Before Building, Build for Yourself |
| `question-format.md` | every interactive skill | The structured question format, with harness fallback |
| `completion-protocol.md` | every skill | DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT / ABANDONED, escalation |
| `plan-discovery.md` | every plan-bound skill | `ctx`, resolve the plan, refuse summaries and the base branch |
| `obsidian-sync.md` | plan reviews, execute-plan, ship | The metadata update block, parameterized by status |
| `plan-footer.md` | plan producers and reviewers | REVIEW REPORT table, fold decisions in place |
| `dashboard.md` | every skill | Run `workflow-state --dashboard` and `--next`; how to present them |
| `docs-contract.md` | execute-plan, quickfix, ship, update-docs, reviews | The doc set, the doc map, when to call `/update-docs` |
| `tool-map.md` | every skill | Canonical tool verbs and their names per harness |

Rules: skills reference these by path, never copy them. Edits here change every skill at once.
