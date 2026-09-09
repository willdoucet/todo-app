# Dashboard and next step

Do not compute review readiness or the next step in prose. Both are derived from the registry,
the review log, and the plan's frontmatter by one function, so every skill and the session
banner agree.

## At the end of every skill

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```

Present the dashboard table verbatim, then the next step in this shape:

```
NEXT: /plan-eng-review — required (shipping gate)
OPTIONAL: /plan-adversarial-review — risk tags: auth, infra
```

Add one line reminding the user that the invocation syntax depends on the harness (`/name` in
Claude Code, Grok Build, and Cursor; `$name` in Codex).

## Verdicts

- `CLEARED FOR IMPLEMENTATION`: eng review clean, plus design review when the plan has UI scope.
- `CLEARED TO SHIP`: implementation review and final review clean.
- `NOT CLEARED`: the missing items are listed. Say which one you recommend doing first.

A review counts only when it was logged against the current plan file. Superseding a plan resets
the dashboard, by design.
