# UX principles: how users actually behave

Observed behavior, not preference. Apply before, during, and after every design judgment in
`/design-review`. The goodwill reservoir at the end is the scoring instrument for journeys.

## The three laws of usability

1. **Don't make me think.** Every page should be self-evident. If a user stops to ask "what
   do I click?" or "what does this mean?", the design has failed. Self-evident beats
   self-explanatory beats requires-explanation.
2. **Clicks don't matter, thinking does.** Three mindless, unambiguous clicks beat one click
   that requires thought. Each step should feel like an obvious choice, not a puzzle.
3. **Omit, then omit again.** Remove half the words on a page, then half of what is left.
   Happy talk (self-congratulation) must go. Instructions must go. If it needs reading, the
   design has failed.

## How users behave

- **They scan, they don't read.** Design for scanning: prominence equals importance, clearly
  defined areas, headings and lists, highlighted key terms. Billboards at speed, not
  brochures to be studied.
- **They satisfice.** They pick the first reasonable option, not the best. Make the right
  choice the most visible one.
- **They muddle through.** They wing it. If they reach the goal by accident they will not
  look for the right way, and once something works, however badly, they keep doing it.
- **They don't read instructions.** They dive in. Guidance must be brief, timely, and
  unavoidable, or it is never seen.

## Billboard design for interfaces

- **Use conventions.** Logo top-left, navigation top or left, search is a magnifying glass.
  Innovate on navigation only when you know you have a better idea.
- **Visual hierarchy is everything.** Related things grouped; nested things contained; more
  important means more prominent. If everything shouts, nothing is heard. Assume every element
  is visual noise until it proves otherwise.
- **Make clickable things obviously clickable.** No relying on hover for discoverability,
  least of all on touch screens. Shape, position, and formatting signal clickability without
  interaction.
- **Eliminate noise.** Three sources: shouting (too much competing for attention),
  disorganization (things not grouped logically), clutter (too much stuff). Fix by removal, not
  addition.
- **Clarity beats consistency.** When making something clearer requires making it slightly
  inconsistent, choose clarity.

## Navigation as wayfinding

Users on the web have no sense of scale, direction, or location. Navigation must answer, on
every page: what site is this, what page am I on, what are the major sections, what are my
options here, where am I in the whole, how do I search. Persistent navigation everywhere;
breadcrumbs for depth; the current section visibly marked. The trunk test in
`design-checklist.md` scores this.

## The goodwill reservoir

Users arrive with a reservoir of goodwill. Every friction point drains it; a few things
refill it. The meter is heuristic, not measured; its value is naming specific drains and fills,
not the final number.

Start each journey at **70/100**.

| Drain | Points |
|---|---|
| Hiding information the user wants (pricing, contact, shipping, limits) | −15 |
| Interstitials, splash screens, forced tours blocking the task | −15 |
| Format punishment (rejecting valid input such as dashes in a phone number) | −10 |
| Asking for information the task does not need | −10 |
| Sloppy or unprofessional appearance | −10 |
| Each choice that requires thinking about whether it is the right one | −5 |

| Fill | Points |
|---|---|
| The top user tasks are obvious and prominent | +10 |
| Graceful error recovery with a specific fix | +10 |
| Upfront about costs and limitations | +5 |
| Each step saved (direct link, smart default, autofill) | +5 |
| An apology when something goes wrong | +5 |

Report as a dashboard, one line per step:

```
Goodwill: 70 ████████████████████░░░░░░░░░░
  Step 1: Sign-in page      70 → 75  (+5 obvious primary action)
  Step 2: Dashboard         75 → 60  (−15 forced tour popup)
  Step 3: Settings          60 → 50  (−10 format punishment on phone field)
  Step 4: Billing           50 → 35  (−15 hidden pricing)
  FINAL: 35/100  ⚠ CRITICAL UX DEBT
```

Below 30: critical UX debt. 30–60: needs work. Above 60: healthy. The largest drains and fills
become findings with the step, the element, and the change.

## Mobile: same rules, higher stakes

Everything above applies on a phone, more so. Real estate is scarce, but usability is never
traded for space. Affordances must be visible: no cursor means no hover to discover. Touch
targets are at least 44 px. Flat design can strip the cues that signal interactivity; check
that it has not. Prioritize ruthlessly: what is needed in a hurry sits close at hand,
everything else a few obvious taps away.
