# Plan completion audit

How to turn the plan into a checklist and grade the diff against it. Informational: it never
blocks on its own, but NOT DONE items become findings, and summary boxes that disagree with the
diff are findings.

## Extract actionable items from `$_PLAN_FILE`

Include anything that describes work to do:

- Checkbox items, checked or not.
- Numbered steps under implementation headings ("1. Create ...", "2. Add ...").
- Imperative statements ("Add X to Y", "Create a Z service", "Modify the W handler").
- File-level specifications ("New file: path", "Modify path").
- Test requirements ("Test that X", "Add test for Y", "Verify Z").
- Data model changes ("Add column X to table Y", "Create migration for Z").

Ignore:

- Context, background, and problem sections.
- Questions and open items (`?`, "TBD", "TODO: decide").
- `## REVIEW REPORT`.
- Explicitly deferred items ("Future:", "Out of scope:", "NOT in scope:", "P2:" and lower).
- Review decision sections; they record choices, not work.

Cap at 50 items. Past that, note "Showing top 50 of N plan items — full list in plan file".
No items at all: "Plan file contains no actionable items — skipping completion audit."

For each item record its text (verbatim or a tight summary) and its category: CODE, TEST,
MIGRATION, CONFIG, DOCS.

## Grade each item against the diff

Use `git diff "$BASE_BRANCH"` and `git log "$BASE_BRANCH"..HEAD --oneline`.

- **DONE**: clear evidence in the diff. Cite the file(s). A touched file is not enough; the
  described functionality must be present.
- **PARTIAL**: some work exists but is incomplete (model without route, function without the
  edge cases the plan named).
- **NOT DONE**: no evidence.
- **CHANGED**: the goal is met by a different approach than the plan described. Note the
  difference. Be generous here; be conservative with DONE.

Cross-check with the summary file: a step ticked `[✓]` whose item grades NOT DONE is a finding
in its own right, because the summary is what the banner and the next executor trust.

## Output

```
PLAN COMPLETION AUDIT
═══════════════════════════════
Plan: <_PLAN_FILE>

## Implementation items
  [DONE]      Create the task service — app/services/tasks.py (+142)
  [PARTIAL]   Add validation — model validates, route checks missing
  [NOT DONE]  Add caching layer — no cache-related change in the diff
  [CHANGED]   "queue via X" → implemented with the existing job runner

## Test items
  [DONE]      Unit tests for the task service — tests/unit/test_tasks.py
  [NOT DONE]  End-to-end test for task creation

## Migration items
  [DONE]      Create tasks table — migrations/<id>_create_tasks.py

─────────────────────────────────
COMPLETION: 4/7 DONE, 1 PARTIAL, 1 NOT DONE, 1 CHANGED
─────────────────────────────────
```

Then the scope check, printed before the main review begins:

```
Scope Check: CLEAN | DRIFT DETECTED | REQUIREMENTS MISSING
Intent: <one line, from the plan>
Plan: <_PLAN_FILE or "none">
Delivered: <one line, what the diff actually does>
Plan items: N DONE, M PARTIAL, K NOT DONE, J CHANGED
Missing: <each NOT DONE item or unaddressed requirement>
Out of scope: <each change with no plan item behind it>
```

NOT DONE items feed REQUIREMENTS MISSING. Diff changes that match no plan item feed DRIFT
DETECTED. Without a plan, grade intent from commit messages, the pull request body, and
`TODOS.md` only, and omit the plan-items line.
