# Scoring, baseline, and critique format

## Per-category grades

Each of the ten checklist categories starts at **A**. Each high-impact finding drops one
letter; each medium-impact finding drops half a letter (two mediums equal one letter). Polish
findings are recorded but do not move the grade. Floor is **F**. Round half-letters down in
the report (a B-and-a-half is B).

| Grade | Meaning |
|---|---|
| **A** | Intentional, polished, delightful. Shows design thinking. |
| **B** | Solid fundamentals, minor inconsistencies. Looks professional. |
| **C** | Functional but generic. No major problems, no point of view. |
| **D** | Noticeable problems. Feels unfinished or careless. |
| **F** | Actively hurting the user. Needs significant rework. |

## Design Grade (weighted)

| Category | Weight |
|---|---|
| Visual hierarchy and composition | 15% |
| Typography | 15% |
| Spacing and layout | 15% |
| Color and contrast | 10% |
| Interaction states | 10% |
| Responsive design | 10% |
| Content and microcopy | 10% |
| AI slop | 5% |
| Motion and animation | 5% |
| Performance as design | 5% |

Map A=4, B=3, C=2, D=1, F=0; weighted mean; back to a letter at the nearest whole value
(3.5 and up is A, 2.5 to 3.49 is B, and so on). A category not audited (for example motion on a
page with none) is excluded from the denominator and marked "not scored".

## AI Slop Grade (independent)

Graded from `ai-slop.md` alone, with a one-line verdict. It also feeds 5% of the Design
Grade, but the headline number stands on its own: a B design can be a D for slop, and the
report says so.

## Trunk test and goodwill

Report the trunk test as counts (PASS / PARTIAL / FAIL across pages) and the goodwill score
per journey with its dashboard (`ux-principles.md`). Neither moves the letter grades directly;
a trunk FAIL and each large goodwill drain are findings that do.

## Impact levels

- **high**: affects the first impression or user trust; a trunk-test FAIL; a hard rejection
  criterion; a guideline token contradicted on a primary surface; a mindless-choice failure
- **medium**: reduces polish, felt subconsciously; a checklist item missed on a secondary
  surface; a consistency break between pages
- **polish**: separates good from great; noted, fixed when time allows

## Critique format

Structured feedback, not opinion. Every finding uses at least two of these and ends with a
specific change:

- "I notice…" an observation ("I notice the primary action competes with the secondary one")
- "I wonder…" a question ("I wonder if users understand what 'Process' means here")
- "What if…" a suggestion ("What if search moved above the list?")
- "I think… because…" a reasoned opinion ("I think the section spacing is too uniform because
  it creates no hierarchy")

Then: **Change X to Y because Z.** Tie it to the user's goal. Depth over breadth: five to ten
findings with screenshots and specific changes beat twenty vague observations.

## Quick wins

Always include three to five: the highest-impact fixes that take under thirty minutes each,
with the page, the element, and the change.

## Baseline file

`$STATE_DIR/design-baseline.json`, written at the end of every run after the final audit. Read
the previous one first (step 13) and report deltas; then overwrite. Write it with an inline
Python script; no other JSON tool is assumed.

```json
{
  "schemaVersion": 1,
  "date": "YYYY-MM-DD",
  "branch": "<branch>",
  "commit": "<short sha>",
  "url": "<target>",
  "depth": "quick | standard | deep",
  "pages": ["/", "/settings"],
  "surface": "PERSUADE | OPERATE | READ | EXPERIENCE | HYBRID",
  "designGrade": "B",
  "aiSlopGrade": "C",
  "categoryGrades": { "hierarchy": "A", "typography": "B", "color": "B", "spacing": "C", "states": "B", "responsive": "B", "motion": "A", "content": "B", "slop": "C", "performance": "A" },
  "trunkTest": { "pass": 3, "partial": 2, "fail": 1 },
  "goodwill": { "sign-in-to-first-task": 55, "create-and-edit": 70 },
  "drift": [ { "token": "font-family.display", "guideline": "...", "rendered": "...", "verdict": "code bug | guideline stale | intentional evolution" } ],
  "findings": [
    { "id": "FINDING-001", "title": "...", "impact": "high", "category": "typography", "page": "/", "status": "verified | best-effort | reverted | deferred" }
  ]
}
```

## Regression output

When a previous baseline was read:

| Metric | Previous | Current | Delta |
|---|---|---|---|
| Design grade | B | A | +1 |
| AI slop grade | C | B | +1 |
| per category… | | | |
| Goodwill (per journey) | 55 | 70 | +15 |

Then **Resolved since previous** (titles in the previous file, absent now) and **New since
previous** (titles now, absent then). Match by title; keep titles stable across runs. A
different page set or surface gives partial deltas; say which pages overlap. Live pages
jitter (timing, dynamic content), so a single-step change in performance is advisory; a change
in findings is the signal.
