# Health score

One number, 0–100, computed the same way before and after the fix loop so the delta means
something. Compute each category score, then the weighted average. Show the category table
every time you print the score.

## Counting rules

- **Deduplicate.** The same root cause across pages is one issue. Assign one primary category,
  the first applicable: Links (navigation), Accessibility (access barriers), Functional
  (behavior), Performance (speed), Visual (layout), Content (copy), UX (friction), Console
  (errors not already scored elsewhere). No double deductions.
- **Untested categories are excluded** from the weighted average, not scored 100. A category
  tested on some pages only is **provisional**; say which pages. Nothing tested: "not scored".
- **Compare only identical coverage.** A before and after with different page sets is not a
  delta; re-run the after on the before's pages.

## Console (weight 15%)

Deduplicate reproducible errors and exceptions by message and source across pages. Exclude
warnings, info, and defects scored in another category.

| Errors | Score |
|---|---|
| 0 | 100 |
| 1–3 | 70 |
| 4–10 | 40 |
| 11+ | 10 |

## Links (weight 10%)

Count unique broken destinations, including client-side routes: repeatable 4xx or 5xx, missing
routes or anchors, timeouts. Exclude expected auth redirects and resource or API requests
(those are Console or Functional). Unverified links on a non-local target do not count.

Score = 100 − 15 per broken destination, floor 0.

## Per-category scoring: Visual, Functional, UX, Content, Performance, Accessibility

Start at 100, deduct per issue, floor 0:

| Severity | Deduction |
|---|---|
| Critical | −25 |
| High | −15 |
| Medium | −8 |
| Low | −3 |

Severity definitions are in `issue-taxonomy.md`. Use the highest applicable severity and record
impact and workaround on the issue.

## Weights

| Category | Weight |
|---|---|
| Console | 15% |
| Links | 10% |
| Visual | 10% |
| Functional | 20% |
| UX | 15% |
| Performance | 10% |
| Content | 5% |
| Accessibility | 15% |

## Final score

With decimal weights (15% = 0.15):

```
score = Σ (category_score × weight) / Σ (weights of tested categories)
```

Round only the final score, to the nearest integer, halves up. Print:

```
HEALTH: 74/100   console 70 · links 100 · visual 92 · functional 60 · ux 85 · performance 100 · content 97 · accessibility 55
```

If the after score is lower than the before score, the report opens with a warning naming the
regression.

## Baseline file

Write `$PLANS_DIR/testing/$SAFE_BRANCH-qa-baseline.json` at the end of the run. When one already
exists at that path, read it first and append the regression section to the report (health
delta, issues fixed since: in the baseline and not now; issues new since: now and not in the
baseline), then overwrite.

```json
{
  "schemaVersion": 1,
  "date": "YYYY-MM-DD",
  "branch": "<branch>",
  "commit": "<short sha>",
  "url": "<target>",
  "mode": "diff | full | quick",
  "tier": "quick | standard | exhaustive",
  "pages": ["/", "/settings"],
  "healthBefore": 74,
  "healthAfter": 91,
  "categoryScores": { "console": 100, "links": 100, "visual": 92, "functional": 90, "ux": 85, "performance": 100, "content": 97, "accessibility": 80 },
  "issues": [
    { "id": "ISSUE-001", "title": "...", "severity": "high", "category": "functional", "page": "/settings", "status": "verified | best-effort | reverted | deferred" }
  ]
}
```

Write it with a small inline Python script (the helpers are Python; no other JSON tool is
assumed). Keep issue ids stable across runs by title match so "fixed since" and "new since"
line up.
