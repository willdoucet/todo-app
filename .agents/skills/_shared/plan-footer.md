# Plan footer and folding decisions in place

## Fold decisions into the plan, in place

After a review or a design session, edit `_PLAN_FILE` to fold in every decision the user made.

- Use the edit tool, not the write tool. Targeted changes only; never rewrite the whole plan.
- Never create a sibling file with a suffix. Every downstream tool resolves the plan by its
  original filename.
- Update the specific sections a decision touches: scope, problem statement, success criteria,
  constraints, next steps, open questions, deferred. Leave a short breadcrumb next to each change,
  for example `Eng review 2: decision`.
- Preserve every frontmatter key.
- Do not ask permission. This is an automatic output of the skill, like the completion summary.

## REVIEW REPORT

Every plan carries a `## REVIEW REPORT` section at its end. Office-hours writes the placeholder;
each review updates its own row with a one-line findings summary.

**The Status cell carries the same word the review logged** (`clean`, `issues_open`, …). A row
never reads cleaner than its log entry. A `resolved` record does not rewrite the original
status: it adds to that row the resolver and where each item was closed, for example
`issues_open (2026-09-12) · resolved by /plan-eng-review, 2026-09-16: item 2, break-glass entry`.
A re-review demand **adds** to the demanded review's row, never rewriting its status, for
example `clean (2026-09-12) · re-review demanded by /plan-design-review, 2026-09-15: item 15a
adds a backend contract`; when that review runs again, its new entry on the row says
`scoped re-review of <what>` or names the full run.

```markdown
## REVIEW REPORT

| Review | Skill | Why | Status | Findings |
|---|---|---|---|---|
| CEO Review | `/plan-ceo-review` | Scope and strategy | — | — |
| Eng Review | `/plan-eng-review` | Architecture and tests (required) | — | — |
| Adversarial Review | `/plan-adversarial-review` | Red-team pass, prefer another model | — | — |
| Design Review | `/plan-design-review` | UI and UX | — | — |
| Implementation Review | `/review-implementation` | First code review (required) | — | — |
| Adversarial subagent | inside `/review-implementation` | Fresh-context pass on the diff | — | — |
| QA | `/qa` | Browser verification | — | — |
| Design Audit | `/design-review` | Live-site grade | — | — |
| Final Review | `/final-review` | Second opinion (required) | — | — |

**VERDICT:** NO REVIEWS YET
```

The verdict line is whatever `"$BIN/workflow-state" --dashboard` prints as its verdict.

If you are in a plan mode that restricts writes, the plan file is the one file you may edit,
and updating this footer is always allowed.
