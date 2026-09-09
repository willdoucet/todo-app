<!-- Claude Code entry point. Project rules live in AGENTS.md; keep this file to what only Claude Code needs. -->
@AGENTS.md

## Claude Code notes

- Skills: `.claude/skills` is a symlink to `.agents/skills`. Invoke one with `/name args` (for example `/office-hours "Phase 1"`, `/quickfix todo-app-notes/Ideas.md#^task-id`).
- Session start: `.claude/settings.json` runs `.agents/bin/workflow-state --json` through a `SessionStart` hook, so the branch, plan, stage, and next step are already in context. Other harnesses run it by hand per the first line of AGENTS.md.
- `.agents/bin/` helpers are host-side; run them with `Bash` directly, never through a container. `.claude/settings.json` pre-allows them.
