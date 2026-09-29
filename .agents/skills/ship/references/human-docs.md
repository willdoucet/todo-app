# Human docs

Loaded by ship steps 1 and 8 when `modules.human_docs` is `true` in
`$REPO_ROOT/.agents/config.json`. Every ship writes one log entry, and a feature page unless the
step 1 decision was log-only. That includes a part of a plan that ships in parts which does not
complete it: a part can be live for weeks before the next one, and one entry per pull request is
the rule. Both files are committed by step 9's record commit, so they are in the pull request's
diff before anyone merges it. The reader is a person who does not have the code open.

```
docs/human/features/<slug>.md                  one page per capability; rewritten on every ship that touches it
docs/human/log/<utc-date>-<safe-branch>.md     one entry per pull request; never rewritten after merge
```

The templates are `$REPO_ROOT/.agents/templates/human/feature.md` and `log.md`. They carry the
audience in their own placeholder text; this file carries the caps and where each slot comes
from.

## Rules

Slots: `{{…}}` is filled by the writer named in the file; `<…>` inside a slot is a sub-slot;
`a | b` inside a slot means choose one; `<utc-date>` is the output of `date -u +%F`;
`{{one line}}` in a History row is the log entry's H1 without its date.

Both files:

- `{{PR_URL}}` is `PR_URL` from step 7. `{{PR_NUMBER}}` is its trailing integer. When a pull
  request could not be opened (no `gh`), `PR_URL` is the compare URL `references/pr-body.md`
  sets, and the PR cell of both headers is written as `[PR pending](<that compare URL>)`, one
  form. The ship's `DONE_WITH_CONCERNS` names both files for a hand edit unless the user hands
  back the real URL inside the run (step 8, item 4).
- `{{BRANCH}}` is `$BRANCH`.
- `{{LOG_FILE}}` and `{{LOG_DATE}}` are the log entry's actual filename and the date parsed from
  it (its first ten characters; step 8, item 4), never recomputed.
- Nothing is copied from the plan, the summary, or the pull request; the files retell.
- No frontmatter (GitHub renders it as a table, and the header line already carries the date).
  Relative links only, so a file works on GitHub and in Obsidian.

The feature page:

- `{{FEATURE_NAME}}` is the capability's name as a person would say it, proposed at step 1
  beside the slug: free text, title case ("Household login", not the slug).
- At most 40 lines excluding `## History`; History at most ten rows.
- "What it does" is a retelling from the plan's problem statement and the summary, never an
  excerpt. On a part that does not complete its plan (`PARTIAL=1`), it describes what works
  once this part merges, never the plan's end state (the problem statement describes the whole
  plan, so retelling it would claim the unshipped parts); one closing sentence may say more is
  coming, without part labels. "What changed in this ship" is this part's changes.
- `{{PLAN_RELPATH}}` is `../../../` followed by the repo-relative `_PLAN_FILE`, whatever
  `paths.plans` is (`../../../.agents/plans/features/<dir>/<file>.md` by default).

The log entry:

- At most 30 lines.
- `{{PLAN_TITLE}}` is the plan's H1 with the `# Design:` prefix removed.
- `{{LOG_DATE}}` is the date in the entry's own filename.
- `{{PART_SUFFIX}}` is ` (part <PART>)` when `ship-record` printed a part (every ship of a plan
  that declares `ship_parts`, the last part included), and empty otherwise, so two parts
  shipped the same day get distinct titles and distinct History rows.
- Never rewritten after the pull request merges; a correction is a new entry that links the
  old one. This is enforced, not only stated: no lookup returns an entry the base branch
  already has (step 8, item 4). A re-run of an interrupted ship finds and rewrites its own
  entry, so one pull request has exactly one.

## Step 1: the proposal

Before writing the ASSUMPTIONS block, list the pages; an empty or missing folder lists nothing:

```bash
ls "$REPO_ROOT/docs/human/features/" 2>/dev/null
```

Propose exactly one of:

- `update features/<slug>.md` when an existing page names this capability: its title or the
  intake's words match. Say which words.
- `new page features/<slug>.md "<Feature name>"` when no page does, with the slug and the
  capability's name you propose.
- `log-only` when the ship adds nothing a person would name as a capability: an
  infrastructure change, a dependency bump, a refactor. A workflow change that gives people
  something new is a capability of the repository, not log-only.

**Slug rule.** `^[a-z0-9]+(-[a-z0-9]+)*$`, 2 to 40 characters: lowercase letters, digits,
single hyphens, no leading or trailing hyphen. Named for the capability as a person would say
it, for example `household-login`, `recipe-import`, `calendar-sharing`, never for a branch, a
plan, or a milestone. A slug you propose that fails the rule is corrected before the block is
shown. One the user types in the correction reply that fails it is refused with the rule
quoted, and the block is shown again with that line corrected. `new page` for a slug whose
file already exists is shown as `update features/<slug>.md` instead; the user can still rename.

Then the log entry's path, a preview of what step 8 decides. Set `PR_URL` to the branch's open
pull request (step 7's `gh pr view` line), or else to the compare URL from
`references/pr-body.md`, and run the lookup block under step 8, item 4. A hit shows
`update log/<file>` (an interrupted ship, or one that crossed midnight); none shows the planned
`log/<utc-date>-<safe-branch>.md`. The block gains one line, which the user corrects in the
reply they already give:

```
HUMAN DOCS: new page features/<slug>.md "<Feature name>"; log/<utc-date>-<safe-branch>.md
```

## Step 8: write the files

```
 PR_URL empty? ──yes──▶ PR_URL := compare URL; both files will say [PR pending]
      │ no
      ▼
 (a) grep -rlF -- "${PR_URL})" log/ | not_on_base | sort | tail -1 ──hit──▶ rewrite in place
      │ miss                                                              LOG_FILE = its name
      ▼                                                                   LOG_DATE = date in the name
 (b) grep -rlE -- '^\[PR pending\].* branch `$BRANCH`' log/ | not_on_base | sort | tail -1 ──hit──▶ same, PR cell := real number
      │ miss
      ▼
 name := <utc-date>-<safe-branch>.md ── exists? ──yes──▶ lowest free -N suffix, N ≥ 2
      │ no                                             (a name (a) and (b) did not return belongs to another pull
      ▼                                               request, or to an earlier part already merged)
 create it; LOG_FILE = the name written; LOG_DATE = its date; H1 ends (part <PART>) when a part is set

 not_on_base: drop a file when `git cat-file -e $BASE_REF:<path>` succeeds; BASE_REF = origin/<base> | <base>
              (a merged entry is never rewritten; with no readable base ref every file passes)
```

Why the filter: one branch can carry several pull requests of one plan, and a compare URL is the
same for every part of a branch.

```
 branch feat-x ── PR1 ship (no gh) ─▶ log/D1-feat-x.md  "[PR pending](compare…) · branch `feat-x`" ─▶ merged to the base
        │
        └─ PR2 ship ─▶ (a) compare URL matches D1's entry ┐ without the filter: D1's merged entry rewritten as PR2's
                       (b) pending + branch matches it     ┘ with it: D1 is on the base ─▶ dropped ─▶ new entry
                                                               log/D2-feat-x.md (or D1-feat-x-2.md the same day), "(part PR2)"
```

A section of a page is its heading line through the line before the next line that starts
with `## `, or the end of the file. A rewrite replaces exactly that span: a person's `### `
sub-heading inside `## What it does` goes with it; a `## Custom` heading anywhere survives.

1. `mkdir -p "$REPO_ROOT/docs/human/features" "$REPO_ROOT/docs/human/log"`. A folder deleted by
   accident must not block a ship; `framework doctor` reports the deletion.
2. Read the templates from `$REPO_ROOT/.agents/templates/human/`. A missing template is a soft
   failure: that file is not written, and the ship reports it.
3. Sources, in this order: the plan's problem statement and success criteria; the summary's
   deviations; the pull request body's summary; the REVIEW REPORT. The files retell; the caps
   and slot derivations are under Rules above.
4. The log entry first; find before creating. Both lookups run only when `PR_URL` is non-empty:
   with an empty one, (a) would be `grep -F ")"`, which matches every entry that holds a
   parenthesis and hands back another pull request's file. `PR_URL` is empty when `gh pr view`
   fails right after the create; set it to the compare URL from `references/pr-body.md` first,
   and both files carry `PR pending` exactly as in the no-`gh` case. Then (a), the entry that
   names `${PR_URL})` (the closing parenthesis stops `/pull/5` matching `/pull/58`); else (b),
   the newest `[PR pending]` entry whose header names `` branch `$BRANCH` `` (a previous run
   without `gh`, whose entry names the compare URL; the prefix excludes every `[PR #` line).
   Both drop every hit the base branch already has and take the newest by filename:

   ```bash
   LOG_DIR="$REPO_ROOT/docs/human/log"
   BASE_REF="origin/$BASE_BRANCH"; git -C "$REPO_ROOT" rev-parse --verify --quiet "$BASE_REF" >/dev/null || BASE_REF="$BASE_BRANCH"
   not_on_base() { while IFS= read -r f; do git -C "$REPO_ROOT" cat-file -e "$BASE_REF:${f#"$REPO_ROOT"/}" 2>/dev/null || printf '%s\n' "$f"; done; }
   HIT=
   [ -n "$PR_URL" ] && HIT=$(grep -rlF --include='*.md' -- "${PR_URL})" "$LOG_DIR" 2>/dev/null | not_on_base | sort | tail -1)
   [ -n "$PR_URL" ] && [ -z "$HIT" ] && HIT=$(grep -rlE --include='*.md' -- "^\[PR pending\].* branch \`$BRANCH\`" "$LOG_DIR" 2>/dev/null | not_on_base | sort | tail -1)
   printf '%s\n' "${HIT:-none}"
   ```

   `BASE_REF` is step 2's `SYNC_REF` rule, and step 2 fetched it in this run. When no base ref
   can be read, every hit passes, never none. `-r --include` needs no shell glob, so an empty
   folder is fine under zsh too. A part whose predecessor has not merged is not covered here:
   `/execute-plan` asks before any code of the next part when the last part's pull request is
   not merged.

   A hit is rewritten in place: its filename kept (`LOG_FILE`), `LOG_DATE` parsed from that
   filename, and the PR cell replaced with the real number. On none, name a new entry; a name
   that exists and was not returned belongs to another pull request, or to an earlier part
   already merged, so the lowest free `-N` suffix (`N` ≥ 2) is used:

   ```bash
   LOG_DATE=$(date -u +%F); LOG_FILE="$LOG_DATE-$SAFE_BRANCH.md"; N=2
   while [ -e "$REPO_ROOT/docs/human/log/$LOG_FILE" ]; do LOG_FILE="$LOG_DATE-$SAFE_BRANCH-$N.md"; N=$((N + 1)); done
   echo "LOG_FILE=$LOG_FILE"
   ```

   If the run had no `gh` and the user hands back the real URL before step 9
   (`references/pr-body.md` already asks for it), run items 4 and 5 again with it: lookup (b)
   finds the pending entry and its PR cell gets the real number. Otherwise both files carry
   `PR pending` and the completion says so.
5. The feature page, unless the step 1 decision was log-only (then no page is written or
   touched). A new page: fill `feature.md` whole. An existing page: replace the line starting
   `As of `, rewrite `## What it does` and `## What changed in this ship` entirely, and in
   `## History` replace the first row when it already links `LOG_FILE` (a re-run), otherwise
   prepend a row and drop rows past ten. Everything else on the page stays as it is: a person
   may have added sections below `## History`, and they survive. When any of the four anchors
   (`As of `, the three headings) is missing because a person removed or renamed it, fill
   `feature.md` whole, keep the rows of a `## History` that is still there under the new row,
   carry every unrecognized section over below `## History`, and say so in the transcript.
6. Read both files back and show them in the transcript: the user sees them before the record
   commit. Do not ask a question here; the decision was made at step 1.
7. Dates: `date -u +%F` for the "As of" line; `LOG_DATE` from the filename everywhere else, so a
   next-day re-run leaves the entry's date and the History link consistent with its name.
   Never the plan's date, never the agent's belief.

A failure in any item (a template missing, a folder that cannot be created, a page whose
headings cannot be found) never stops the ship: keep going through step 9 and report
`DONE_WITH_CONCERNS` naming the file that was not written.
