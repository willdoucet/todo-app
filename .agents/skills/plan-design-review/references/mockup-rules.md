# HTML mockup rules

Loaded by `plan-design-review` at step 8C-B. Mockups are the artifact route whenever the
design-sync module is off, and the right route for a single component on a settled page.

## Generation

Use a frontend-design skill if your harness provides one, invoked per the tool map; it tends
to produce more distinctive work than a plain prompt. Otherwise write the HTML yourself,
self-contained (inline styles or a style block, no build step), so each file opens directly in
a browser from `$PLAN_DIR/mockups/`.

Before generating, run the web searches on generalized category terms and summarize two to
four distinct approaches per component. Those approaches seed the options. The search is for
what everyone does and why, so you can pick the ones worth showing and notice the one nobody
has tried.

## Diversity (enforced)

At least three options per component. More is fine. The options must differ in **layout,
interaction pattern, or information architecture**, never only in color, type, or spacing. A
good spread reads like "sidebar-driven / top-nav modal / inline expansion", not "blue / green /
gray". If two options differ only cosmetically, regenerate one of them with a structurally
different approach before presenting anything.

## Contextual framing (enforced)

Show each option in its real page context, never in isolation. The only thing that varies
between options is the thing being designed; everything else (surrounding components, page
chrome, navigation, sibling sections) stays constant, so the user judges the change against
the whole page.

- A new component on an existing page: render the full page with the existing components in
  place and the new one where it will actually live. The rest should look like the current
  site.
- A modified existing component: render the page or section with every other component
  unchanged, so only the target differs between options and against the current site.
- A new standalone page or view: render it inside the app's navigation shell and chrome as it
  will exist.
- Reuse the project's tokens, typography, spacing, and component styles from
  `$DOCS_DIR/FRONTEND_GUIDELINES.md` and the existing components listed in
  `FRONTEND_STRUCTURE.md`, so the surrounding UI matches the real app. A mockup should feel
  like a screenshot of the real site with one thing changed, not a generic design demo.

## Naming

`$PLAN_DIR/mockups/<component-slug>-option-<letter>.html`, the slug lowercase and hyphenated
from the component name in the plan; letters `a`, `b`, `c`, and onward.

## Presenting

One question per component. For each option: the file path, so the user can open it, and one
line naming its distinguishing structural choice. The user may pick one, ask for changes to
one, ask questions, or ask for more options. Iterate until exactly one option per component is
selected. Do not move on with a component unselected.

## Cleanup

After selection, delete every unselected file under `$PLAN_DIR/mockups/`. Keep only the chosen
options and report the counts. The selected files are referenced from the plan's Design Source
of Truth section, read by `/execute-plan`, and compared against by `/review-implementation`.
