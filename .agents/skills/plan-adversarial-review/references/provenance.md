# Provenance section

Loaded by `plan-adversarial-review` at step 10. Add or update this section at the end of
`$_PLAN_FILE`, before or after the review table but never inside it. If a prior adversarial
pass wrote one, update it in place rather than appending a second copy.

The heading carries no model or harness name. Both are fields inside the section, so the
section stays stable across reruns in different harnesses and the log stays greppable.

```markdown
## Adversarial Review Summary

- **Skill:** `plan-adversarial-review`
- **Harness:** <HARNESS from ctx>
- **Model:** <the model you are, or unknown>
- **Date:** <TIMESTAMP from ctx>
- **Eng review provenance:** harness=<eng_harness> model=<eng_model> (<different family | same family>)
- **Passes run:** 7 (premise inversion, hostile implementer, silent-failure hunt, rollout and
  reversal, test escape, trust boundary and abuse, future regret)

### What this review changed
- [short bullet, naming the section edited]
- [short bullet]

### Remaining adversarial concerns
- [severity] [concern] — [deferred by user | recorded in TODOS.md | needs decision]

### Why these were flagged
This pass was intentionally adversarial: it looked for failure modes, ambiguities, rollback
traps, silent failures, abuse cases, and test gaps that could still survive a normal
engineering review.
```

Rules:

- When every finding was fixed cleanly, write `Remaining adversarial concerns: none`.
- On an epic, "What this review changed" lists changes per milestone seam, for example
  `M2→M3: added flag-off rollback order`.
- This section records the review. It never substitutes for fixing the plan inline.
- The plan's review table gets a one-line summary in its `Adversarial Review` row; the detail
  lives here.
