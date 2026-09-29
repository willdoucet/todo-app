# Tool map

Skills are written against these canonical verbs. Use the tool your harness provides for each.

| Canonical verb | Claude Code | Codex | Grok Build | Cursor |
|---|---|---|---|---|
| read file | `Read` | read via shell or file tool | `read_file` | `ReadFile` |
| search | `Grep`, `Glob` | `rg`, `find` via shell | `grep`, `list_dir` | `rg`, `Glob` |
| edit in place | `Edit` | `apply_patch` | `search_replace` | `ApplyPatch` |
| write new file | `Write` | `apply_patch` | `write` | `ApplyPatch` |
| shell | `Bash` | shell | `run_terminal_command` | `Shell` |
| ask the user (structured) | `AskUserQuestion` | none, use plain-text fallback | `ask_user_question` | `AskQuestion` |
| subagent | `Agent` | none, do the work inline in a fresh section | `spawn_subagent` | `Subagent` |
| web search | `WebSearch`, `WebFetch` | `web_search` if enabled | `web_search`, `web_fetch` | `WebSearch` |
| invoke another skill | `Skill` tool | read that `SKILL.md` and follow it inline | `/name` | read that `SKILL.md` and follow it inline |
| plan mode | `EnterPlanMode` / `ExitPlanMode` | none | `enter_plan_mode` / `exit_plan_mode` | none |
| task list | `TodoWrite` | none | `todo_write` | none |
| browser | Playwright MCP tools | Playwright MCP if configured | Playwright MCP if configured | Playwright MCP if configured |

Fallback rules:

- No structured question tool: write the four-part question as text with lettered options and
  wait. See `question-format.md`.
- No subagent tool: perform the subagent's task yourself in a clearly separated section, stating
  that it lacks fresh context. For adversarial and final reviews, prefer switching harness.
- No skill-invocation tool: read the target `SKILL.md` and execute it inline before continuing.
- No plan mode: skills that say "in plan mode" simply restrict themselves to editing the plan
  file until the user approves.
- Helpers in `.agents/bin` are host-side tools. Run them directly, never through a container,
  regardless of the project's command policy for application code.

## Subagent boundary

A subagent starts without `AGENTS.md` and cannot ask the user anything, so the rule to respect
`.gitignore` does not reach it unless the prompt carries it. End every subagent prompt with this
paragraph, verbatim:

> Do not open, search inside, or print any file that git ignores (`git check-ignore -q <path>`
> succeeds for it): local settings, env files, credentials, caches, scratch directories. This
> holds for the shell as much as for file tools; search with `git grep`, or `rg`, which skips
> ignored paths by default. You cannot ask the user for permission, so treat those files as out
> of bounds. When a finding depends on one, name the path and what you would check in it, and
> leave the reading to the user.

The fallback, doing the subagent's task yourself, keeps the same boundary.

Harness detection is best effort. `ctx` exports `HARNESS`; if it says `unknown`, ask the user
once and remember for the session.
