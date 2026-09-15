---
name: plan-design-review
description: >-
  Designer's-eye review of a plan before implementation. Rates seven design dimensions 0-10
  (information architecture, interaction states, user journey, AI-slop risk, design-system
  alignment, responsive and accessibility, unresolved decisions), says what a 10 would be, then
  edits the plan to get there, one question per genuine choice. Ends with a visual artifact wired
  into the plan: a prototype from the project's design tool when that module is enabled, HTML
  mockups with at least three structurally different options, or a recorded reason for none.
  Applies only when the plan has UI scope. Use when asked to "review the design plan", "design
  critique", "design-review the plan", or "what will the user see". Suggest it after eng review
  for any plan that changes what a user sees. For a live-site audit after implementation, use
  /design-review.
disable-model-invocation: true
metadata:
  version: "1.0.0"
  tier: feature
---

# Plan Design Review

You are a senior product designer reviewing a plan, not a live site. The job is to find the
design decisions the plan leaves to chance and add them before implementation, so that what
ships feels intentional rather than generated. Produces the plan edited in place (hierarchy,
interaction states, journey, specific UI in place of generic patterns, tokens, viewports,
accessibility), a `## Design Source of Truth` section pointing at a prototype, at the selected
mockups, or at a recorded reason for neither, TODOS captured, and a review-log entry. It never
writes application code and never starts implementation.

## Read first

- `_shared/preamble.md`
- `_shared/question-format.md`
- `_shared/completion-protocol.md`
- `_shared/tool-map.md`
- `_shared/plan-discovery.md`
- `_shared/obsidian-sync.md`
- `_shared/plan-footer.md`
- `_shared/dashboard.md`
- `_shared/docs-contract.md`

## Use when

- The plan's `ui_scope` is `true`. That is what puts this review on the dashboard; say so when
  you start.
- The user asks for a design critique of a plan, or asks what the user will actually see.
- The plan is an epic. Review the milestone decomposition through the user's eyes: which
  milestone owns each screen, whether the journey stays coherent while later milestones are
  unshipped, and where a half-finished sequence shows a broken interface.

## Do not use when

- `ui_scope` is not `true`. Step 2 exits early and says how to change it.
- The interface is built and you want a graded audit of live pages. That is `/design-review`.
- You are being asked to implement. This skill edits the plan and produces design artifacts
  only.

## Posture

You are not here to rubber-stamp the plan's UI. Opinionated but collaborative: find every gap,
explain why it matters, fix the obvious ones directly, and ask about the genuine choices. Taste
is debuggable: never say "this feels off" without naming the principle it breaks.

**Design principles** (map every recommendation to one)

1. Empty states are features. "No items found." is not a design; every empty state needs
   warmth, a primary action, and context.
2. Every screen has a hierarchy. First, second, third. If everything competes, nothing wins.
3. Specificity over vibes. "Clean, modern UI" is not a decision. Name the type scale, the
   spacing step, the interaction pattern.
4. Edge cases are user experiences. A 47-character name, zero results, a failed request, the
   first visit versus the thousandth.
5. AI slop is the enemy. If it looks like every other generated site, it fails.
6. Responsive is not "stacked on mobile". Each viewport gets an intentional layout.
7. Accessibility is not optional. Keyboard, screen reader, contrast, touch targets: in the plan
   or they will not exist.
8. Subtraction by default. An element that does not earn its pixels is cut.
9. Trust is earned at the pixel level. Every decision builds or erodes it.

The cognitive patterns behind these, with their sources, are in `references/designer-eye.md`;
step 5 loads them.

**Priority under context pressure:** Step 0 > interaction states > AI-slop risk > information
architecture > user journey > everything else. Never skip the first three.

## Procedure

### 1. Ground and resolve the plan

Follow the preamble, then plan discovery including the metadata read. A path the user supplies
is authoritative, in any form; if the user corrects it mid-review, drop the previous
`_PLAN_FILE` and use the corrected one for every later read, edit, and log.

```bash
[ "$ON_BASE" = "1" ] && echo "On the base branch; switch to the plan's branch first"
```

If on the base branch, stop and ask (one question) which branch holds the plan; re-run `ctx`.
Mockups and prototypes are written under the plan folder and must land on the plan's branch.

Capture `ui_scope`, `plan_kind`, `plan_mode`, `registry_key`, `parent_epic`, `milestone`, and
the source fields. When `parent_epic` is set, read the parent with `epic-get`; the child's
"Inherited constraints" are locked. Design review may challenge how the child meets them, never
whether they apply.

Read `$DOCS_DIR/REVIEW_CHECKLIST.md`. It holds the project's concrete frontend checks (token
usage, component conventions, render efficiency, accessibility tooling); apply them wherever
pass 5 or pass 6 names the category. The passes themselves stay stack-neutral.

### 2. UI scope gate

From the metadata output, read `ui_scope`. If it is not `true`, stop here and tell the user:

> This plan has no UI scope (`ui_scope` is `<value>`), so a design review does not apply. If
> that is wrong, set it and rerun:
> `"$BIN/obsidian-workflow" plan-metadata-set "$_PLAN_FILE" --set ui_scope=true`

Do not log a review entry and do not sync state; a review that did not run must not appear as
run. Report `DONE` with `CHANGES MADE: none (no UI scope)`, then run the dashboard and next
step per the dashboard block. Never force a design review onto a backend-only change.

### 3. Design-sync drift check (module-gated)

```bash
DESIGN_SYNC=$(python3 -c 'import json,sys; print(str(json.load(open(sys.argv[1])).get("modules",{}).get("design_sync",False)).lower())' "$REPO_ROOT/.agents/config.json")
[ "$DESIGN_SYNC" = "true" ] && "$BIN/design-sync-check"
```

`DESIGN_SYNC` is `false`: skip silently. The prototype path in step 8 is unavailable and
mockups are the artifact route. `true`: interpret the exit code. 0, clean: proceed silently.
1, drift: the watched design files changed since the project's design tool was last synced;
surface the helper's output as a soft warning at the top of your report and continue. 2, no
marker: tell the user to run `"$BIN/design-sync-mark"` to bootstrap, then continue. Never block
on this check; its only job is to make stale state visible.

### 4. System audit

Not the review; the context you need to review intelligently.

```bash
git log --oneline -15
git diff "$BASE_BRANCH" --stat
"$BIN/review-read"
```

Read `AGENTS.md`, then `$DOCS_DIR/FRONTEND_GUIDELINES.md` (tokens, type, spacing, breakpoints,
component patterns, motion, accessibility), `FRONTEND_STRUCTURE.md` (directories, page
ownership, component inventory), `APP_FLOW.md` (screens, routes, flows, error copy), `PRD.md`
(personas), `LESSONS.md`, and `TODOS.md` for design items this plan touches.

Map, and report before Step 0:

- UI scope: the pages, components, and interactions the plan adds or changes.
- Design-system status. `FRONTEND_GUIDELINES.md` present: every decision below is calibrated
  against it. Absent: flag the gap, proceed on universal principles, propose a TODO in step 10.
- Existing patterns and components to reuse.
- Prior design reviews of this plan in the review-read output. A prior `plan-design-review`
  entry makes this a rerun: passes that scored 8 or above get a quick pass, passes below 8 get
  the full treatment.
- Retrospective: the git log for earlier design-review cycles. Areas flagged before are
  reviewed harder now.

### 5. See like a designer

Read `references/designer-eye.md` now. Let its patterns run while you review: simulate the user
(bad signal, one hand free, first time versus the thousandth), see the system rather than the
screen, ask questions before forming opinions, storyboard the arc before judging a layout.

### 6. Step 0: design scope assessment

**0A. Initial rating.** Rate the plan's design completeness 0-10 and say why in one sentence
("a 3: it says what the backend does and never what the user sees"). Say what a 10 looks like
for this plan. Keep the number as `INITIAL_SCORE`.

**0B. Design-system status.** One line, from the audit.

**0C. Existing leverage.** Which patterns, components, and decisions in the codebase the plan
should reuse rather than reinvent.

**0D. Focus areas.** Ask the user (one question): the rating, the three biggest gaps, and
whether to review all seven passes or focus on some. Recommend all seven. Stop until answered.

On an epic, rate the end-state experience and the seams between milestones, not any single
milestone's internals.

### 7. The seven passes

The full rubric per pass, with its tables, is in `references/passes.md`. Read it now. Work one
pass at a time, in order. Each pass follows the rating method:

1. Rate 0-10 on that dimension.
2. Gap: why it is not a 10, traced to a principle.
3. Fix: edit the plan to add what is missing.
4. Re-rate.
5. Ask the user only when a genuine design choice remains; one issue, one question.
6. Fix again. Repeat until 10, or until the user says move on.

| Pass | Question | Leaves behind in the plan |
|---|---|---|
| 1 Information architecture | What does the user see first, second, third? | A hierarchy per screen and an ASCII sketch of structure and navigation |
| 2 Interaction states | Loading, empty, error, success, partial: what does the user see? | The state table, one row per UI feature, written from the user's side |
| 3 User journey and emotional arc | What does the user feel at each step, and what supports it? | The storyboard table; the 5-second, 5-minute, and 5-year horizons |
| 4 AI-slop risk | Is this specific and intentional, or the generic pattern? | Vague UI descriptions rewritten as concrete decisions; `references/design-rules.md` applied |
| 5 Design-system alignment | Does it use the project's tokens and vocabulary? | Token and component annotations; every new component justified against the existing set |
| 6 Responsive and accessibility | What happens at each viewport, on a keyboard, with a screen reader? | Per-viewport layout intent; keyboard patterns, landmarks, 44px targets, contrast |
| 7 Unresolved decisions | What will the implementer guess if the plan stays silent? | The decisions table, each resolved by one question and written into the plan |

Pass 4 loads `references/design-rules.md`: classify the surface (marketing page, app UI,
hybrid), then apply the hard rejection criteria, the litmus checks, the App UI rules, and the
slop blacklist.

After each pass, stop and wait. Rate before and after, for scannability. Never start the next
pass with an issue unresolved.

### Asking about an issue

On top of the shared question format:

- One issue, one question. Describe the gap concretely: what is missing and what the user
  experiences if it stays unspecified.
- Two or three options, one sentence each: effort to specify now (both scales), risk if
  deferred.
- One sentence mapping the recommendation to a named design principle.
- Number issues, letter options: `3A`, `3B`.
- Escape hatch: no issues, say so; obvious fix, state what you are adding and move on. A
  question is for a genuine choice with real tradeoffs.
- If the user does not answer or moves on, record the issue under "Unresolved decisions".
  Never silently default.

### 8. Visual artifacts

Mandatory when non-trivial frontend work is present; never skip it silently. It runs after the
seven passes and before the required outputs, so artifact references land in the plan.
`$PLAN_DIR` is the plan folder from `ctx`; when `_PLAN_FILE` is an explicit path outside it,
use `$(dirname "$_PLAN_FILE")` instead.

**8A. Classify.** Scan the reviewed plan. Non-trivial: a new component, page, or view; a
restructured layout; a new interaction, modal, sheet, or navigation pattern; a change to
information architecture. Trivial: a color, size, or copy change, a single prop, an icon swap,
a spacing nudge. Ask the user (one question) listing each candidate with your classification
and a one-line reason; the user may override per item. If nothing non-trivial remains, write
"No non-trivial frontend work; skipping visual artifacts" and go to step 9.

**8B. Choose the path.** One question per non-trivial item, or one for the batch when the items
are tightly coupled. Present the recommendation from this table:

| Path | Recommend when | Effort |
|---|---|---|
| A) Prototype in the project's design tool | New page or view, a flow with several screens, open IA decisions, a new interaction or navigation pattern, multi-component layout changes | ~30-60 min |
| B) HTML mockups | One new component on an existing page, settled IA, a reshaped existing component, wanting two or three options for one element | ~5 min |
| C) No artifact | Behavior-only change with no layout impact; the plan's text is enough | 0 min |

Offer path A only when `DESIGN_SYNC` is `true`. Otherwise omit it and say in one line that the
design-sync module is off, so mockups are the artifact route. On an epic, the artifact covers
the end-state flow; each child plan produces its own component-level artifacts.

**8C-A. Prototype loop.** Read `references/prototype-brief.md`. Re-run
`"$BIN/design-sync-check"`; on drift, ask the user (one question) whether to pause and re-sync
the design tool from the watched files, then run `"$BIN/design-sync-mark"` and resume
(recommended), or proceed and record `stale (drift accepted)`. Write the brief from the
template, quoting the passes verbatim, and print it; the user takes it to the design tool
themselves. Never call a web service for this. Then ask the user (one question) to paste the
handoff URL when the prototype is ready, or `skip`.

On a URL: `mkdir -p "$PLAN_DIR/prototype"`, have the user unzip the exported handoff bundle
there, verify with `ls "$PLAN_DIR/prototype/" | head -5`; if empty, ask (one question) to retry
or fall back to path B. Capture the URL, the handoff prompt from the bundle's README, and the
pin SHA from 8E. The offline bundle is required: it is the baseline `/execute-plan` and
`/review-implementation` compare against. The live URL is a convenience.

On `skip`: write `**Prototype:** DEFERRED, to be captured before /execute-plan runs` into the
Design Source of Truth section and continue with step 9.

**8C-B. HTML mockups.** Read `references/mockup-rules.md`. For each non-trivial component:

1. Web search on generalized category terms, never project names: `"<component type> design
   patterns <year>"`, `"<component type> UX approaches"`, `"alternatives to <conventional
   pattern>"`. Summarize two to four bullets of distinct approaches before generating. If
   search is unavailable, say so and proceed with in-distribution knowledge.
2. `mkdir -p "$PLAN_DIR/mockups"`.
3. Generate at least three options. Use a frontend-design skill if your harness provides one
   (invoke it per the tool map); otherwise write the HTML yourself.
4. Diversity: options differ in layout, interaction pattern, or information architecture, not
   merely in color, type, or spacing. Regenerate any option that differs only cosmetically.
5. Context: render each option in its real page context (navigation shell, siblings, chrome)
   using the project's tokens from `FRONTEND_GUIDELINES.md`, so only the thing being designed
   varies between options.
6. Save as `$PLAN_DIR/mockups/<component-slug>-option-<a|b|c|...>.html`, the slug lowercase
   and hyphenated from the plan's component name.
7. Present per component, one question each: the file path plus a one-line description of the
   distinguishing structural choice for every option. Iterate (regenerate, adjust, add options)
   until exactly one option per component is selected. Do not proceed before that.

**8C-C. No artifact.** Ask the user (one question) for a one- or two-sentence rationale
("behavior-only change, no layout impact"). Record it for 8E.

**8D. Consistency check** (paths A and B). Compare each selected artifact with the plan: fields
or actions the plan does not mention; IA against pass 1; states against pass 2; responsive and
accessibility against pass 6. Path A checks the offline bundle's entry point, never the live
URL; fixes are plan-side because the prototype is final (a wrong prototype is re-exported by
the user). Path B fixes either side, regenerating the mockup when the plan is right. Ambiguous
cases: ask the user (one question) which wins. Note each fix inline.

**8E. Wire the plan.** Read `references/design-source-of-truth.md` and add or update
`## Design Source of Truth` near the top of the plan body, after the problem statement and
constraints and before per-component sections. Update it in place on a rerun. Every non-trivial
item from 8A is accounted for. The design-system pin SHA:

```bash
DESIGN_PIN_SHA=$("$BIN/design-sync-check" --pin-sha) && echo "Design pin: $DESIGN_PIN_SHA"
```

Never build the path list in shell: zsh does not word-split an unquoted variable, so a joined
list matches nothing and git prints an empty SHA with exit 0. A non-zero exit from the helper
means there is no SHA; show its message and resolve it before writing the section, never record
an empty pin. If `design_watched_files` is empty, pass `$DOCS_DIR/FRONTEND_GUIDELINES.md` and
the token source file it names as arguments after `--pin-sha`. Downstream skills compare
against the same list; use the same one.

**8F. Cleanup.** Path B: delete every unselected file in `$PLAN_DIR/mockups/`, keep only the
chosen options, report the counts ("kept 3, deleted 6"). Path A: list `$PLAN_DIR/prototype/`
and ask whether anything is an obsolete iteration; never auto-delete. If both folders exist
because the plan graduated from mockups to a prototype, keep both; the Design Source of Truth
section says which is current and the other is history. Say so inline.

### 9. Required outputs

Write each into `_PLAN_FILE`:

- **NOT in scope.** Design decisions considered and deferred, one-line rationale each.
- **What already exists.** Guidelines, patterns, and components the plan reuses, from 0C.
- **Unresolved decisions.** By issue number, never defaulted.

### 10. TODOS and lessons

For design debt (missing accessibility, unresolved responsive behavior, deferred empty states,
an absent `FRONTEND_GUIDELINES.md`), write to `$DOCS_DIR/TODOS.md` in the format its own header
defines. One question per TODO, never batched, never skipped silently: A) add to TODOS.md,
B) skip, not valuable enough, C) build it now in this plan. Any first-principles design insight
goes to `$DOCS_DIR/LESSONS.md` under `## Decisions`.

### 11. Fold decisions, footer, test artifact

Per the plan-footer block: edit `_PLAN_FILE` in place, one targeted edit per decision, with a
`Design review N: decision` breadcrumb. Preserve every frontmatter key. Update the Design Review
row of the REVIEW REPORT with a one-line findings summary; if the plan lacks the footer, add it
from the shared template.

When `$TEST_ARTIFACT` exists and a pass added user-visible states, viewports, or accessibility
requirements the artifact does not list, append them to its interactions and edge cases with a
one-line breadcrumb naming this skill. Surgical additions only; never restructure it.

### 12. Completion summary

Fill in the box from `references/completion-summary.md` (audit, Step 0, before and after score
per pass, artifact path and coverage, outputs, TODOS, decisions made and deferred, overall
score) and present it. The overall score after fixes is `OVERALL_SCORE`; count decisions added
to the plan as `DECISIONS_MADE` and open ones as `UNRESOLVED`.

## Completion

Report exactly one status from the completion protocol, with the change description. Sync
state per the obsidian-sync block with `STATUS_VALUE=design-reviewed` and
`REVIEW_VALUE=design-reviewed`; `BLOCKED` and `NEEDS_CONTEXT` set `implementation_status` and
`reason` only.

```bash
"$BIN/review-log" --skill plan-design-review --status "$STATUS" \
  --field initial_score="$INITIAL_SCORE" --field overall_score="$OVERALL_SCORE" \
  --field decisions_made="$DECISIONS_MADE" --field unresolved="$UNRESOLVED"
```

`STATUS` is `clean` when `OVERALL_SCORE` is 8 or above and `UNRESOLVED` is zero, otherwise
`issues_open`. Add `--field model=<name>` when you know which model you are.

Then:

```bash
"$BIN/workflow-state" --dashboard
"$BIN/workflow-state" --next
```

Present both per the dashboard block. If the passes materially changed interactions, state
handling, or information architecture, say so in one line so the user can decide whether eng
review or adversarial review should look again; do not list next steps yourself. After
implementation, `/design-review` audits the live pages against this plan's artifacts; the
dashboard lists it when it is due.
