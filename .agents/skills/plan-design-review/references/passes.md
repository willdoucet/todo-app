# The seven passes

Loaded by `plan-design-review` at step 7. Run them in order, one at a time. Each pass follows
the rating method (rate, gap, fix, re-rate, ask only on a genuine choice, fix again) and ends
in edits to the plan, not notes about it. Stop after each pass and wait for the user.

## The rating method

1. **Rate:** "Information architecture: 4/10."
2. **Gap:** "It is a 4 because the plan never defines content hierarchy. A 10 has clear
   primary, secondary, and tertiary content for every screen."
3. **Fix:** edit the plan to add what is missing.
4. **Re-rate:** "Now 8/10; still missing the mobile navigation hierarchy."
5. **Ask** the user only when a genuine design choice remains, one issue per question.
6. **Fix again.** Repeat until 10, or until the user says "good enough, move on".

On a rerun of this skill, passes that scored 8 or above last time get a quick pass; passes
below 8 get the full treatment.

## Pass 1: Information architecture

Rate 0-10: does the plan define what the user sees first, second, third, on every screen it
touches?

Fix to 10: add the hierarchy to the plan, per screen. Include an ASCII sketch of the screen
structure and the navigation flow between screens. Apply constraint worship: if only three
things can be shown, which three? Name the primary action per screen and where the eye lands.

```
  +--------------------------------------------------+
  | [navigation]                                     |
  +--------------------------------------------------+
  | PRIMARY: <what the user came for>                |
  |   SECONDARY: <supporting context>                |
  |     TERTIARY: <everything else, collapsed>       |
  +--------------------------------------------------+
  screen A --(primary action)--> screen B --(back)--> screen A
```

## Pass 2: Interaction state coverage

Rate 0-10: does the plan specify loading, empty, error, success, and partial states for every
UI feature it adds or changes?

Fix to 10: add the interaction state table to the plan, one row per feature. Each cell
describes what the user sees, not what the backend does.

```
  FEATURE              | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL
  ---------------------|---------|-------|-------|---------|--------
  [each UI feature]    | [spec]  | [spec]| [spec]| [spec]  | [spec]
```

Empty states are features: specify warmth, the primary action, and the context that tells the
user why it is empty and what to do next. Error states name the copy and the recovery action.
Partial states cover slow or paginated data, optimistic updates that fail, and a list that is
half loaded. Loading states say what is shown while waiting (skeleton, spinner, or nothing) and
how long before feedback appears.

## Pass 3: User journey and emotional arc

Rate 0-10: does the plan consider the user's emotional experience through the flow?

Fix to 10: add the storyboard to the plan.

```
  STEP | USER DOES        | USER FEELS      | PLAN SPECIFIES?
  -----|------------------|-----------------|----------------
  1    | Lands on page    | [what emotion?] | [what supports it?]
  2    | ...              |                 |
```

Apply time-horizon design: the five-second visceral impression, the five-minute behavioral
flow, the five-year reflective relationship. A row where "plan specifies?" is empty is a gap;
fill it with the concrete element (copy, motion, layout, feedback) that supports the intended
feeling, or change the feeling if it is the wrong one to aim for.

## Pass 4: AI-slop risk

Rate 0-10: does the plan describe specific, intentional UI, or generic patterns that could
belong to any product?

Fix to 10: read `references/design-rules.md`. Classify the surface, apply the hard rejection
criteria, run the litmus checks, apply the App UI rules where they fit, and check every
described element against the slop blacklist. Rewrite vague UI descriptions in the plan with
the specific alternative; the vague-phrase table in that file gives the replacement question
for each.

## Pass 5: Design-system alignment

Rate 0-10: does the plan align with `$DOCS_DIR/FRONTEND_GUIDELINES.md` and the component
inventory in `FRONTEND_STRUCTURE.md`?

Fix to 10: when the guidelines exist, annotate the plan with the specific tokens (color, type,
spacing, radius, motion) and the existing components each element uses. Flag every new
component: does it fit the existing vocabulary, or does an existing one already do the job?
Apply the project's concrete token and component checks from `REVIEW_CHECKLIST.md`. When no
guidelines exist, flag the gap in the plan and propose a TODO to write them.

## Pass 6: Responsive and accessibility

Rate 0-10: does the plan specify the layout at each viewport and the keyboard, screen-reader,
contrast, and touch behavior?

Fix to 10: add responsive specs per viewport using the breakpoints named in the guidelines. Not
"stacked on mobile": say what changes, what collapses, what is hidden and where it goes, and
what the primary action becomes. Add accessibility requirements: keyboard navigation patterns
and focus order, ARIA landmarks and roles for custom widgets, touch targets of at least 44px,
color contrast targets, reduced-motion behavior, and what a screen reader announces for each
state from pass 2. Apply the project's accessibility tooling from `REVIEW_CHECKLIST.md`.

## Pass 7: Unresolved design decisions

Surface the ambiguities that will haunt implementation.

```
  DECISION NEEDED                  | IF DEFERRED, WHAT HAPPENS
  ---------------------------------|---------------------------------------
  What does the empty state show?  | The engineer ships "No items found."
  Mobile navigation pattern?       | Desktop nav hides behind a hamburger
  ...                              |
```

Each row is one question to the user with a recommendation, why, and alternatives. Edit the
plan with each decision as it is made. A row the user declines to decide goes to "Unresolved
decisions" in the plan, never to a silent default.
