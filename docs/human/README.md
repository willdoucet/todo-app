# todo-app — human docs

Plain-English pages about what this project does, written for a person, committed with the
code. Open this folder as an Obsidian vault, or read it on GitHub.

| Folder | What is in it | Who writes it |
|---|---|---|
| `features/` | One page per capability: what it does now, what the last ship changed, links to history | `/ship`, on every feature ship; rewritten each time |
| `log/` | One entry per pull request, newest by date: what changed and why | `/ship`; never rewritten after merge |
| `briefs/` | Parked prompts for `/office-hours`, one per idea, deleted when the plan is approved; local until you commit one. A folder named like the brief holds its supporting files and moves in beside the plan on approval | you, from `.agents/templates/human/brief.md` |

Three places hold writing about this project; they do not overlap:

- **`docs/human/`** (here): for people. What it does, in plain words. Committed by `/ship`.
- **`todo-app-notes/`**: the intake vault. Ideas and bugs as checkboxes the workflow promotes
  into plans and ticks when they ship, plus optional per-plan learning summaries. Gitignored,
  local to your machine.
- **`.agents/docs/`**: the product and engineering docs the agents work from (PRD, app flow,
  structure, lessons). Guarded by `doc-guard`; edited by the workflow skills, not by hand.

Quickfixes do not write here. A page's "As of" line is the date it was last true; the log has
everything since.
