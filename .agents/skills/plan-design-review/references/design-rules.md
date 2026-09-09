# Design hard rules and the slop blacklist

Loaded by `plan-design-review` in pass 4. Classify first; the rule set depends on the surface.

## Classifier

- **Marketing or landing page**: hero-driven, brand-forward, conversion-focused. Apply the
  landing-page rules: the hard rejection criteria and the litmus checks.
- **App UI**: workspace-driven, data-dense, task-focused (dashboards, admin, settings,
  editors). Apply the App UI rules, plus the hard rejection criteria that name app UI.
- **Hybrid**: a marketing shell with app-like sections. Landing-page rules for the hero and
  marketing sections, App UI rules for the functional ones.

## Hard rejection criteria

Instant-fail patterns. Flag if any applies to what the plan describes:

1. A generic SaaS card grid as the first impression.
2. A beautiful image with a weak brand.
3. A strong headline with no clear action.
4. Busy imagery behind text.
5. Sections repeating the same mood statement.
6. A carousel with no narrative purpose.
7. App UI made of stacked cards instead of a layout.

## Litmus checks

Answer yes or no for each; a no is a finding:

1. Is the brand or product unmistakable in the first screen?
2. Is there one strong visual anchor?
3. Is the page understandable by scanning headlines only?
4. Does each section have one job?
5. Are the cards actually necessary?
6. Does motion improve hierarchy or atmosphere?
7. Would the design still feel premium with every decorative shadow removed?

## App UI rules

- Calm surface hierarchy, strong typography, few colors.
- Dense but readable; minimal chrome.
- Organize as: primary workspace, navigation, secondary context, one accent.
- Avoid dashboard-card mosaics, thick borders, decorative gradients, ornamental icons.
- Copy is utility language: orientation, status, action. Not mood, brand, or aspiration.
- Cards only when the card is the interaction.
- Section headings state what the area is or what the user can do there ("Selected KPIs",
  "Plan status").

## Universal rules

- Define the color system as CSS variables, or through the token mechanism
  `FRONTEND_GUIDELINES.md` names.
- One job per section.
- "If deleting 30% of the copy improves it, keep deleting."
- Cards earn their existence; no decorative card grids.

## The AI-slop blacklist

The ten patterns that read as generated:

1. Purple, violet, or indigo gradient backgrounds, or blue-to-purple color schemes.
2. **The three-column feature grid**: icon in a colored circle, bold title, two-line
   description, repeated three times symmetrically. The most recognizable generated layout.
3. Icons in colored circles as section decoration (the starter-template look).
4. Everything centered: headings, descriptions, cards.
5. Uniform bubbly border radius on every element.
6. Decorative blobs, floating circles, wavy dividers. A section that feels empty needs better
   content, not decoration.
7. Emoji as design elements: in headings, as bullets.
8. A colored left border on cards.
9. Generic hero copy: "Welcome to X", "Unlock the power of", "Your all-in-one solution for".
10. Cookie-cutter section rhythm: hero, three features, testimonials, pricing, call to action,
    every section the same height.

## Vague phrases and the question that replaces them

| The plan says | Ask, then write the answer into the plan |
|---|---|
| "Cards with icons" | What differentiates these from every template? |
| "Hero section" | What makes this hero feel like this product? |
| "Clean, modern UI" | Meaningless. Which type scale, spacing step, and interaction pattern? |
| "Dashboard with widgets" | What makes this not every other dashboard? |
| "Standard form" | Which fields, in which order, with which validation and error copy? |
| "Responsive" | What changes at each named breakpoint? |
