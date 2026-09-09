# Design audit checklist

Applied on every page in scope, at every viewport captured. Each finding gets an impact
(high, medium, polish) and one category. Values that `$DOCS_DIR/FRONTEND_GUIDELINES.md`
blesses are never findings; departures from it name the token. Measurable items name the
evaluate probe in `browser-procedures.md`.

## Trunk test (every page)

Imagine being dropped onto this page with no context. Can you immediately answer:

1. What site is this? (site identity visible and recognizable)
2. What page am I on? (page name prominent, matching what was clicked)
3. What are the major sections? (primary navigation visible and clear)
4. What are my options at this level? (local navigation or content choices obvious)
5. Where am I in the whole? ("you are here" marker, breadcrumbs)
6. How can I search? (findable without hunting, when the app has search)

Score **PASS** (all six clear), **PARTIAL** (four or five), **FAIL** (three or fewer). A FAIL
is a high-impact finding regardless of visual polish.

## 1. Visual hierarchy and composition (8)

- One clear focal point; one primary call to action per view
- The eye flows naturally top-left to bottom-right
- No visual noise: no competing elements fighting for attention
- Information density fits the content type
- Stacking clarity: nothing unexpectedly overlapping
- Above the fold, the purpose reads in three seconds
- Squint test: hierarchy survives blurring
- White space is intentional, not leftover

## 2. Typography (15)

- At most three font families
- Scale follows a ratio (1.25 major third or 1.333 perfect fourth)
- Line height about 1.5 for body, 1.15–1.25 for headings
- Measure 45–75 characters per line (66 ideal)
- Heading hierarchy without skipped levels (no h1 to h3)
- At least two weights used for hierarchy
- No banned faces (Papyrus, Comic Sans, Lobster, Impact, Jokerman, Bleeding Cowboys, Permanent
  Marker, Bradley Hand, Brush Script, Hobo, Trajan, Raleway, Clash Display, Courier New)
- Display face on the overused list (Inter, Roboto, Arial, Helvetica, Open Sans, Lato, and
  the system stacks) is flagged `[overused-font]`; as body or UI text on an OPERATE or READ
  surface it passes when the guidelines say so
- `text-wrap: balance` or `pretty` on headings (probe the computed style of `h1`)
- Curly quotes, not straight quotes
- The ellipsis character, not three dots
- `font-variant-numeric: tabular-nums` on number columns
- Body text at least 16 px
- Captions and labels at least 12 px
- No letter-spacing on lowercase text

## 3. Color and contrast (10)

- Coherent palette: at most 12 unique non-gray colors
- WCAG AA: body text 4.5:1, large text (18 px and up) 3:1, UI components 3:1
- Semantic colors consistent (success green, error red, warning amber)
- No color-only encoding: labels, icons, or patterns alongside
- Dark mode: surfaces use elevation, not a lightness inversion
- Dark mode: text off-white, not pure white
- Primary accent desaturated 10–20% in dark mode
- `color-scheme: dark` on the root when dark mode exists
- No red-and-green-only pairs (8% of men have red-green deficiency)
- Neutral palette consistently warm or cool, not mixed

## 4. Spacing and layout (12)

- Grid consistent at every breakpoint
- Spacing on a scale (4 or 8 px base), not arbitrary values
- Alignment consistent: nothing floating off the grid
- Rhythm: related items closer, distinct sections further apart
- Border-radius hierarchy, not one bubbly radius on everything
- Inner radius equals outer radius minus the gap on nested elements
- No horizontal scroll on mobile
- Maximum content width set: no full-bleed body text
- `env(safe-area-inset-*)` respected on notched devices
- URL reflects state: filters, tabs, pagination in the query string
- Flex or grid for layout, not script measurement
- Breakpoints present at mobile (375), tablet (768), desktop (1024), wide (1440), or the set
  the guidelines document

## 5. Interaction states (12)

- Hover state on every interactive element
- `focus-visible` ring present; never `outline: none` without a replacement
- Active or pressed state with depth or color shift
- Disabled state: reduced opacity plus `cursor: not-allowed`
- Loading: skeleton shapes match the real content layout
- Empty states: warm message plus primary action plus a visual, not "No items."
- Error messages specific, with the fix or next step
- Success: confirmation animation or color, auto-dismissed
- Touch targets at least 44 px
- `cursor: pointer` on everything clickable
- Mindless-choice audit: every decision point (button, link, menu, modal choice) is a
  mindless click. A choice that requires thought is a high-impact finding
- Browser surfaces themed from the palette: `::selection`, caret, scrollbars, focus ring,
  underline offset, tabular numerals. Left at defaults, the page reads as assembled

## 6. Responsive design (8)

- The mobile layout makes design sense; it is not stacked desktop columns
- Touch targets sufficient on mobile (44 px)
- No horizontal scroll at any viewport
- Images responsive (`srcset`, `sizes`, or CSS containment)
- Text readable without zooming (16 px body)
- Navigation collapses appropriately (hamburger, bottom bar)
- Forms usable on mobile: correct input types, no autofocus
- No `user-scalable=no` or `maximum-scale=1` in the viewport meta

## 7. Motion and animation (7)

- Easing: ease-out entering, ease-in exiting, ease-in-out moving
- Duration 50–700 ms; nothing slower except page transitions
- Purpose: every animation communicates a state change, attention, or spatial relationship
- `prefers-reduced-motion` respected (probe `matchMedia`)
- No `transition: all`; properties listed explicitly
- Only `transform` and `opacity` animated, never layout properties
- One authored motion moment per page: not the same entrance on every section, not a hover
  effect on everything; ease-out from an already visible default; content never hides behind
  animation timing

## 8. Content and microcopy (11)

- Empty states designed with warmth: message, action, illustration or icon
- Error messages: what happened, why, what to do next
- Button labels specific ("Save API key", not "Continue" or "Submit")
- No placeholder or lorem ipsum text
- Truncation handled (`text-overflow: ellipsis`, `line-clamp`, or `break-words`)
- Active voice ("Install the CLI", not "The CLI will be installed")
- Loading states end with the ellipsis character ("Saving…")
- Destructive actions have a confirmation or an undo window
- Happy-talk detection: introductory paragraphs starting "Welcome to…" or telling users how
  great the product is. If you can hear "blah blah blah", flag it for removal
- Instructions detection: any visible instructions longer than one sentence. Flag the
  instructions and the interaction they compensate for
- Happy-talk count: total visible words on the page; classify each block useful or happy
  talk; report "This page has X words; Y (Z%) are happy talk."

## 9. AI slop detection

The full blacklist, judgment tells, and mode rules are in `ai-slop.md`. Grade this category
against that file; do not re-derive it here. The test: would a human designer at a respected
studio ship this?

## 10. Performance as design (6)

- LCP under 2.0 s for web apps, under 1.5 s for informational sites (probe in the page)
- CLS under 0.1: no visible layout shifts during load (probe in the page)
- Skeleton quality: shapes match the real content, shimmer animation
- Images: `loading="lazy"`, width and height set, modern formats
- Fonts: `font-display: swap`, preconnect to font origins
- No visible font swap flash; critical fonts preloaded

## Reflexes no probe catches (check by hand, every page)

- **Depth has an offset.** Shadows are offset plus soft blur. A zero-offset colored halo is
  decoration, not depth.
- **Secondary text on a colored surface is tinted from that hue.** Never gray.
- **More space above a heading than below it.** Read the computed values.
- **Light or dark comes from the use scene.** Who, where, under what light: one sentence.
  Never from the product category.
