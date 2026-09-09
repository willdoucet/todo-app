# Issue taxonomy

Severity, categories, and the per-page exploration checklist for `/qa`. Every documented issue
carries exactly one severity and one primary category; the health-score rubric depends on
both being assigned consistently.

## Severity

Use the highest applicable level. Record the impact and any workaround in the issue.

| Severity | Definition | Examples |
|---|---|---|
| **critical** | Data loss, security or privacy exposure, or a core workflow unusable for all users | form submit lands on an error page, checkout broken, data deleted without confirmation |
| **high** | A core or major task is blocked with no workaround | search returns wrong results, upload silently fails, auth redirect loop |
| **medium** | The task is impaired but a workaround exists | slow page (over 5 s), validation missing but submit still works, layout broken on mobile only |
| **low** | Cosmetic, copy, or friction without lost task completion | typo in the footer, one-pixel misalignment, inconsistent hover state |

Tiers: Quick fixes critical and high; Standard adds medium; Exhaustive adds low.

## Categories

Assign one primary category per root cause, the first that applies in this order: Links,
Accessibility, Functional, Performance, Visual, Content, UX, Console. The same root cause seen
on several pages is one issue.

### Visual
- Layout breaks: overlapping elements, clipped text, unexpected horizontal scrollbar
- Broken or missing images
- Wrong stacking: elements appearing behind others
- Font and color inconsistencies against the rest of the app
- Animation glitches: jank, incomplete transitions
- Alignment: off-grid, uneven spacing
- Dark mode or theme problems

### Functional
- Broken links: 404, wrong destination
- Dead buttons: click does nothing
- Form validation missing, wrong, or bypassable
- Incorrect redirects
- State not persisting: data lost on refresh or back
- Race conditions: double submit, stale data after an action
- Search returning wrong or no results

### UX
- Confusing navigation: no breadcrumbs, dead ends, no way back
- Missing loading indicators; the user cannot tell something is happening
- Slow interactions: over 500 ms with no feedback
- Unclear error messages: "Something went wrong" with no detail or next step
- No confirmation before destructive actions
- Inconsistent interaction patterns across pages

### Content
- Typos and grammar
- Outdated or incorrect text
- Placeholder or lorem ipsum text left in
- Truncated text without an ellipsis or a "more" affordance
- Wrong labels on buttons or fields
- Missing or unhelpful empty states

### Performance
- Slow page loads: over 3 s
- Janky scrolling: dropped frames
- Layout shifts: content jumping after load
- Excessive requests: over 50 on one page
- Large unoptimized images
- Blocking scripts: the page unresponsive during load

### Console
- Uncaught exceptions
- Failed network requests: 4xx, 5xx
- Deprecation warnings that predict breakage
- Cross-origin errors
- Mixed content: insecure resources on a secure page
- Content-security-policy violations

### Accessibility
- Missing alt text on meaningful images
- Unlabeled form inputs
- Keyboard navigation broken: cannot tab to a control
- Focus traps: cannot escape a modal or menu
- Missing or incorrect ARIA attributes
- Insufficient color contrast
- Content unreachable by a screen reader

### Links
- Repeatable 4xx or 5xx destinations, including client-side routes
- Missing routes or anchors
- Timeouts

## Per-page exploration checklist

For every page in scope, in this order:

1. **Visual scan.** Read the page (see `browser-procedures.md`) and look at the screenshot for
   layout issues, broken images, alignment.
2. **Interactive elements.** Click every button, link, and control. Does each do what it says?
3. **Forms.** Fill and submit (non-local target: consent first). Empty submission, invalid
   data, edge cases: very long text, special characters, boundary values.
4. **Navigation.** Every path in and out: breadcrumbs, back button, deep links, mobile menu.
5. **States.** Empty, loading, error, full or overflow. Long titles, many items, no items.
6. **Console.** Record `CONSOLE_ERRORS=` and `NETWORK_FAILURES=` after each interaction.
7. **Responsiveness.** Mobile viewport when layout or touch matters; tablet when the project
   documents that breakpoint.
8. **Auth boundaries.** Never sign the user out or switch accounts. If the signed-out or
   other-role view matters, ask the user to switch and re-run the page.

Quick mode skips the checklist: loads, console errors, broken links visible, nothing else.

## Stack-specific checks

The project's concrete checks are in `$DOCS_DIR/REVIEW_CHECKLIST.md`. Apply every browser-relevant
entry and cite it; `browser-procedures.md` lists the stack-neutral categories those entries fall
into.
