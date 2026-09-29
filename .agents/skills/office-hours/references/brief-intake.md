# Brief intake

Loaded by office-hours step 2 when the argument is a path under `docs/human/briefs/` ending in
`.md`. A brief is an office-hours prompt a person parked there, copied from
`.agents/templates/human/brief.md`, so that `docs/human/briefs/` holds exactly the briefs not
yet run. Removing one after approval is bookkeeping of the same kind as step 16's
`note-update`: the intake record catching up with the plan. It is not an output, so the
sentences in `SKILL.md` that name the plan file as the only thing office-hours writes, and the
hard gate's list of outputs, still hold. A brief may bring a companion folder,
`docs/human/briefs/<slug>/`, for the files it points at; approval moves the folder in beside the
plan, for the same reason.

```
 a person copies .agents/templates/human/brief.md ─▶ docs/human/briefs/<slug>.md   (parked; local until committed)
   │ optional companion folder docs/human/briefs/<slug>/ , linked from the brief as <slug>/<file>
   │ /office-hours docs/human/briefs/<slug>.md
   ▼
 step 2  path prefix docs/human/briefs/ + .md, checked before the note forms; missing ▶ NEEDS_CONTEXT
         seed := ## What I want · premises += ## Do not reopen · step-1 notes += ## Context links
         companion folder present ▶ every file it holds is listed in the notes; linked ones are read
 step 10 branch defaults to <slug>
 step 12 plan body gains ## Source brief (path + full text, + the folder's new home), after the header block
 step 16 approved ▶ rm -f the brief, BRIEF_REMOVED=1
                    folder ▶ mv to $PLAN_DIR/sources/<slug>/, BRIEF_DIR_MOVED=1 (destination taken ▶ left, reported)
                    ─▶ ship step 9's git add -A commits the deletion and the move
 ABANDONED ▶ BRIEF_REMOVED=1 and tracked ▶ git checkout HEAD -- brief · otherwise nothing (text lives in ## Source brief)
             BRIEF_DIR_MOVED=1 ▶ mv the folder back (its old place taken ▶ left, reported)
```

## Recognize it (step 2)

The form is a repository-relative path with the prefix `docs/human/briefs/` and the suffix
`.md`. Check it before the note forms: a brief path is also a valid note path, and it is never
handed to `parse-task` or `validate-vault`. `BRIEF_SLUG` is the filename without `.md`.

```bash
BRIEF_REL="docs/human/briefs/$BRIEF_SLUG.md"
[ -f "$REPO_ROOT/$BRIEF_REL" ] || echo "NEEDS_CONTEXT: no brief at $BRIEF_REL"
```

A path that does not exist stops the session with `NEEDS_CONTEXT` naming it; nothing is
written. Otherwise read the whole file, then:

- The seed brief is the `## What I want` section's text verbatim: the lines under its heading,
  up to the next line that starts with `## `.
- Each `## Do not reopen` item is a constraint for step 7, presented as a premise the user has
  already agreed to. An item reading "none" adds nothing.
- Each `## Context` link is read now and added to the step 1 notes.
- When the companion folder `docs/human/briefs/$BRIEF_SLUG/` exists, list every file in it in
  the step 1 notes. A file the brief links is read above; one it does not link is listed, and
  read only when the session needs it.
- `plan_mode: feature`. The registry key is `plan:$SAFE_BRANCH` once the branch exists, as for
  free text.

## Companion folder

Supporting files for a brief (a spec, research notes, a screenshot) go in a folder with the
brief's slug beside it. The brief links them relative to its own location, so the links open on
GitHub and in Obsidian while the brief is parked:

```
docs/human/briefs/
  calendar-sharing.md             - [API spec](calendar-sharing/api-spec.md) under ## Context
  calendar-sharing/
    api-spec.md
    mockup.png
```

The folder is optional; a brief without one runs exactly as before. Approval moves it to
`$PLAN_DIR/sources/<slug>/`. The brief's text is kept verbatim in the plan, links included, so
a link written as `<slug>/<file>` names the file's path under `sources/` too.

## Branch (step 10)

The name defaults to `BRIEF_SLUG`. The usual question still applies when the user wants another.

## Plan (step 12)

Directly after the header block, before the Problem Statement, the plan body carries the brief,
the way a note-sourced plan carries `## Source task`. The text goes inside a four-backtick fence
so that its headings do not become the plan's, and a fence inside the brief survives:

`````markdown
## Source brief
- File: `docs/human/briefs/<slug>.md` (removed on approval; this section keeps its text)
- Companion folder: `sources/<slug>/` (moved from `docs/human/briefs/<slug>/` on approval)

````markdown
<the brief's full text, verbatim>
````
`````

The `Companion folder` line is written only when the folder exists. No frontmatter key records
the brief: this section is the provenance.

## Approval (step 16)

After approval, remove the brief on the branch and move its companion folder in beside the plan:

```bash
: "${REPO_ROOT:?}" "${BRIEF_SLUG:?}" "${PLAN_DIR:?}"
rm -f -- "$REPO_ROOT/docs/human/briefs/$BRIEF_SLUG.md"
BRIEF_REMOVED=1
BRIEF_DIR_MOVED=0
BRIEF_DIR="$REPO_ROOT/docs/human/briefs/$BRIEF_SLUG"
SOURCES_DIR="$PLAN_DIR/sources/$BRIEF_SLUG"
if [ -d "$BRIEF_DIR" ]; then
  if [ -e "$SOURCES_DIR" ]; then
    echo "companion folder not moved: $SOURCES_DIR exists"
  else
    mkdir -p "$PLAN_DIR/sources"
    mv -- "$BRIEF_DIR" "$SOURCES_DIR" && BRIEF_DIR_MOVED=1
  fi
fi
```

The first line stops the block, before anything is removed, when any of the three variables is
empty (a fresh shell that did not set them again): with no slug, `$BRIEF_DIR` would be
`briefs/` itself and every parked brief would move into this plan. Set them and run it again.

The destination is named in full and checked first: `mv` into an existing folder would nest the
brief's folder inside it. When the check stops the move, the folder stays parked and the session
ends DONE_WITH_CONCERNS naming both paths.

Plain `rm` and `mv`, never `git rm` or `git mv`. Office-hours never commits, and a staged
deletion would sit in the index across every later session and ride in whichever commit came
first. The working-tree deletion and the move are picked up by ship step 9's `git add -A` into
the record commit, so `briefs/` on the base branch equals what is still parked once the plan
lands. Before that the brief is usually
untracked anyway: written by hand, never committed.

## Abandoned

Only when `BRIEF_REMOVED=1`, and only for a tracked brief, restore it:

```bash
cd "$REPO_ROOT"
if [ "$BRIEF_REMOVED" = "1" ] && git ls-files --error-unmatch -- "$BRIEF_REL" >/dev/null 2>&1; then
  git checkout HEAD -- "$BRIEF_REL"
fi
```

Otherwise touch nothing: before approval nothing was removed, and an unguarded checkout would
discard a person's uncommitted edits to a tracked brief. An untracked brief removed after
approval is gone from disk; its text is in the plan's `## Source brief`, which abandon leaves
in place, and the ABANDONED report says so. If the checkout fails (a brief staged but never
committed), the report says that too, and points at the same section.

A companion folder that approval moved (`BRIEF_DIR_MOVED=1`, carried from step 16 like
`BRIEF_REMOVED`) goes back to where the person put it, tracked or not:

```bash
BRIEF_DIR="$REPO_ROOT/docs/human/briefs/$BRIEF_SLUG"
SOURCES_DIR="$PLAN_DIR/sources/$BRIEF_SLUG"
if [ "$BRIEF_DIR_MOVED" = "1" ]; then
  : "${REPO_ROOT:?}" "${BRIEF_SLUG:?}" "${PLAN_DIR:?}"
  if [ -e "$BRIEF_DIR" ]; then
    echo "companion folder left at $SOURCES_DIR: $BRIEF_DIR exists"
  else
    mv -- "$SOURCES_DIR" "$BRIEF_DIR"
    rmdir -- "$PLAN_DIR/sources" 2>/dev/null || true
  fi
fi
```

The same check stops a move back when one of the three variables is empty. `rmdir` removes
`sources/` only when the move left it empty. The plan's `Companion folder` line
then names a path that is gone; the ABANDONED report says where the folder is.

Every other step runs as it does for free text.
