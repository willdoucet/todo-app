# Design audit report template

Copy this skeleton to `$PLANS_DIR/testing/$SAFE_BRANCH-design-audit.md` before the first
impression and fill it in as you go: findings when found, grades at the end of the baseline
and again after the fix loop. Screenshot paths are relative to the report; the folder
`$SAFE_BRANCH-design-screenshots/` is a sibling.

```markdown
# Design Audit: {PROJECT}

> ⚠ REGRESSION: design grade {before} → {after} / slop {before} → {after}. {what regressed}   ← only when it did

| Field | Value |
|---|---|
| **Date** | {DATE} |
| **URL** | {URL} |
| **Branch** | {BRANCH} |
| **Commit** | {SHORT SHA} |
| **Plan** | {plan file or "none"} · Design source of truth: {mockups / prototype / none} |
| **Guidelines** | {FRONTEND_GUIDELINES.md present / missing} |
| **Depth / Scope** | Standard · {pages} |
| **Surface** | PERSUADE / OPERATE / READ / EXPERIENCE / HYBRID ({per section when hybrid}) |
| **Viewports** | 375 × 812 · 768 × 1024 · 1440 × 900 |
| **Screenshots** | {COUNT} in `{SAFE_BRANCH}-design-screenshots/` |
| **Baseline compared** | {date of previous} / first run |

## Design Grade: {BEFORE} → {AFTER}   ·   AI Slop Grade: {BEFORE} → {AFTER}

| Category | Weight | Before | After | High | Medium | Polish |
|---|---|---|---|---|---|---|
| Visual hierarchy | 15% | | | | | |
| Typography | 15% | | | | | |
| Spacing & layout | 15% | | | | | |
| Color & contrast | 10% | | | | | |
| Interaction states | 10% | | | | | |
| Responsive | 10% | | | | | |
| Content & microcopy | 10% | | | | | |
| AI slop | 5% | | | | | |
| Motion | 5% | | | | | |
| Performance feel | 5% | | | | | |

**Slop verdict:** {one line}

## First Impression

![First impression]({SAFE_BRANCH}-design-screenshots/first-impression.jpg)

The site communicates **{what}**. I notice **{observation}**. The first three things my eye
goes to are **{1}**, **{2}**, **{3}** — {intended? if not, the hierarchy is lying}. In one word:
**{word}**.

{First-person narration of the scan, naming elements, positions, and weights.}

**Page-area test:** areas nameable in two seconds: {list}. Not nameable: {list}.

## Inferred Design System

- **Fonts:** {families with counts; flag over three}
- **Colors:** {palette; non-gray count; warm / cool / mixed}
- **Heading scale:** {h1–h6 sizes and weights; skipped levels; non-systematic jumps}
- **Spacing:** {sampled values; on-scale or arbitrary}
- **Radii and shadows:** {values; hierarchy or uniform}
- **Touch targets under 44 px:** {count, worst offenders}
- **Viewport / color scheme / reduced motion:** {values}

### Drift against FRONTEND_GUIDELINES.md

| Token class | Guideline | Rendered | Pages | Verdict | Decision |
|---|---|---|---|---|---|
| {fonts / colors / type scale / spacing / radii / shadows / breakpoints / touch targets} | {value} | {value} | {pages} | code bug / guideline stale / intentional evolution | fix code / doc change / leave ({why}) |

**Doc changes for /update-docs:** {section → new value, or none}

## Trunk Test

| Page | Site? | Page? | Sections? | Options? | Where? | Search? | Result |
|---|---|---|---|---|---|---|---|
| {route} | ✓/✗ | | | | | | PASS / PARTIAL / FAIL |

## Findings

### FINDING-001: {Short title}

| Field | Value |
|---|---|
| **Impact** | high / medium / polish |
| **Category** | hierarchy / typography / color / spacing / states / responsive / motion / content / slop / performance |
| **Page / Viewport** | {route} · {viewport} |
| **Pattern** | {[rule-id] or judgment tell, when slop} · **Token** {guideline token, when drift} |
| **Screenshot** | ![]({SAFE_BRANCH}-design-screenshots/{file}) |

I notice… / I wonder… / What if… / I think… because…

**Change:** {X} to {Y} because {Z}.

---

## Journeys and Goodwill

### {Journey name}
{First-person narration: response feel, transitions, feedback, form polish.}

```
Goodwill: 70 ████████████████████░░░░░░░░░░
  Step 1: …   70 → 75  (+5 …)
  FINAL: {N}/100  {healthy / needs work / critical UX debt}
```

Biggest drains: {list → findings}. Biggest fills: {list}.

## Cross-Page Consistency

| Check | Result | Pages |
|---|---|---|
| Navigation identical | | |
| Footer identical | | |
| Same component, same styling | | |
| One tone | | |
| Spacing rhythm carries | | |

## Second Voice [subagent]

{Consistency findings with file:line and severity, or "unavailable".}

## Quick Wins

1. {page · element · change · why} (~{minutes})
2. …

## Fixes Applied

| Finding | Status | Files changed | Patch |
|---|---|---|---|
| FINDING-NNN | verified / best-effort / reverted / deferred | {files} | `{SAFE_BRANCH}-design-fixes/finding-NNN.patch` |

### Before / After Evidence

#### FINDING-NNN: {title}
**Before:** ![]({SAFE_BRANCH}-design-screenshots/{page}-{viewport}.jpg)
**After:** ![]({SAFE_BRANCH}-design-screenshots/finding-NNN-after.jpg)
Console before → after: {arrays}. {mockup comparison when a design source of truth exists}

## Regression Tests (behavior fixes only)

| Finding | Test file | Runner | Status |
|---|---|---|---|

## Design-Fix Risk

Final tally: {N}% ({reverts, component files, unrelated files}). Fixes applied: {N} of cap 30.

## Regression vs Previous Baseline

| Metric | Previous | Current | Delta |
|---|---|---|---|
| Design grade | | | |
| AI slop grade | | | |
| {category…} | | | |
| Goodwill ({journey}) | | | |

**Resolved since previous:** {titles}  ·  **New since previous:** {titles}

## Ship Readiness

| Metric | Value |
|---|---|
| Design grade | {before} → {after} |
| AI slop grade | {before} → {after} |
| Findings | {N} (high H, medium M, polish P) |
| Fixes applied | {N} (verified V, best-effort B, reverted R) |
| Deferred | {N} → TODOS.md |
| Drift decisions | code fixes {A}, doc changes {B}, intentional {C} |

**PR summary:** "Design review found {N} issues, fixed {M}. Design grade {X} → {Y}, AI slop {X} → {Y}."
```
