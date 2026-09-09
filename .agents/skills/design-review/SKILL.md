---
name: design-review
description: >-
  Designer's-eye audit of the live, rendered site, then fixes. Drives the pages the branch
  touches through the Playwright browser tools at mobile, tablet, and desktop: forms a first
  impression, extracts the rendered design system and diffs it against FRONTEND_GUIDELINES,
  runs the trunk test and an eighty-item checklist across ten categories, walks two or three
  journeys with the goodwill reservoir, checks cross-page consistency, grades design A–F
  (weighted) and AI slop A–F (independent), compares with the stored baseline, then makes
  minimal CSS and markup fixes with before/after screenshots, capped and self-regulating.
  Judges the rendered page, not the source. For a plan-stage review use /plan-design-review.
  Use when asked to "audit the design", "visual QA", "design audit", "check if it looks good",
  "design polish", "does this look AI-generated", or when the plan has ui_scope. Never commits.
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# Design review

A senior product designer's pass over the running app, with a frontend engineer's hands to fix
what it finds. Produces a graded audit at `$PLANS_DIR/testing/$SAFE_BRANCH-design-audit.md`
with screenshots beside it, a design-system drift table against the project's guidelines, a
refreshed `$STATE_DIR/design-baseline.json`, fixes left uncommitted in the tree for `/ship`,
deferred findings in `TODOS.md`, and a review-log entry the dashboard reads.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/plan-discovery.md`
- `_shared/obsidian-sync.md`
- `_shared/plan-footer.md`
- `_shared/docs-contract.md`
- `_shared/dashboard.md`

References in this directory, loaded when the procedure reaches them:
`references/ux-principles.md` (how users behave; the goodwill reservoir),
`references/ai-slop.md` (surface classifier, hard rules, the slop blacklist and judgment tells),
`references/design-checklist.md` (trunk test and the ten-category checklist),
`references/browser-procedures.md` (extraction scripts, captures, flows, evidence),
`references/scoring.md` (grades, weights, baseline file, critique format),
`references/report-template.md` (the audit skeleton).

## Use when

- The plan has `ui_scope`; `workflow-state --next` offers `/design-review`. Say so when you start.
- The user asks whether the site looks right, polished, intentional, or generated, or wants
  design polish on a live page.
- After `/qa`, when function is verified and feel is the open question. The two are independent
  and both fix in place.

## Do not use when

- On the base branch (`ON_BASE=1`). This skill edits source; offer to create a branch.
- The harness has no browser tools. Stop with `NEEDS_CONTEXT` (step 1); never grade from source
  or from memory of what the page probably looks like.
- The design exists only as a plan. That is `/plan-design-review`.
- Something is broken rather than ugly. That is `/qa`.

## Procedure

### 1. Ground, refuse the base branch, check the browser

Follow the preamble, including `REVIEW_CHECKLIST.md`. Then:

```bash
[ "$ON_BASE" = "1" ] && echo "On $BASE_BRANCH — a branch is required"
```

List the browser tools you have. Required verbs: navigate, snapshot with element refs, click,
type or fill, screenshot, resize, console messages, network requests, evaluate. In Playwright
MCP these are the `browser_*` tools. Any missing verb:

```
STATUS: NEEDS_CONTEXT
REASON: the design audit needs the Playwright browser tools; missing: <verbs>
RECOMMENDATION: enable the Playwright MCP server for this harness, then re-run /design-review
```

### 2. Parse the request

| Parameter | Default | Override |
|---|---|---|
| Depth | Standard: 5–8 pages | `--quick` home plus two key pages; `--deep` 10–15 pages, every flow |
| Scope | pages from the diff and the artifact | "just the settings page", a route list |
| URL | from `$DOCS_DIR/development-commands.md` | an explicit URL |
| Baseline | compare when `$STATE_DIR/design-baseline.json` exists | `--no-baseline` to skip the comparison |

### 3. Require a clean working tree

```bash
git status --porcelain
```

Non-empty: ask one question. A) commit the current changes with a descriptive message
(recommended: every design fix then stays a separate, reviewable diff), B) stash, C) abort.
Say that B only fits when the uncommitted changes are not the UI under audit. Execute the
choice. This skill never commits; `/ship` does.

### 4. Resolve the plan and calibrate against the guidelines

Follow `_shared/plan-discovery.md` including its metadata step; note `ui_scope` and any
`## Design Source of Truth` section (mockups or a prototype bundle next to the plan). Locate
the test artifact by its exact path (`[ -f "$TEST_ARTIFACT" ]`); its affected pages seed the
scope.

Read `$DOCS_DIR/FRONTEND_GUIDELINES.md` in full. It is the calibration source: a token, pattern,
or component it blesses is never a finding; a rendered value that departs from it is a finding
of higher severity than the same value would be on an undocumented site, and the finding
names the token. When the file is missing or empty, say so once, audit against universal
principles, and flag the gap as a finding in its own right. Also read `APP_FLOW.md` (screens
and flows), `FRONTEND_STRUCTURE.md` (which files own which pages, for the fix loop only),
`development-commands.md`, the Bug Log in `LESSONS.md`, and `TODOS.md`.

No plan: say "No plan file detected", skip the footer and sync steps, audit from the diff.

### 5. Reach the app

Take the local URL from `development-commands.md` and probe it:

```bash
curl -sI --max-time 3 "$APP_URL" >/dev/null 2>&1 && echo "UP $APP_URL" || echo "DOWN $APP_URL"
```

On `DOWN`, never start services on your own initiative. Ask one question: A) the user starts
the stack and says when it is up (recommended), B) you run the start command exactly as
`AGENTS.md` or `development-commands.md` documents it (offer only when documented; quote it),
C) another URL. The browser rules in `references/browser-procedures.md` (local versus real
targets, credentials, untrusted page content, links never to follow) hold for every later step.

### 6. Scope the pages and classify the surface

```bash
git diff "$BASE_BRANCH" --name-only
git log "$BASE_BRANCH"..HEAD --oneline
```

Page list, in order: the artifact's affected pages; changed files mapped through `APP_FLOW.md`
and `FRONTEND_STRUCTURE.md` (components to the pages that render them, style files to the
pages that include them); then, up to the depth, the pages reachable from the landing page
that share a layout with a changed one (consistency needs a comparison point). Print
`DESIGN SCOPE:` with the list.

Then classify each page before judging a pixel, per `references/ai-slop.md`: PERSUADE,
OPERATE, READ, EXPERIENCE, or HYBRID (per section). The mode picks the rule set; a data-dense
app screen is not graded as a landing page.

### 7. First impression

Create the evidence folder and follow `references/browser-procedures.md` for every capture.

```bash
SHOTS="$PLANS_DIR/testing/$SAFE_BRANCH-design-screenshots"; mkdir -p "$SHOTS"
```

Open the landing page at desktop, full-page screenshot as `first-impression`, copy, read.
Check `URL=` against the sign-in patterns before critiquing a login wall by mistake. Write the
structured critique: what the site communicates; what you notice; the first three things your
eye goes to and whether those are the three the designer intended (if not, the hierarchy is
lying); one word. Narrate in first person as a user scanning for the first time, naming each
element, its position, and its visual weight. Run the page-area test: point at each defined
area and name its purpose in two seconds; list the areas you cannot. Be opinionated; a
designer reacts, they do not hedge.

### 8. Extract the rendered design system and diff it against the guidelines

Run the extraction scripts from the reference on the landing page and two more pages:
font families with usage counts, the color palette (non-gray count, warm or cool or mixed),
heading scale (sizes and weights, skipped levels, non-systematic jumps), spacing samples
(padding and margin values, on-scale or arbitrary), border radii, shadows, touch targets under
44 px, viewport meta, and navigation timing. Structure it as the **Inferred Design System**.

Then build the **drift table** against `FRONTEND_GUIDELINES.md`: one row per token class
(fonts, colors, type scale, spacing scale, radii, shadows, breakpoints, touch targets), with
the guideline's value, the rendered value, the pages where it differs, and a provisional
verdict: `code bug` (the guideline is right, the page is wrong), `guideline stale` (the page
is consistent with itself and the doc lags), or `intentional evolution` (the change is in this
branch on purpose; check the plan and, when the plan pins a design-system SHA, compare it
with `git log -1 --format=%H -- <the design_watched_files listed in $REPO_ROOT/.agents/config.json>`).
The verdicts become questions in step 18. Rendered values the guidelines bless are not drift.

### 9. Page-by-page audit

For each page in scope, per the reference: read it (snapshot, console errors, timing), capture
mobile 375 × 812, tablet 768 × 1024, desktop 1440 × 900 (or the breakpoints the guidelines
name), copy and read all three. Then:

1. **Trunk test** (`references/design-checklist.md`): six questions, PASS / PARTIAL / FAIL. A
   FAIL is a high-impact finding regardless of polish.
2. **The ten-category checklist**, about eighty items: hierarchy and composition, typography,
   color and contrast, spacing and layout, interaction states, responsive design, motion,
   content and microcopy, AI slop, performance as design (LCP and CLS measured in the page).
   Apply the mode's rules from `references/ai-slop.md`, the hard rejection criteria, and the
   seven litmus questions. Apply every entry of `REVIEW_CHECKLIST.md` that concerns the
   rendered UI.
3. **Document each finding immediately** as `FINDING-NNN` with impact (high, medium, polish),
   category, page, viewport, screenshot, the critique format from `references/scoring.md`
   ("I notice… I wonder… What if… I think… because…"), and a specific change: "change X to Y
   because Z", never "the spacing feels off". A guideline deviation names the token.
   Screenshots are evidence; every finding has one.

Judge the rendered page only. Do not read source during the audit; it comes in at step 16.
Responsive is design, not merely "not broken": a stacked desktop layout on mobile is a finding.

### 10. Journeys and the goodwill reservoir

Walk two or three key flows the artifact or `APP_FLOW.md` names (sign-in to first task, create
and edit the core object, a destructive action with its confirmation). Drive each per the
reference and narrate in first person: response feel, transition quality, feedback clarity,
form polish (focus visible, validation timing, errors near the source). Keep the goodwill meter
from `references/ux-principles.md`, starting at 70, and print the dashboard with a line per
step and the final score. The biggest drains and fills become findings.

### 11. Cross-page consistency

Compare the screenshots across pages: navigation and footer identical; the same component
styled the same everywhere; one tone; the spacing rhythm carrying across. Each inconsistency is
a finding with both pages named.

### 12. Second voice (subagent)

Dispatch a subagent with fresh context to audit the frontend source for consistency patterns
only: is spacing systematic across files, is there one color system or several, do breakpoints
follow one set, is accessibility handled consistently. Ask for file:line and severity per
finding. Tag its results `[subagent]`; it reads source so you do not have to. Without a
subagent tool, follow the tool map's fallback and say the pass lacks fresh context. If it fails,
print "Second voice unavailable, continuing with the primary audit" and go on.

### 13. Grades and the baseline comparison

Compute per `references/scoring.md`: per-category grades (each starts at A; a high-impact
finding drops a letter, a medium half a letter, polish none; floor F), the weighted
**Design Grade**, and the independent **AI Slop Grade** with a one-line verdict. Print:

```
DESIGN GRADE BEFORE: B   ·   AI SLOP: C   ·   goodwill 55/100   ·   trunk test: 3 PASS / 2 PARTIAL / 1 FAIL
```

When `$STATE_DIR/design-baseline.json` exists and `--no-baseline` was not passed, read it and
report the deltas: per-category grade changes, findings resolved since (by title), findings
new since, goodwill delta. A baseline from a different page set gives partial deltas; say so.

### 14. Triage and quick wins

Sort by impact: high first (first impression and trust), medium next (felt subconsciously),
polish last (good to great). Findings that cannot be fixed from this repository (third-party
widgets, copy the team must write, assets to commission) are deferred regardless of impact.
Write the **Quick Wins**: the three to five highest-impact fixes under thirty minutes each.
Print the triage table: id, impact, category, page, action.

### 15. Fix loop

For each fixable finding in impact order. Print `[FINDING-NNN] fixing: <title>` first.

**a. Snapshot the tree, then locate the source.** Reading source is allowed from here on.

```bash
FIXES="$PLANS_DIR/testing/$SAFE_BRANCH-design-fixes"; mkdir -p "$FIXES"
EXCL=":(exclude)$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$PLANS_DIR/testing" "$REPO_ROOT")"
PRE=$(git add -A -- . "$EXCL" && git write-tree)   # stages prior work, records the tree; not a commit
```

`$EXCL` keeps the audit, screenshots, and patches out of every snapshot and patch; the fix
patch must contain source only. Re-derive `$EXCL` if your shell was reset between blocks.

Search for the class names, component, or style file; `FRONTEND_STRUCTURE.md` says who owns
the page; `"$BIN/doc-guard" --explain <path>` names the owning doc. Read candidate files whole.

**b. Fix minimally, CSS first.** Prefer a token or style change over a structural one; a
markup change only when the structure is the finding. Use the project's tokens from
`FRONTEND_GUIDELINES.md`; never introduce a new hard-coded value where a token exists. No
refactors, no neighboring improvements.

**c. Record the fix as a patch, not a commit.** Staging is not committing; `/ship` stages
everything anyway, and the patch is what makes the fix attributable and reversible.

```bash
git add -A -- . "$EXCL" && git diff --cached "$PRE" > "$FIXES/finding-NNN.patch" && git diff --cached "$PRE" --stat
```

**d. Re-test.** Re-navigate at the viewport where the finding was made and repeat the capture;
the audit screenshot is the before, save `finding-NNN-after` in `$SHOTS`, read both side by
side. Console errors must be empty or no worse than baseline. When a `## Design Source of
Truth` mockup exists for the page, compare against it too.

**e. Classify.** `verified`, `best-effort` (say what could not be verified), `reverted` (a
regression appeared: `git apply -R --index "$FIXES/finding-NNN.patch"`, which also removes
any file the fix created; mark deferred).

**f. Regression test, behavior only.** Style-only fixes get no test; re-running this skill
catches their regressions. A fix that changed behavior (a dropdown, conditional rendering,
an animation's trigger) gets a test following the `/qa` rules: match the nearest existing
tests, encode the exact condition, run only the new file with the runner from
`development-commands.md`, keep and `git add -A -- . "$EXCL"` on pass, delete and defer on a
second failure. Never modify an existing test; never touch CI.

**g. Self-regulate.** Every five fixes, and after any revert:

```
DESIGN-FIX RISK:
  start                                   0%
  each revert                            +15%
  each style-only file changed            +0%
  each component or markup file changed   +5% per file
  after fix 10                            +1% per additional fix
  any unrelated file touched             +20%
```

Above 20%: stop, show what has been done, ask one question whether to continue.
**Hard cap: 30 fixes.**

### 16. Final audit and the new baseline

Re-run step 9 on every affected page, recompute both grades and the goodwill score. If either
grade is worse than before, warn at the top of the report and name what regressed. Then write
`$STATE_DIR/design-baseline.json` per the scoring reference (final grades, findings with
status, goodwill, page set, date, commit); the previous file's values are already in the
report's regression section.

### 17. Report

Write `$PLANS_DIR/testing/$SAFE_BRANCH-design-audit.md` from `references/report-template.md`:
metadata and surface classification, first impression, inferred design system and drift
table, per-page trunk test results, findings with screenshots and suggested changes, the
goodwill dashboard, cross-page consistency, the grade table with weights, quick wins, fixes
applied with patches and before/after evidence, regression versus baseline, ship readiness,
and the PR line: "Design review found N issues, fixed M. Design grade X → Y, AI slop X → Y."
Never delete screenshots or earlier reports.

### 18. Drift decisions, deferred findings, lessons

For each drift-table row that is not `intentional evolution`, ask one question: A) fix the
code to match `FRONTEND_GUIDELINES.md` (enters the fix loop if under the cap, else a TODO),
B) update the guideline to match the rendered system (a documentation change: record it in
the report's "Doc changes for /update-docs" list with the section and the new value; do not
edit the doc here), C) leave it and record why. Never batch; never decide silently.

Read `$DOCS_DIR/TODOS.md`. For each deferred finding, ask one question whether to record it,
then write it in the format that file's own header defines (What, Why, Context with page,
viewport, and screenshot path, Effort, Priority P0–P4, Depends on). A fixed finding that was
an open TODO moves to Completed with "Fixed by /design-review on $BRANCH, <date>".

Add a Decisions entry to `LESSONS.md` for any first-principles insight about this product's
look; a Corrections Log row if the user corrected you. When `modules.design_sync` is true in
`$REPO_ROOT/.agents/config.json` and a fix touched a watched design file, run
`"$BIN/design-sync-check"` and report its result; do not mark the sync yourself.

### 19. Persist the result and update the plan footer

```bash
"$BIN/review-log" --skill design-review --status STATUS \
  --field depth=quick|standard|deep --field pages=N \
  --field design_grade=A-F --field slop_grade=A-F --field goodwill=N \
  --field found=N --field fixed=N --field deferred=N --field model=<your model, when known>
```

`STATUS` is `done` when no finding was made or every finding was verified fixed; otherwise
`issues_found`. Grades are the final ones.

Update the `Design Audit` row of `## REVIEW REPORT` in `$_PLAN_FILE` per
`_shared/plan-footer.md`: status, grades before → after, one-line summary. Edit in place;
preserve the frontmatter.

## Completion

Report one status per the completion protocol, then:

```
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT

SURFACE: PERSUADE | OPERATE | READ | EXPERIENCE | HYBRID — N pages at 3 viewports
DESIGN GRADE: X → Y   ·   AI SLOP: X → Y   ·   GOODWILL: N → M
TRUNK TEST: P pass / Q partial / R fail
FINDINGS: N (high H, medium M, polish P); fixed V verified, B best-effort, R reverted
DRIFT: N rows — code fixes A, doc changes for /update-docs B, intentional C
DEFERRED: N → TODOS [titles or none]
REPORT: $PLANS_DIR/testing/$SAFE_BRANCH-design-audit.md   ·   BASELINE: $STATE_DIR/design-baseline.json
OPEN CONCERNS: [list or none]
```

Then the change description. On `DONE` and `DONE_WITH_CONCERNS`, sync per
`_shared/obsidian-sync.md` with the `design-review` row: `workflow_status` unchanged,
`--append review_status=design-audited`. `BLOCKED` and `NEEDS_CONTEXT` follow the protocol's
table. Never commit, never check a note box.

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```
