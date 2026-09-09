# {{PROJECT_NAME}} Notes

This folder is the writing surface for ideas, bugs, polish items, and planning notes for
{{PROJECT_NAME}}. It is an Obsidian vault, it is ignored by git, and it is local to your machine.

The workflow reads it through the host-side helper `.agents/bin/obsidian-workflow` (never through
a container). Point a skill at a task here and the workflow creates the plan, runs the reviews,
implements, ships, and comes back to tick the box.

## Short Version

Keep writing normal Markdown. For any task you want the workflow to pick up:

1. Use a checkbox: `- [ ]`
2. One task per checkbox
3. Add context under it with `notes::` lines (yours to write and edit, always)
4. Let the workflow assign the `^block-id` when the task is promoted; never write, edit, or reuse one yourself

```md
## Ideas

- [ ] Improve the loading state so very fast loads feel intentional instead of broken.
  notes:: Research patterns for pages that load in under 200ms.

- [ ] Add a short transition to the date bar so it does not pop in after loading.
  notes:: Should feel connected to the loading treatment above.
```

## Task Format

| Line | Who writes it | Rule |
|---|---|---|
| `- [ ] <task>` | you | one feature-sized or fix-sized unit of work; concrete enough that "done" is obvious |
| `  notes:: <text>` | you | any number of them; add, edit, or remove freely at any time |
| `  ^block-id` | the workflow | assigned on promotion; lowercase, hyphenated, derived from the task text; never edited, never reused |

Nothing else is written under a task. Status, plan path, review state, and completion date are
**not** stored in the note. They live in the workflow registry at `.agents/state/registry/`, keyed
by `<note path>#^block-id`. Ask `.agents/bin/workflow-state` for them.

## What The Workflow Does To Your Note

- **On promotion** (first `/quickfix` or `/office-hours` against the task): inserts the `^block-id` line under the checkbox if it is missing. Task text and `notes::` lines are left alone.
- **On ship**: checks the box and moves the task, with its id and notes, under a `# Completed` heading at the bottom of the note (created if absent).
- **On supersede or abandon**: may append one line, `notes:: superseded by <ref>` or `notes:: abandoned — <reason>`, so the history stays in the note.

That is the whole write surface. The workflow never rewrites your task text, never removes your
`notes::` lines, and never writes `status::`, `plan::`, or `review_status::` fields.

## Entry Modes

| Command | Scope | Behavior |
|---|---|---|
| `/quickfix {{VAULT_PATH}}/Ideas.md#^task-id` | one task | small fix; escalates to office-hours if it grows, keeping the same id |
| `/office-hours {{VAULT_PATH}}/Ideas.md#^task-id` | one task | one feature plan for that task |
| `/office-hours {{VAULT_PATH}}/Ideas.md` | every unchecked task in the note | one combined plan; ids generated for all; completion is all-or-nothing |

Batch mode ticks the boxes only when the whole combined plan ships. If execution is blocked or
needs context, no box in the batch is ticked. Use batch mode when the tasks belong together and
should ship as one change; use a ref when you want exactly one.

A task without an id yet can be started by path plus a quoted fragment of its text; the workflow
assigns the id and tells you the ref to use from then on.

## Good And Bad Examples

Good — one improvement, concrete, plannable:

```md
- [ ] Improve the loading state so very fast loads feel intentional instead of broken.
```

Also good — context lives below the task, not inside it:

```md
- [ ] Add a short transition to the date bar so it does not pop in after loading.
  notes:: Coordinate with the loading-state change.
  notes:: Keep it under 200ms; the page already feels slow to me.
```

Bad — several deliverables in one checkbox; "done" is undefined and the ship step cannot tick it honestly:

```md
- [ ] Fix the loading state, update the date bar animation, audit related CSS, and rethink page transitions.
```

Bad — too vague to plan or to generate a readable id from:

```md
- [ ] Improve loading.
```

Bad — hand-written status fields; the workflow ignores them and they drift from the registry:

```md
- [ ] Improve the loading state.
  ^loading-state
  status:: shipped
  plan:: some/path.md
```

## Splitting

Split a task when it has independent success criteria, when one part could ship without the
other, or when one part is visual polish and the other is architecture. Keep it as one task
when it is one user-visible improvement and the notes are context, not separate deliverables.

## Block ID Lifecycle

1. Write tasks without ids.
2. The workflow assigns an id on promotion.
3. The id never changes; you can rewrite the task text freely.
4. Revisiting a shipped idea: write a new checkbox. Shipped ids stay reserved even after the task moves under `# Completed`.
5. Moving a task to another note changes its ref (`<path>#^id`); tell the workflow with `obsidian-workflow` rather than editing the registry.

## Folder Intent

Use this folder for scratch notes, idea capture, rough lists, exploration, and planning seeds. No
frontmatter, no file-per-idea, no structure is required. Only a task you want the system to plan,
track, execute, and tick off needs the checkbox format above.

Suggested layout, none of it mandatory:

```
{{VAULT_PATH}}/
├── README.md        # this file
├── Ideas.md         # capture
├── Bugs.md          # things that are broken
└── <Feature>/       # a folder per large area once it earns one
```
