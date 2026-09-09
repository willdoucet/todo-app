# Prototype brief

Loaded by `plan-design-review` at step 8C-A, only when `modules.design_sync` is `true` in
`.agents/config.json`. The brief is a copy-pasteable prompt the user takes to the project's
design tool. Print it to chat; never call a web service. One brief per non-trivial item, or
one for a tightly coupled batch.

## Pre-flight

Run `"$BIN/design-sync-check"` again. On drift (exit 1), ask the user (one question):

- A) Pause prototyping: re-sync the design tool from the watched design files now, run
  `"$BIN/design-sync-mark"`, then resume here. Recommended; it prevents stale tokens in the
  prototype.
- B) Proceed anyway, accepting that the prototype may be built on a stale design system, to be
  reconciled in 8D. Record `**Sync state at capture:** stale (drift accepted)` in the plan.

## The brief

Every section below is required. Quote the plan's passes verbatim; do not summarize them.

```markdown
# Prototype brief: <component or flow name>

## Purpose
<the component's purpose, from the plan>

## Information architecture (pass 1, verbatim)
<hierarchy per screen and the navigation sketch>

## Interaction states (pass 2, verbatim)
<the loading / empty / error / success / partial table>

## User journey (pass 3, relevant rows)
<the storyboard rows this component participates in>

## Responsive intent (pass 6)
<per-viewport layout intent at the guidelines' breakpoints>

## Accessibility (pass 6)
<keyboard patterns, landmarks and roles, 44px targets, contrast, reduced motion, announcements>

## Design system
Use the project's published design system in the design tool. Tokens come from
$DOCS_DIR/FRONTEND_GUIDELINES.md.

## Do not produce
Centered-everything three-column feature grids, indigo or violet gradients, icon-in-colored-
circle decoration, decorative card grids, or any other pattern on the slop blacklist.
```

## After the user prototypes

Ask the user (one question) to paste the handoff URL, or `skip`.

On a URL:

1. `mkdir -p "$PLAN_DIR/prototype"`.
2. Ask the user to download the handoff bundle from the design tool and unzip it into
   `$PLAN_DIR/prototype/`, then confirm.
3. Verify: `ls "$PLAN_DIR/prototype/" | head -5`. Empty: ask (one question) to retry or fall
   back to HTML mockups.
4. Capture for 8E: the handoff URL, the handoff prompt (one line, from the bundle's README),
   the design-system pin SHA, and the sync state at capture.

The offline bundle is required. It is the durable baseline `/execute-plan` reads and
`/review-implementation` compares against; the live URL is a convenience that may expire.

On `skip`: mark the section `**Prototype:** DEFERRED, to be captured before /execute-plan
runs`. The plan can still go to `/execute-plan`; the implementer will work without prototype
context, and the completion summary says so.
