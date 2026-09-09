# Surface classifier, hard rules, and AI slop

The rule set depends on what the visitor's win looks like on this surface, not on what the
product is. Name the mode before judging a pixel. The blacklist below is the same list
`/plan-design-review` applies at plan stage, so a plan that passed there and a page that fails
here point at the implementation, not at a moving target.

## Classifier

| Mode | Surface | The visitor's win | Rule set |
|---|---|---|---|
| **PERSUADE** | marketing and landing pages, pricing, campaigns: hero-driven, brand-forward | they decide and act; design is the product | Landing page rules |
| **OPERATE** | app UI: dashboards, admin, settings, editors, tools: workspace-driven, data-dense, task-focused | they finish a task; scanability and native expectations beat expression; the brand lives in the details | App UI rules |
| **READ** | docs, articles, guides, changelogs | they understand something; structure for comprehension, then make staying worth it | Read rules |
| **EXPERIENCE** | portfolios, galleries, showcases | they are inside the work; the artifact owns the first viewport | Experience rules |
| **HYBRID** | a marketing shell with app-like sections | classify per section, not per page | the matching set per section |

A dev tool's landing page is PERSUADE. A fashion house's docs are READ.

## Hard rejection criteria (instant fail, flag if any apply)

1. Generic SaaS card grid as the first impression
2. Beautiful image with weak brand
3. Strong headline with no clear action
4. Busy imagery behind text
5. Sections repeating the same mood statement
6. Carousel with no narrative purpose
7. App UI made of stacked cards instead of layout

## Litmus checks (answer YES or NO for each)

1. Brand or product unmistakable in the first screen?
2. One strong visual anchor present?
3. Page understandable by scanning headlines only?
4. Each section has one job?
5. Are cards actually necessary?
6. Does motion improve hierarchy or atmosphere?
7. Would the design feel premium with every decorative shadow removed?

## Landing page rules (PERSUADE)

- The first viewport reads as one composition, not a dashboard
- Brand-first hierarchy: brand, then headline, then body, then call to action
- Typography expressive and purposeful; no default stacks as the display voice
- No flat single-color background by default: texture from the brand or a real asset, never a
  halo, spotlight, stripe, or grid-paper gradient
- Hero full-bleed, edge to edge; no inset, tiled, or rounded variants
- Hero budget: brand, one headline, one supporting sentence, one call-to-action group, one image
- No cards in the hero; cards only when the card is the interaction
- One job per section: one purpose, one headline, one short supporting sentence
- Motion: one authored moment on the first viewport, ease-out from a visible default; hover
  states only where they carry information
- Color: variables defined, no purple-on-white defaults, one accent by default
- Copy: product language, not design commentary. "If deleting 30% improves it, keep deleting"
- Composition first, brand as the loudest text, two text faces at most (plus a mono for data
  and code), cardless by default, display type under 6 rem

## App UI rules (OPERATE)

- Calm surface hierarchy, strong typography, few colors
- Dense but readable, minimal chrome
- Organize as primary workspace, navigation, secondary context, one accent
- Avoid dashboard-card mosaics, thick borders, decorative gradients, ornamental icons
- Copy is utility language: orientation, status, action. Not mood, brand, or aspiration
- Cards only when the card is the interaction
- Section headings state what the area is or what the user can do ("Selected KPIs", "Plan status")

## Read rules (READ)

- Measure 65–75 characters, one reading column, headings closer to what follows than to what
  precedes
- Wayfinding is a feature: where am I, what is next, where do I search
- A docs index is READ, not PERSUADE: no hero, no call-to-action theater

## Experience rules (EXPERIENCE)

- The work fills the first viewport; chrome earns every pixel
- One authored transition, not a scroll-jacked tour
- Never crop the artifact to fit a template

## Universal rules (every mode)

- Variables define the color system
- No default font stacks as the display voice (Inter, Roboto, Arial, system); body and UI use
  on an OPERATE or READ surface passes when the guidelines say so
- One job per section
- "If deleting 30% of the copy improves it, keep deleting"
- Cards earn their existence; no decorative card grids
- Never small, low-contrast type: body under 16 px or under 4.5:1 on body text
- Never a placeholder as the only label; labels stay visible when the field has content
- Always preserve the visited versus unvisited link distinction
- Never float a heading between paragraphs; it sits closer to what it introduces

## The AI slop blacklist (the patterns that scream "generated")

Shared with `/plan-design-review`. Items 1–10 are the plan-stage list; item 11 is the
rendered-page addition.

1. Purple, violet, or indigo gradient backgrounds, or blue-to-purple color schemes
2. **The three-column feature grid:** icon in a colored circle, bold title, two-line
   description, repeated three times symmetrically. The most recognizable generated layout
3. Icons in colored circles as section decoration (the starter-template look)
4. Centered everything: `text-align: center` on every heading, description, and card
5. Uniform bubbly border radius on every element
6. Decorative blobs, floating circles, wavy dividers. An empty-feeling section needs better
   content, not decoration
7. Emoji as design elements: rockets in headings, emoji as bullets
8. Colored left border on cards (`border-left: 3px solid <accent>`)
9. Generic hero copy: "Welcome to [X]", "Unlock the power of…", "Your all-in-one solution for…"
10. Cookie-cutter section rhythm: hero, three features, testimonials, pricing, call to action,
    every section the same height
11. A system font stack as the primary display or body face: the "I gave up on typography"
    signal. Pick a real typeface

The plan-stage prompts still apply to the rendered page: "cards with icons" asks what
separates these from every template; "hero section" asks what makes this hero feel like this
product; "clean, modern UI" is meaningless until replaced by decisions; "dashboard with
widgets" asks what makes this not every other dashboard.

## Mechanical patterns (name them by id in findings)

`[border-accent-on-rounded]` accent border on a rounded card · `[overused-font]` overused
display face · `[flat-type-hierarchy]` · `[gradient-text]` · `[cream-palette]` cream default
palette · `[nested-cards]` · `[shape-assembled-illustration]` · `[dark-glow]` dark-mode glow ·
`[radial-halo]` · `[radial-spotlight-glow]` · `[marquee]` logo marquee · `[icon-tile-stack]`
icon tile above every heading · `[italic-serif-display]` · `[hero-eyebrow-chip]` ·
`[kicker-above-heading]` · `[marketing-buzzword]` · `[aphoristic-cadence]` · `[oversized-h1]` ·
`[theater-slop-phrase]`.

One element hit by a mechanical pattern and a judgment tell is one finding.

## Judgment tells (you are the detector)

- Gradient buttons as the primary call to action. One solid color the palette owns
- A generic stock-photo hero, or a gray placeholder standing in for one. Show the product or
  show nothing
- Rounded cards with drop shadows as the container for everything. Stacked cards are not layout
- A testimonial row with avatars, five stars, and quotes nobody said. Real names with real
  claims, or cut it
- The cookie-cutter hero: headline left, screenshot right, two buttons
- "Get Started" and "Learn More" as the only calls to action. Name the outcome the click buys
- Three big numbers with tiny labels under the hero ("10k+ users", "99.9%")
- A grid of cards with the same shape, the same icon slot, the same two lines: content of
  unequal weight given equal boxes
- Frosted-glass panels with blurred backdrops as the default surface
- Generated doodles and mascots in place of art direction. Commission or license, or ship none
- Every secondary action in a modal. Inline, a side panel, or a page usually costs less
- Sparklines, progress rings, and fake avatars filling space where content should be
- Dark because it is a dev tool, light because it is health. Light or dark comes from the use
  scene: who, where, under what light
- Only the happy path designed. Empty, loading, error, and long-content states are part of the
  component
- Cards only when the card is the interaction; everywhere else, layout
- Hover effects on everything and the same entrance on every section

## Polish-level tells (note, do not grade)

`[monotonous-spacing]`, `[bounce-easing]`, `[pulsing-dot]`, `[blinking-cursor]`,
`[numbered-section-labels]`, `[em-dash-overuse]`, `[extreme-negative-tracking]`,
`[thin-border-wide-shadow]`, `[repeating-stripes-gradient]`, `[grid-paper-background]`,
`[image-hover-transform]`, monospace as costume, unthemed browser surfaces.

## Calibration: the three looks

Generated interfaces land in one of three looks whatever the product: (1) cream ground,
high-contrast serif display, terracotta or signal-red accent; (2) near-black, one neon accent,
glowing edges; (3) broadsheet hairlines, italic display serif, tiny tracked mono labels. Each
is fine when the brief asked for it. If the brief left the look open and the page landed in one
anyway, somebody stopped looking. The test: could a stranger guess the look from the product
category alone, or from "the category, but avoiding the obvious"? Either way it fails. "It's
about books, so cream and a serif" fails. Book cloth and jackets come in every saturated color.

## The AI Slop Grade

Graded independently of the design grade, from this file only, with a one-line verdict:

- **A** nothing on the blacklist, no judgment tells, a look that could only be this product
- **B** one or two polish-level tells; the look is chosen, not defaulted
- **C** one blacklist item or two judgment tells; the look could be guessed from the category
- **D** several blacklist items; a template with the product's name on it
- **F** a hard rejection criterion applies, or the three-column feature grid is the first
  impression
