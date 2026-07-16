# AGENTS.md

This file provides guidance to Grok Build when working with code in this repository.

Project rules (AGENTS.md) are the primary mechanism for per-project instructions in Grok Build. They are appended to the system prompt. `Claude.md` / `CLAUDE.md` files are supported for compatibility with Claude Code workflows (AGENTS.md takes precedence if present at the same level).

## Project Overview

Family task and responsibility management app with a FastAPI backend and React frontend.

**Documentation** (in `.claude/` directory):

| Document | Purpose |
|----------|---------|
| [PRD.md](./.claude/PRD.md) | Product requirements, user personas, feature specs, roadmap |
| [APP_FLOW.md](./.claude/APP_FLOW.md) | Every page, navigation path, and user flow |
| [TECH_STACK.md](./.claude/TECH_STACK.md) | All dependencies locked to exact versions |
| [FRONTEND_GUIDELINES.md](./.claude/FRONTEND_GUIDELINES.md) | Design system, colors, spacing, component patterns |
| [BACKEND_STRUCTURE.md](./.claude/BACKEND_STRUCTURE.md) | Database schema, API contracts, code organization |
| [FRONTEND_STRUCTURE.md](./.claude/FRONTEND_STRUCTURE.md) | Frontend directory layout, component inventory |
| [IMPLEMENTATION_PLAN.md](./.claude/IMPLEMENTATION_PLAN.md) | Step-by-step build sequence for remaining features |
| [LESSONS.md](./.claude/LESSONS.md) | Canonical mistakes, corrections, and project lessons |

Additional context lives in `todo-app-notes/`, `.claude/plans/`, and `.claude/agents/`.

## Development Commands — CRITICAL

**IMPORTANT: App commands must run through Docker Compose. Never run `npm`, backend app `uv`, or backend app `pytest` directly on the host.**

Exceptions (host-side by design):
- Local workflow tooling under `.claude/`
- The Obsidian helper at `.claude/skills/bin/obsidian-workflow`
- Tests for that helper live under `.claude/tests/`

For the complete reference (services, required environment variables, exact `docker-compose` invocations for running the stack, frontend, migrations, all forms of testing including visual regression, and local host-side helper tests), see the dedicated runbook:

→ **[Development Commands](development-commands.md)**

This is the single source of truth for development commands and is also referenced from CLAUDE.md.

## Workflow

### Planning for Ambiguity (Plan Mode)
Grok Build has **native plan mode** designed exactly for non-trivial tasks (3+ steps, architectural decisions, unclear requirements, high-impact changes). 

- The agent will automatically enter plan mode via `enter_plan_mode` when it detects genuine ambiguity.
- During plan mode: full read/search access, but writes are restricted to the plan file only.
- When ready, it calls `exit_plan_mode` and presents the plan for your approval.
- Use this flow: provide feedback, iterate the plan, then approve implementation.

Let the agent decide when plan mode is warranted. For clearly straightforward tasks (simple bugfix, adding a button that follows existing patterns), it should implement directly.

### Task Management & Tracking
- Use Grok's built-in `todo_write` tool for live, visible task lists during multi-step work. This renders checkable items in the scrollback.
- The project's established human/Obsidian workflow uses `.claude/tasks/todo.md`. Continue updating it for plans and status that need to survive sessions or be reviewed outside the agent.
- High-level summary + mark items done promptly as work progresses. Add a review section on completion.

### Subagents & Parallel Work
- Use subagents (via the `spawn_subagent` / `task` tool) liberally to keep the main context window clean.
- Built-in agent types: `general-purpose`, `explore` (read-only research), `plan`.
- Built-in personas for focused behavior: `reviewer`, `implementer`, `researcher`, `test-writer`, `security-auditor`, etc.
- Offload research, exploration, parallel analysis, or specialized review (e.g., "review this change as a senior frontend engineer").
- One focused task per subagent.

### Self-Improvement Loop
- After **any** correction from the user, or when you discover a recurring mistake pattern: update `.claude/LESSONS.md` with the rule.
- Ruthlessly iterate on these lessons. Review relevant sections of LESSONS.md at the start of work in that area.
- The project maintains a strong "verify current state" discipline (see LESSONS.md).

### Verification Before Done
- Never mark a task complete without proving it works.
- Run the actual commands/tests (through Docker Compose), check logs, exercise the behavior.
- Compare behavior/diffs against expected or main branch when relevant.
- Ask yourself: "Would a staff engineer approve this?"

### Demand Elegance (Balanced)
- For non-trivial changes: pause and consider "is there a more elegant way?"
- If a fix feels hacky: implement the cleaner solution with the full context you now have.
- Skip over-engineering for simple/obvious fixes.
- Challenge your own work before presenting it.

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code. Prefer the boring, obvious solution.
- **Scope Discipline**: Touch only what you're asked to touch. Do NOT remove comments you don't understand, "clean up" orthogonal code, refactor adjacent systems, or delete seemingly-unused code without explicit approval. Surgical precision.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
- **No Laziness / Root Cause**: Find root causes. No temporary fixes. Senior developer standards.
- **Assumption Surfacing**: Before implementing anything non-trivial, explicitly state assumptions in a clear "ASSUMPTIONS I'M MAKING" block and ask for correction.
- **Confusion Management**: When you see inconsistencies or ambiguity, STOP, name it specifically, present tradeoffs or ask the clarifying question. Do not guess.
- **Push Back When Warranted**: You are not a yes-machine. Point out clear problems with the requested approach, explain concrete downsides, propose alternatives. Accept the decision if overridden.
- **Dead Code Hygiene**: After refactoring or changes, identify unreachable code and explicitly ask: "Should I remove these now-unused elements?"
- **Communication**: Be direct. Quantify where possible. Don't hide uncertainty.

## Guardrails & Specific Rules

- **Docker-only for app work** (see [Development Commands](development-commands.md)). This is non-negotiable.
- When inspecting environment on any remote or containerized system (including `docker-compose exec`, Fly SSH, CI), **never** run unfiltered `env` or `printenv`. Secrets will leak into the transcript and require rotation. Always filter server-side (names only, existence checks, or redacted single vars).
- See `.claude/LESSONS.md` for the living set of project-specific rules and patterns (high signal, one canonical rule per topic).
- Respect `.gitignore`. Do not bypass it unless explicitly needed and approved.

## Grok Build Specifics

- Use `grok inspect` to see all loaded project rules, token counts, configuration, **and discovered skills**.
- Project-scoped configuration can live in `.grok/config.toml` (MCP servers), `.grok/skills/`, `.grok/agents/`, `.grok/hooks/`, etc.
- Skills are now available under `.grok/skills/` (repo-scoped but gitignored — local-only on each machine, like `.cursor/` and `.claude/skills/`). Invoke with `/skill-name` (e.g. `/office-hours`, `/plan-eng-review`, `/execute-plan`, `/review-implementation`) or `/skills` to list. They are the Grok-native home for the reusable workflows previously in `.claude/skills/`.
- For Grok skills, plan files (design docs from /office-hours, reviewed plans, etc.) are written to/read from `.grok/plans/features/<safe-branch>/` (and test artifacts to `.grok/plans/testing/`). This parallels the `.claude/plans/` structure so the two harnesses can coexist without interfering on the same branch's plans. The bin/ helpers (still invoked as `$REPO_ROOT/.claude/skills/bin/obsidian-workflow ...` etc.) accept arbitrary plan paths as arguments (e.g. `--plan-path "$_PLAN_FILE"`), so they work fine with plans under .grok/plans/. The workflow registry, review-log.json, eureka.jsonl, and most .claude/ docs remain shared under `.claude/` .
- The existing `.claude/` setup (detailed docs, custom agents in `.claude/agents/`, plans/features/, review logs, eureka.jsonl, TODOS.md, tasks/todo.md, the host-side bin/ helpers for Obsidian + review state + design sync, and .knowledge-quiz/) is retained and actively used by the skills. The bin/ CLIs are host-side by design (run directly via terminal tool, not Docker). Some Claude/Cursor compatibility scanning remains useful for hybrid workflows. The .claude/agents/ custom agents were already being picked up by Grok.
- The full review + implementation + Obsidian contract workflow is: `/office-hours` → `/plan-ceo-review` (optional but recommended for scope) → `/plan-eng-review` (required gate) → (Cursor `plan-adversarial-review` if used) → `/plan-design-review` (UI scope) → `/execute-plan` → `/review-implementation` → Cursor `cursor-implementation-review` (final Obsidian task checkoff + shipped state). The Grok skills own the first implementation review; the final gate is currently Cursor-specific.

## Skills (Reusable Workflows)

See the individual `SKILL.md` files under `.grok/skills/`. Each has a Grok port header with tool mappings (read_file / search_replace / run_terminal_command / ask_user_question / spawn_subagent / web_search / todo_write, etc.) and the detailed procedures.

Key ones:
- `office-hours`: Brainstorm / diagnostic or builder design thinking. Produces plan files. Obsidian note intake supported.
- `plan-ceo-review`, `plan-eng-review`, `plan-design-review`: The interactive plan review pipeline (scope/strategy, architecture+tests, UI/UX). Edit plans in place, produce review reports + dashboard, update Obsidian metadata.
- `execute-plan`: Step-by-step implementation executor. Strict Obsidian metadata protocol first, summary file, verification, supporting doc updates, hands off to review.
- `review-implementation`: Pre-landing diff review (Fix-First, scope drift + plan completion audit, coverage diagrams + gap tests, adversarial subagent, dashboard). Hands off to Cursor final gate.
- `learning-module`: Generate self-contained exercises from real project code in .knowledge-quiz/.

Supporting host-side CLIs live at `.claude/skills/bin/` (obsidian-workflow, review-log, review-read, design-sync-check/mark, etc.). Call them with full `$REPO_ROOT/.claude/skills/bin/...` paths from the terminal tool.

ETHOS.md (Boil the Lake + Search Before Building) is referenced by the skills and available at both `.claude/skills/ETHOS.md` and `.grok/skills/ETHOS.md`.

## What Not to Copy From Prior Claude.md

The large embedded behavioral system prompt that was present in the previous CLAUDE.md was specific to Claude Code's tool model and interaction patterns. Grok Build has native equivalents for plan mode, subagents, todo tracking, and strong built-in reasoning. The principles above capture the enduring engineering discipline without duplicating model-specific scaffolding.
