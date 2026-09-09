# QA report template

Copy this skeleton to `$PLANS_DIR/testing/$SAFE_BRANCH-qa-report.md` at the start of the
baseline audit and fill it in as you go. Issues are appended when found; the score sections are
filled at the end of the baseline and again after the fix loop. Screenshot paths are relative
to the report: `../$SAFE_BRANCH-qa-screenshots/` is a sibling folder, so write
`$SAFE_BRANCH-qa-screenshots/<file>`.

```markdown
# QA Report: {PROJECT}

> ⚠ REGRESSION: health score fell from {before} to {after}. {what regressed}   ← only when it did

| Field | Value |
|---|---|
| **Date** | {DATE} |
| **URL** | {URL} |
| **Branch** | {BRANCH} |
| **Commit** | {SHORT SHA} |
| **Plan** | {plan file or "none"} |
| **Test artifact** | {path or "none"} |
| **Mode / Tier** | diff · Standard |
| **Scope** | {pages tested} |
| **Duration** | {DURATION} |
| **Pages visited** | {COUNT} |
| **Screenshots** | {COUNT} in `{SAFE_BRANCH}-qa-screenshots/` |
| **App shape** | client-side routed / server-rendered / static / mixed |
| **Report-only** | yes / no |

## Health Score: {BEFORE}/100 → {AFTER}/100

| Category | Before | After |
|---|---|---|
| Console | {0-100} | {0-100} |
| Links | | |
| Visual | | |
| Functional | | |
| UX | | |
| Performance | | |
| Content | | |
| Accessibility | | |

Provisional categories: {list with coverage, or none}. Not scored: {list or none}.

## Top 3 Things to Fix

1. **{ISSUE-NNN}: {title}** — {one line}
2. **{ISSUE-NNN}: {title}** — {one line}
3. **{ISSUE-NNN}: {title}** — {one line}

## Console Health

| Error | Count | First seen |
|---|---|---|
| {message} | {N} | {URL} |

## Summary

| Severity | Found | Fixed | Deferred |
|---|---|---|---|
| Critical | 0 | 0 | 0 |
| High | 0 | 0 | 0 |
| Medium | 0 | 0 | 0 |
| Low | 0 | 0 | 0 |
| **Total** | **0** | **0** | **0** |

## Changes Tested (diff mode)

| Changed area | Page(s) | Intent (from plan / commits) | Works? | Evidence |
|---|---|---|---|---|
| {file or feature} | {route} | {what it should do} | yes / no / partial | {screenshot} |

## Issues

### ISSUE-001: {Short title}

| Field | Value |
|---|---|
| **Severity** | critical / high / medium / low |
| **Category** | visual / functional / ux / content / performance / console / accessibility / links |
| **Page** | {URL} |
| **Viewport** | desktop / mobile / both |
| **Checklist entry** | {REVIEW_CHECKLIST.md entry, when one applies} |
| **Prior lesson** | {LESSONS.md Bug Log row, when one applies} |

**Description:** {expected vs actual, impact, workaround if any}

**Repro Steps:**

1. Navigate to {URL}
   ![Step 1]({SAFE_BRANCH}-qa-screenshots/issue-001-step-1.jpg)
2. {Action}
3. **Observe:** {what goes wrong}
   ![Result]({SAFE_BRANCH}-qa-screenshots/issue-001-result.jpg)

`CONSOLE_ERRORS=` {array}  ·  `NETWORK_FAILURES=` {list}  ·  diff: {one line}

---

## Fixes Applied

| Issue | Status | Files changed | Patch |
|---|---|---|---|
| ISSUE-NNN | verified / best-effort / reverted / deferred | {files} | `{SAFE_BRANCH}-qa-fixes/issue-NNN.patch` |

### Before / After Evidence

#### ISSUE-NNN: {title}
**Before:** ![Before]({SAFE_BRANCH}-qa-screenshots/issue-NNN-result.jpg)
**After:** ![After]({SAFE_BRANCH}-qa-screenshots/issue-NNN-after.jpg)
Console before → after: {arrays}. {what the diff shows now}

## Regression Tests

| Issue | Test file | Runner | Status | Covers |
|---|---|---|---|---|
| ISSUE-NNN | {path} | {command from development-commands.md} | added / deferred / skipped | {precondition → assertion} |

### Deferred Tests

#### ISSUE-NNN: {title}
**Precondition:** {state that triggers the bug}
**Action:** {what the user does}
**Expected:** {correct behavior}
**Why deferred:** {reason}

## Fix Risk

Final tally: {N}% ({reverts, wide fixes, unrelated files}). Fixes applied: {N} of cap 50.

## Ship Readiness

| Metric | Value |
|---|---|
| Health score | {before} → {after} ({delta}) |
| Issues found | {N} |
| Fixes applied | {N} (verified {V}, best-effort {B}, reverted {R}) |
| Deferred | {N} → TODOS.md |

**PR summary:** "QA found {N} issues, fixed {M}, health score {X} → {Y}."

## Regression vs previous baseline

| Metric | Previous | Current | Delta |
|---|---|---|---|
| Health score | {N} | {N} | {±N} |
| Issues | {N} | {N} | {±N} |

**Fixed since previous:** {list}  ·  **New since previous:** {list}
```
