# Adversarial subagent prompts

The subagent gets fresh context on purpose. Give it the prompt below and nothing from the
structured review: no findings, no summary, no hints. Its independence is what catches the
things the primary reviewer is blind to.

Substitute the base branch and the docs directory before dispatch; the subagent does not share
your shell variables.

## Medium tier (50–199 lines changed)

> Read the diff for this branch with `git diff <base branch>` and read every changed file in
> full. Think like an attacker and a chaos engineer. Your job is to find the ways this code
> fails in production. Look for edge cases, race conditions, security holes, resource leaks,
> failure modes, silent data corruption, logic errors that produce wrong results silently,
> error handling that swallows failures, and trust boundary violations. Read
> `<docs dir>/REVIEW_CHECKLIST.md` and apply every entry that matches a changed file. Be
> adversarial. Be thorough. No compliments, only problems. For each finding give file:line,
> the failure in one line, and classify it FIXABLE (you know the fix; state it) or
> INVESTIGATE (needs human judgment; say what to look at).

## Large tier (200+ lines changed, or a thorough review was requested)

> Read the diff for this branch with `git diff <base branch>` and read every changed file in
> full. This is a large diff. Think like an attacker and a chaos engineer. For each changed
> file, trace the full data flow from entry point to persistence or render, and check for edge
> cases, race conditions, security holes, resource leaks, failure modes, silent data
> corruption, logic errors, swallowed failures, trust boundary violations, N+1 access
> patterns, missing indexes for new query patterns, and missing input validation. Check
> cross-file consistency: every file that references a changed interface, schema, type, or
> enum must handle the change. Read `<docs dir>/REVIEW_CHECKLIST.md` and apply every entry
> that matches a changed file. Be adversarial. Be thorough. No compliments, only problems.
> For each finding give file:line, the failure in one line, and classify it FIXABLE (state
> the fix) or INVESTIGATE (say what to look at).

## Synthesis block

After both passes:

```
ADVERSARIAL REVIEW SYNTHESIS (auto: TIER, N lines):
════════════════════════════════════════════════════════════
  High confidence (found by both structured + adversarial): [findings]
  Unique to structured review: [findings]
  Unique to adversarial review: [findings]
════════════════════════════════════════════════════════════
```

Fix the high-confidence findings first. FIXABLE findings enter the fix-first flow; INVESTIGATE
findings are reported as informational with the suggested line of inquiry.

## No subagent tool

Per `_shared/tool-map.md`: do the pass yourself under a heading that says it lacks fresh
context, after finishing the structured review and before re-reading your own findings. For a
genuinely independent pass, switch harness or model and run `/final-review`.
