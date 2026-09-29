# 2026-09-29 — Human-readable docs after every ship — docs/human/ (framework 1.6.1)

[PR #67](https://github.com/willdoucet/todo-app/pull/67) · branch `human-docs` · feature: [human-docs](../features/human-docs.md)

The repository now has a place written for people rather than agents. Every feature ship leaves a short page saying what that feature does now and a dated note like this one. Until now, the only way to find out what a feature did was to ask an agent or remember.

## What changed

- Add a plain-English page per feature and one dated log entry per pull request, both written when a feature ships and both shown in the pull request before it merges.
- Add a parking spot for ideas that are not ready to plan ("briefs"), which planning can pick up directly, along with any mockups or notes kept beside them.
- Keep parked briefs and Obsidian's own settings out of commits until someone deliberately commits a brief, while still committing mockups once a brief becomes a plan.
- Point the agents' project guide at the new folder.
- Upgrade the workflow tooling from 1.4.1 to 1.6.1.

## Worth knowing

- These pages are written by the AI, against the usual advice, because they come only from reviewed material and a person sees them in the pull request: [the decision](../../../.agents/docs/LESSONS.md#decisions).
- Quick fixes do not update these pages yet, so a page can fall behind; its "As of" date shows how current it is: [deferred work](../../../.agents/plans/features/human-docs/human-docs-plan-20260921-233505.md#deferred).
