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
OPEN: /plan-ceo-review — ran with issues open: re-run it, or confirm each open item is closed and log resolved
```

Add one line reminding the user that the invocation syntax depends on the harness (`/name` in
Claude Code, Grok Build, and Cursor; `$name` in Codex).

## When the next step names a review that ran with issues open

`--next` names a review whose latest entry is `issues_open`; every other such review is an
`Open:` line. A review that ran and did not pass blocks its stage; "optional" governs only a
review that never ran. There are two ways to clear it, and only two.

1. **Confirm each open item is closed, then log a resolution.** Find the review's open items: a
   plan review's REVIEW REPORT row and the plan; `/qa`'s QA report; `/design-review`'s audit
   report; `/review-implementation`'s and `/final-review`'s findings in their REVIEW REPORT rows
   and the summary file. For each item, find where it is closed: a plan section, a report entry,
   or a commit. If every item is closed:

   ```bash
   "$BIN/review-log" --skill <that review> --status resolved \
     --field resolved_by=<the later review that verified the closure> \
     --field note="<where each item is closed>"
   ```

   The resolver is a review tier that ran after the failure and passed: never the skill that
   wrote the fix (`/execute-plan` and `/quickfix` are not review tiers) and never the failed
   review itself; `review-log` checks both. A failure at the ship stage (implementation review,
   adversarial subagent, QA, design audit, final review) takes a ship-stage resolver or
   `operator`, never a plan review and never `ship`. A resolution clears only the failure it
   names: a later failure of the same review, even one merged in from another branch, reopens
   it (`superseded_by_failure` in the row). At the plan stage the resolver is usually the next
   plan review; when the `--next` reason says a later review already passed, prefer logging
   `resolved` by that review over re-running. At the ship stage no later review runs before the
   gate, so a failed `/qa`, `/design-review`, implementation or final review clears in practice
   by re-running it after the fix, or by `operator`. Use `resolved_by=operator` only when the
   user said in this session that they decided the item; the dashboard row shows who resolved.
2. **Re-run the review** when any item is not closed. A re-run that fails again blocks again.

Never log `clean` under another skill's name. A review that closes an earlier failed review's
items logs its **own** entry first, then the resolution: `review-log` requires the resolver's
latest entry to be passed and not earlier than the failure.

```
                 review runs, logs clean / done
   missing ────────────────────────────────────▶ passed ◀────────────┐
      │                                            ▲                 │ re-run passes
      │ review runs, logs issues_open              │ re-run passes   │
      ▼                                            │                 │
   failed ──── review-log --status resolved ──────▶ resolved ────────┤
      ▲          resolved_by = another gating tier      │            │
      │          whose latest entry is passed at        │ re-run logs issues_open
      │          ts >= failure, or operator; note; once │
      └────────────────────────────────────────────────┘
   ok = passed | resolved · every transition is an appended log line
```

## Verdicts

A review's latest entry has one disposition: `missing` (never ran), `passed`, `failed` (ran
and did not pass), or `resolved`. **ok** is `passed` or `resolved`. `office-hours` is shown on
the dashboard but never gates.

- `CLEARED FOR IMPLEMENTATION`: eng review ok, design review ok when the plan has UI scope, and
  no plan-stage review (CEO, eng, adversarial, design) is `failed`.
- `CLEARED TO SHIP`: implementation review and final review ok, and no review of any gating
  tier is `failed`.
- `NOT CLEARED`: the missing items are listed; a failed one carries ` (issues open)`. Say which
  one you recommend doing first.
- `NOT CLEARED — review log unreadable`: the log holds a line that is not a JSON object,
  usually a merge-conflict marker. Resolve it by keeping both sides; every review command
  refuses until the log is whole.

A review counts only when it was logged against the current plan file. Superseding a plan resets
the dashboard, by design.
