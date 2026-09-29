# Human docs

As of 2026-09-29 · [PR #67](https://github.com/willdoucet/todo-app/pull/67) · [plan](../../../.agents/plans/features/human-docs/human-docs-plan-20260921-233505.md)

## What it does

Every time a feature ships, the workflow writes a short plain-English page about what that feature does now, plus a dated note of what that pull request changed, so anyone can find out without asking an agent or reading through plans. Both are written only from material that has already been reviewed, and both appear in the pull request, so a person checks them before anything merges. Each page opens with the date it was last true, so a page that has fallen behind says so. Ideas that are not ready to plan can be parked here as short briefs, with any mockups or notes beside them; when one is ready, planning picks it up and the brief is removed once its plan is approved. Quick fixes do not update these pages yet.

## What changed in this ship

- Add feature pages and a per-pull-request log, written at every feature ship.
- Add parked briefs that planning can pick up directly, companion files included.
- Keep parked briefs and Obsidian settings out of commits unless one is committed on purpose.
- Upgrade the workflow tooling to 1.6.1.

## History

- 2026-09-29 — [Human-readable docs after every ship — docs/human/ (framework 1.6.1)](../log/2026-09-29-human-docs.md)
