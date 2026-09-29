# Human-readable docs after every ship — `docs/human/` (framework 1.5.0) — execution summary

- Plan: .agents/plans/features/human-docs/human-docs-plan-20260921-233505.md
- Branch: human-docs
- Started: 2026-09-23T02:40:37Z
- Metadata: {"implementation_status": "not-started", "plan_kind": "feature", "plan_mode": "feature", "registry_key": "plan:human-docs", "review_status": ["eng-reviewed"], "risk_tags": ["infra"], "ui_scope": false, "updated_at": "2026-09-23T02:32:02Z", "workflow_status": "eng-reviewed"} (read before the start sync set `implementing`; gate: `--next` names `/execute-plan`, `unreadable` 0)
- Test artifact: .agents/plans/testing/human-docs-test-artifact.md
- Design source of truth: none (installer, skill text and templates; no UI; the plan has no `## Design Source of Truth` section)
- Base: todo-app `human-docs` = `origin/master` = `1087f30` (framework 1.4.1, #59; `git merge-base --is-ancestor 1087f30 HEAD` exits 0; `.agents/config.json` reads `"framework_version": "1.4.1"`), fetched 2026-09-23T02:40Z. §11 step 1's merge had already happened before this run. Framework `main` = `origin/main` = `311ffbd` (VERSION 1.4.1), clean.

## Current PR-T shipping copy

Use this current copy for `/ship`; the dated notes below describe earlier releases.

- PR title: `feat(human-docs): add human docs with framework 1.6.1`
- PR Summary: Upgrade the installed framework from 1.4.1 to 1.6.1 and add the
  `docs/human/` scaffold. Feature ships write plain-English capability pages and a
  per-PR log; parked briefs can bring companion files into their approved plan.
  Keep parked briefs local until deliberately committed, and link the new docs
  from `AGENTS.md`.
- Human-docs log entry title (`{{PLAN_TITLE}}`, used in the log entry's H1 and the feature
  page's History row in place of the plan's historical H1): `Human-readable docs after every
  ship — docs/human/ (framework 1.6.1)`. Final review 2, user decision: the entry is never
  rewritten after merge, so it names the release this pull request installs.

## Steps
- [✓] Step 1 — PR-F §10.1–2: branch `human-docs` from framework `main` at `311ffbd`; baseline suite; failing tests first (§9: `test_cli.py`, `test_skill_lint.py`, `dated_payload_files` extended) (2026-09-23T02:53:15Z)
- [✓] Step 2 — PR-F §2: the four templates under `payload/templates/human/` (2026-09-23T02:56:11Z)
- [✓] Step 3 — PR-F §5: `ensure_human_docs` in `bin/framework` and its three call sites (2026-09-23T02:56:11Z)
- [✓] Step 4 — PR-F §6: doctor's three human-docs warnings (2026-09-23T02:56:11Z)
- [✓] Step 5 — PR-F §7: `payload/config.example.json` and `init-project/SKILL.md` (2026-09-23T02:56:11Z)
- [✓] Step 6 — PR-F §3: ship hook (`ship/SKILL.md` step 1 line, step 8 paragraph, completion line, three same-line rewrites; new `references/human-docs.md`) (2026-09-23T03:04:48Z)
- [✓] Step 7 — PR-F §4: brief intake (`office-hours/SKILL.md` one row and two same-line appends, 500 lines; new `references/brief-intake.md`) (2026-09-23T03:04:48Z)
- [✓] Step 8 — PR-F §8: documents (`WORKFLOW.md`, `templates/AGENTS.md`, framework `README.md`, `CHANGELOG.md` 1.5.0, `VERSION`) (2026-09-23T03:04:48Z)
- [✓] Step 9 — PR-F §10.3: full framework suite green with the count quoted; `init --dry-run` on a temp repo; critical paths 6, 7, 8 and 10 run by hand in scratch repos (2026-09-23T03:09:27Z)
- [✓] Step 10 — PR-F §10.4: the user's OK, then commit, push and open PR-F (2026-09-23T03:11:41Z)
- [✓] Step 11 — PR-T §11.2–3, after PR-F merges: framework `origin/main` reads 1.5.0; `framework upgrade <literal worktree path> --dry-run`, apply, a second run idempotent; `doctor` 0 failures; host `.agents/tests` suite (2026-09-28T20:52:12Z)
- [✓] Step 12 — PR-T §11.4: hand edits (`AGENTS.md` one line; `LESSONS.md` rows the implementation teaches) (2026-09-28T20:53:58Z)

Not boxes: §11 steps 5–8 (update-docs inside `/ship`, the worktree skill-text diff, the first real human-docs write, `ship_parts` unset) belong to `/ship`. The framework commit and pull request are outside `/ship`'s scope; the plan's §10 step 4 gates them on the user's OK.

## Step notes

### Step 1 — framework worktree, baseline, failing tests (2026-09-23T02:53:15Z)
- Worktree: `<the framework worktree's literal absolute path>` (ignored by the framework's `.git/info/exclude`), branch `human-docs` cut from `main` at `311ffbd`; the main framework checkout stays on `main`.
- Baseline: `python3 -m pytest tests payload/tests -q` → **1057 passed in 100.78 s** at `311ffbd`, matching Eng review 2.
- `tests/test_cli.py` (+11 test cases): `test_init_scaffolds_human_docs`, `test_upgrade_scaffolds_human_docs_once`, `test_upgrade_respects_human_docs_off[False|"false"]`, `test_upgrade_dry_run_lists_human_docs_and_writes_nothing`, `test_upgrade_tolerates_a_non_object_modules_key[modules=[] | exempt="docs/**"]`, `test_migrate_scaffolds_human_docs`, `test_doctor_warns_when_human_docs_on_but_folder_missing`, `test_doctor_warns_when_exempt_glob_or_gitignore_line_missing`; `test_init_dry_run_writes_nothing` gains the five `plan` lines. `_lib` imported from `payload/bin` so the 1.4.1-shaped repository is built through `_lib.save_config`, as the plan says.
- `tests/test_skill_lint.py`: `dated_payload_files()` extended with `payload/templates/human/*.md`; `test_ship_writes_human_docs_under_the_flag` (hook after the Learning paragraph, its own paragraph), `test_office_hours_reads_a_brief`, `test_human_docs_templates_and_reference_agree_on_slots`, `test_feature_slug_rule`, `test_human_docs_log_lookups_find_this_prs_entry[bash|zsh]` (runs the reference's fenced block, found by its `not_on_base` anchor, with `bash -c` and `zsh -f -c`, in scratch git repos with a `master` ref).
- Red run: `tests/test_cli.py` 11 failed / 11 passed; `tests/test_skill_lint.py` 6 failed / 409 passed. Every failure is a missing file, function, or line.
- Additions beyond §9's list, all small: the off test is parametrized over `False` and the string `"false"` (test artifact edge case); the shape test also covers a non-array `doc_map.exempt` (the guard's third condition); the doctor test also checks that the flag off silences the folder warning; the slug test adds `recipe-import`, `x1-2y`, 40 characters and `a_b`.

### Steps 2–5 — templates, installer, doctor, config (2026-09-23T02:56:11Z)
- Step 2: `payload/templates/human/{feature,log,brief,README}.md` written from §2's fenced bodies byte for byte. The date, positional, flag and plan-flag lints now run over them (16 new parametrized cases, all green).
- Step 3: `bin/framework::ensure_human_docs(root, cfg, rep) -> bool` in the "Shared install steps" block, with §5's box diagram as its docstring. Order: shape guard (non-object `modules` or `doc_map`, non-array `doc_map.exempt` → one WARN, return False, nothing written); flag (absent → set `true`, `do`, changed; present and not `is True` → `skip` naming the value via `json.dumps`, return False); README (only when absent, own `values` from `cfg.get`, label `docs/human/README.md`); the three folders with `.gitkeep` (present: no line); exempt glob (appended, `do`, changed); `.obsidian/` line (appended directly, with a leading newline when the file lacks a trailing one; not a config change). Call sites: `cmd_init` after `install_harness_files`, before `install_hook`; `cmd_migrate` after `install_harness_files(…, replace_rules=True)`, before `install_hook`; `cmd_upgrade` after the migrations loop, before `raw["framework_version"] = VERSION`, on `raw` (the existing save persists it).
- Step 4: `cmd_doctor`, after the vault check, when `modules.human_docs` is exactly `true`: three `warn`s (folder missing; exempt glob missing, or `exempt` not a list; no `.obsidian/` line), each ending "run framework upgrade". Never `fail`.
- Step 5: `payload/config.example.json`: `"human_docs": true` in `modules`, `"docs/human/**"` in `doc_map.exempt` (after `.cursor/**`). `init-project/SKILL.md`: the `cfg["modules"]` line carries `"human_docs": True`; the module paragraph gains the `human_docs` clause.
- Verification: `python3 -m pytest tests/test_cli.py -q` → 22 passed. A real `framework init` in a scratch repo printed `write docs/human/README.md`, three `create docs/human/<sub>/` and `.gitignore append: .obsidian/`, in that order after the snippet's line; `.obsidian/` is the last line of `.gitignore`, below the `# framework` block; the README's H1 reads `# demo-app — human docs`.
- Deviations: (1) `cmd_init` also saves the config when `ensure_human_docs` returns True, as `cmd_migrate` does; the plan gave migrate the save "so the contract holds if the example ever lacks the key", and init has the same exposure. (2) `init-project`'s module paragraph said "Recommend off" for every module, which contradicts a default-on `human_docs`; it now reads "Recommend off, except `human_docs`, unless the interview surfaced a reason" (one line longer). (3) A test-helper fix, not a code fix: `_strip_human_docs` also removes the empty `docs/` that init created, so "upgrade creates nothing under `docs/`" is checkable.

### Steps 6–8 — ship hook, brief intake, documents (2026-09-23T03:04:48Z)
- Step 6, `payload/skills/ship/references/human-docs.md` (new): the `## Rules` section (slot conventions; both-file rules for `{{PR_URL}}`, `{{PR_NUMBER}}`, `{{BRANCH}}`, `{{LOG_FILE}}`, `{{LOG_DATE}}`; the feature-page and log-entry rules from §2, including the partial-ship wording and `{{PART_SUFFIX}}`); "Step 1: the proposal" (the `ls`, the three proposals, the slug rule with "for example" on its line, the log-path preview); "Step 8: write the files" (the lookup tree with `not_on_base` and the two-parts diagram as inline diagrams, the section-span definition stated once above the list, items 1–7 from §3, the lookup block verbatim from §3 step 4, and a three-line naming block for the `-N` suffix).
- Step 6, `payload/skills/ship/SKILL.md` (434 → 458 lines): the description's two clauses ("logs the ship; writes the human-readable feature page and log entry.", "no release changelog"), the "Do not use when" bullet ("a release changelog"), and the References line gaining `references/human-docs.md`; step 1 gains a flag check (one `python3 -c` that prints `HUMAN DOCS: on` or `HUMAN DOCS: off; nothing is written`, JSON `true` only) and a paragraph pointing at the proposal, and the ASSUMPTIONS list names "the human-docs line"; step 8 gains the hook as its own paragraph after the Learning summary, opening "On every ship, a part that does not complete the plan included"; step 9's list of what the record commit holds names the human-docs files; Completion gains the `DONE_WITH_CONCERNS` cause and the `HUMAN DOCS:` summary line.
- Step 7, `payload/skills/office-hours/SKILL.md` 499 → **500** lines: the Brief row appended after the Free text row (the one net line); line 466 (was 465) ends "concrete build steps. A brief is removed now, per `references/brief-intake.md`." (79 characters; the plan counted 78); line 483 (was 482) ends "`--reason "..."`. A brief is restored per `references/brief-intake.md`." (72). `references/brief-intake.md` (new): the bookkeeping paragraph that reconciles the two "only output" sentences, the lifecycle diagram, recognition before the note forms, the `NEEDS_CONTEXT` check, the seed/premises/context rules, branch default, `## Source brief`, `rm -f` with `BRIEF_REMOVED=1`, and the guarded restore.
- Step 8: `WORKFLOW.md` gains `## Human docs` after `## Documentation` (one paragraph, ten lines) and a `Human docs` column in the Artifacts table; `templates/AGENTS.md` gains the line after line 31; `README.md` gains `### Human docs` after `### A plan that ships in parts` (with the brief `cp`, the `/office-hours` call and an opt-out one-liner as fenced commands), a `docs/human/` row in the Layout tree, `human_docs` in the Configuration `modules` row, the Upgrade bullet, and a Doctor bullet; `CHANGELOG.md` `## 1.5.0 — 2026-09-23`; `VERSION` 1.5.0.
- Verification: `python3 -m pytest tests/test_skill_lint.py -q` → 439 passed; full suite `python3 -m pytest tests payload/tests -q` → **1097 passed in 112.91 s** (1057 baseline + 40: 10 CLI cases, 6 lint cases, 16 template cases across the four per-file lints, 8 cases for the two new references). Negative control for the lookup test, by hand: the block with `not_on_base() { cat; }` (Eng review 1's version), with `head -1` for `sort | tail -1`, and without the `[ -n "$PR_URL" ]` guard each fail, under bash and `zsh -f`, at the assertion written for that bug (part 2's compare-URL lookup, the newer of two pending entries, and the empty `PR_URL`). The README's opt-out one-liner, run in a scratch repo, sets `false` and keeps a trailing newline; the next `upgrade` prints `skip  human docs off (modules.human_docs = false)`.
- Deviations: (1) **`tests/test_skill_lint.py::bash_blocks` reads indented fences** (the fence's own indent is stripped). The lookup block sits inside step 8's numbered item 4, as the plan lays it out, and the column-0 pattern did not see it. The same gap hid three existing indented blocks (`update-docs/SKILL.md`, `execute-plan/SKILL.md`, `_shared/dashboard.md`) from 1.4.1's array-completeness lint; none passes an array, so the lint still holds, and it now sees them. (2) The Rules also derive `{{PR_URL}}` and `{{BRANCH}}` (one sentence each), which §2's prose used but did not define; the slot-agreement test needs every template slot derived. (3) The brief's text in `## Source brief` goes inside a four-backtick fence, so its `#` and `##` headings do not become the plan's; §4 left the form open. (4) A staged-but-never-committed brief makes `git checkout HEAD --` fail on abandon; the reference says the report names that and points at `## Source brief`. (5) Ship step 9's sentence listing what the record commit holds now names the human-docs files (§3 said step 9 is unchanged; this is its description, not its commands). (6) README's Doctor list gains one bullet so its "It checks:" list stays true (§8 listed the other README edits, not this one). (7) The step 1 flag check is a `python3 -c` one-liner rather than prose, so "on" means JSON `true` exactly, as the installer reads it.
- Observation for review, not changed: `sort | tail -1` orders `D-feat-x-2.md` before `D-feat-x.md` (`-` sorts below `.`), and `-10` before `-9`. Through the procedure two unmerged pending entries for one branch cannot share a date (a `-N` name is made only when the base name is merged or belongs to another pull request), so the order only matters when no base ref can be read, the accepted pre-filter behaviour.

### Step 9 — verification before PR-F (2026-09-23T03:09:27Z)
- Full suite, after the two reference fixes below: `python3 -m pytest tests payload/tests -q` → **1097 passed in 112.16 s** (baseline 1057 at `311ffbd`).
- `python3 bin/framework init <temp repo> --dry-run` on a fresh `git init`: the five human-docs lines (`plan  write docs/human/README.md`, three `plan  create docs/human/<sub>/`, `plan  .gitignore append: .obsidian/`), and nothing but `.git` in the directory afterwards.
- Line budgets: `office-hours/SKILL.md` **500** (at the lint's limit, as planned); `ship/SKILL.md` 458.
- Critical paths 6, 7, 8 and 10, by hand (driver kept in the session scratchpad as `hand_runs.py`). Each scratch repo is made by `framework init` from this branch's payload, and every shell step is the block the installed skill text ships, extracted from the scratch repo's `.agents/skills/…` and run under `zsh -f`. The prose an agent would write is stand-in text; the mechanics follow the references as written. Results:
  - **CP 10 (two-part ship):** PR1 without `gh` wrote `2026-09-23-feat-x.md`, titled `(part PR1)` with `[PR pending](<compare URL>)`. After a squash merge into `master` and `master` merged back, PR2 the same UTC day found nothing (part 1's merged entry dropped by the base filter) and named `2026-09-23-feat-x-2.md`, titled `(part PR2)`. The hand-back of `…/pull/12` found `-2` through lookup (b) and gave it the real number; a re-run found it through (a) and rewrote it in place, with no `-3`. Part 1's entry is byte-identical (`git diff master -- …` empty; `git diff --diff-filter=M master -- docs/human/log/` empty); exactly one entry names `…/pull/12)`; the page's History has two rows, newest first, with distinct text.
  - **CP 7 (existing page):** the second ship kept `## My notes` (below History) and `## Custom` (between owned sections), dropped `### detail` with `## What it does`, and prepended a History row. With `## What changed in this ship` renamed by hand, the third ship refilled the page whole and carried `## Custom`, `## Changes` and `## My notes` below History, saying so.
  - **CP 6 (brief):** a missing path printed `NEEDS_CONTEXT: no brief at docs/human/briefs/no-such-brief.md`. The seed is the `## What I want` text verbatim, and the premise came from `## Do not reopen`. `## Source brief` sits in a four-backtick fence, so the plan's own headings stay `# Design:`, `## Source brief`, `## Problem Statement`. After approval, `git status` shows `D docs/human/briefs/calendar-sharing.md` with a clean index. Abandon with `BRIEF_REMOVED=1` restored the tracked brief byte-identical. Abandon before approval left an uncommitted edit alone. An untracked brief removed after approval stays gone.
  - **CP 8 (flag off):** ship step 1's check prints `HUMAN DOCS: on` for `true`, and `HUMAN DOCS: off; nothing is written` for `false`, `"false"`, `null` and an absent key; step 8's text says to print it again and write nothing. The installer half (`upgrade` creates nothing and prints one `human docs off` line) is the automated `test_upgrade_respects_human_docs_off[False|"false"]`.
- Fixed from what the hand runs showed, both in references and both inside the plan's intent: (1) `brief-intake.md` said the seed was the section "its heading line through…"; it now says "the lines under its heading", matching the test artifact's "the `## What I want` text". (2) `human-docs.md` item 5's anchors-missing refill now keeps the rows of a `## History` that is still there; read literally, "fill whole" dropped them from the page.
- Transcript:

```

=== CP 10: two-part ship, hand-driven steps 7 and 8
  PR1 PR_URL (no gh) = https://github.com/o/r/compare/master...feat-x?expand=1
  PR1 lookup -> none; LOG_FILE = 2026-09-23-feat-x.md
  PR1 page: ['new page']
  ┌─ docs/human/log/2026-09-23-feat-x.md
  │ # 2026-09-23 — Weekly digest (part PR1)
  │ 
  │ [PR pending](https://github.com/o/r/compare/master...feat-x?expand=1) · branch `feat-x` · [weekly-digest](../features/weekly-digest.md)
  │ 
  │ Send the digest on Mondays.
  │ 
  │ ## What changed
  │ 
  │ - Send the digest on Mondays.
  PR2 (no gh) lookup -> none  (part 1's merged 2026-09-23-feat-x.md must not come back); LOG_FILE = 2026-09-23-feat-x-2.md
  PR2 page: ['History: row prepended']
  PR2 hand-back https://github.com/o/r/pull/12: lookup -> 2026-09-23-feat-x-2.md
  PR2 page: ['History: first row replaced (re-run)']
  PR2 re-run lookup -> 2026-09-23-feat-x-2.md
  PR2 re-run page: ['History: first row replaced (re-run)']
  log folder: ['2026-09-23-feat-x-2.md', '2026-09-23-feat-x.md']
  part 1 entry byte-identical: True; git diff master -- it: ''
  modified vs master under log/: ''
  entries naming https://github.com/o/r/pull/12): 1
  ┌─ docs/human/log/2026-09-23-feat-x-2.md
  │ # 2026-09-23 — Weekly digest (part PR2)
  │ 
  │ [PR #12](https://github.com/o/r/pull/12) · branch `feat-x` · [weekly-digest](../features/weekly-digest.md)
  │ 
  │ Let each person pick the day.
  │ 
  │ ## What changed
  │ 
  │ - Let each person pick the day.
  ┌─ docs/human/features/weekly-digest.md
  │ # Weekly digest
  │ 
  │ As of 2026-09-23 · [PR #12](https://github.com/o/r/pull/12) · [plan](../../../.agents/plans/features/feat-x/feat-x-plan-20260923-000000.md)
  │ 
  │ ## What it does
  │ 
  │ Families get a weekly email of the week's tasks, on the day each person picks.
  │ 
  │ ## What changed in this ship
  │ 
  │ - Let each person pick the day
  │ 
  │ ## History
  │ 
  │ - 2026-09-23 — [Weekly digest (part PR2)](../log/2026-09-23-feat-x-2.md)
  │ - 2026-09-23 — [Weekly digest (part PR1)](../log/2026-09-23-feat-x.md)

=== CP 7: existing page rewrite, hand-driven step 8
  ship 1: ['new page']
  ship 2: ['History: row prepended']
  '## My notes' survives: True; '## Custom' survives: True; '### detail' gone: True
  History rows, newest first: ['- 2026-09-23 — [Recipe import from a photo](../log/2026-09-23-recipe-import-2.md)', '- 2026-09-23 — [Recipe import](../log/2026-09-23-recipe-import.md)']
  ship 3 (a person renamed an owned heading): ["anchors missing ['## What changed in this ship']: refilled whole; carried below History: ['## Custom', '## Changes', '## My notes']"]
  ┌─ docs/human/features/recipe-import.md
  │ # Recipe import
  │ 
  │ As of 2026-09-23 · [PR #5](https://github.com/o/r/pull/5) · [plan](../../../.agents/plans/features/recipe-import/recipe-import-plan-20260923-000000.md)
  │ 
  │ ## What it does
  │ 
  │ Paste a link or a photo and the recipe is saved.
  │ 
  │ ## What changed in this ship
  │ 
  │ - Fix photo rotation
  │ 
  │ ## History
  │ 
  │ - 2026-09-23 — [Photo rotation fix](../log/2026-09-23-recipe-import-3.md)
  │ - 2026-09-23 — [Recipe import from a photo](../log/2026-09-23-recipe-import-2.md)
  │ - 2026-09-23 — [Recipe import](../log/2026-09-23-recipe-import.md)
  │ 
  │ ## Custom
  │ 
  │ A person's section between owned ones.
  │ 
  │ ## Changes
  │ 
  │ - Import a recipe from a photo
  │ 
  │ ## My notes
  │ 
  │ Kept by hand.

=== CP 6: brief intake by hand
  missing path: 'NEEDS_CONTEXT: no brief at docs/human/briefs/no-such-brief.md'
  present path: '' (empty = recognized)
  seed brief (## What I want, verbatim): '\nLet a family share one calendar with a grandparent who does not use the app.\nDone: they see the week, read-only.\n\n'
  premises from ## Do not reopen: ['Read-only for outside viewers.']; branch default: calendar-sharing
  plan's own headings outside the fence: ['# Design: Calendar sharing', '## Source brief', '## Problem Statement']
  after approval: exists=False; git status: 'D docs/human/briefs/calendar-sharing.md'; index clean: ''
  abandon, tracked, BRIEF_REMOVED=1: restored=True identical=True
  abandon before approval, tracked with an uncommitted edit: edit survives=True
  untracked brief removed after approval, then abandoned: restored=False (expected False; its text lives in ## Source brief)

=== CP 8: flag off
  on:  HUMAN DOCS: on
  false: HUMAN DOCS: off; nothing is written
  "false": HUMAN DOCS: off; nothing is written
  null: HUMAN DOCS: off; nothing is written
  absent: HUMAN DOCS: off; nothing is written  (the installer turns an absent key on at upgrade)
  step 8 says, when off: True
```

### Step 10 — PR-F opened (2026-09-23T03:11:41Z)
- User's OK in session (question answered: "Commit, push, open PR"). Commit `7200cb6` on framework `human-docs` (parent `311ffbd`), 18 files, +977/−26; pushed to `origin/human-docs`; pull request https://github.com/willdoucet/framework/pull/13 against `main`, open. Merging it is the operator's step.
- The plan's Files section says "Sixteen files, six of them new", but its own list names 18 (seven top-level and payload files, four templates, four skill files, `init-project/SKILL.md`, two test files); 18 is what shipped. Six new files, as planned.
- Lesson candidates for step 12 (todo-app `LESSONS.md`): (1) a lint that picks its input by pattern silently skips what the pattern misses. `bash_blocks`' column-0 fence regex hid every indented bash block from 1.4.1's array-completeness lint, and it surfaced only because a new test found 0 blocks. When a test finds nothing, check the selector before the thing selected. (2) "Fill it whole" in a rewrite rule is ambiguous about the sections that survived; name what happens to each owned section.

### Resume — 2026-09-28T20:40:20Z
- Session resumed with `/execute-plan`. Metadata at resume: `{"implementation_status": "blocked", "plan_kind": "feature", "plan_mode": "feature", "reason": "Steps 1-10 done in ../framework: PR-F https://github.com/willdoucet/framework/pull/13 (1.5.0) is open. PR-T (steps 11-12, the upgrade here) waits until framework origin/main reads VERSION 1.5.0; merge PR-F, then resume with /execute-plan.", "reason_by": "execute-plan", "registry_key": "plan:human-docs", "review_status": ["eng-reviewed"], "risk_tags": ["infra"], "ui_scope": false, "workflow_status": "implementing"}`. Gate: `--next` named `/execute-plan`, `unreadable` 0.
- Blocker resolved: PR-F https://github.com/willdoucet/framework/pull/13 `MERGED` 2026-09-28T20:27:54Z as `f6b3577`; framework `origin/main` `VERSION` 1.5.0; the local framework checkout on `main` at `f6b3577`, clean. The start sync set `implementing` and cleared the reason.
- Reconcile: no signal fired (no commit or pull request on the registry entry, no `shipped_parts`, not `partially-shipped`); boxes 1–10 stand, confirmed by PR-F's merge.

### Step 11 — catch-up, upgrade, doctor, host suite (2026-09-28T20:52:12Z)
- **§11 step 1, catch-up.** `human-docs` was at `1087f30`, 6 behind `origin/master` `5825531` (#60–#65, M8) and 0 ahead, so the catch-up was a fast-forward, not a merge commit as the plan expected. User-approved in session (after first choosing to run it themselves). Patch dance over three files, not LESSONS alone: `TODOS.md` and `review-log.jsonl` were uncommitted too and master touched both. Rehearsed first in a throwaway detached worktree at `origin/master` (removed after), then: 42-line patch saved to the session scratchpad; `git checkout --` the three; `git merge --ff-only origin/master` → `5825531`; `git apply --3way` → TODOS and review-log clean, LESSONS one conflict (master's six 2026-09-21 Decisions rows vs. this branch's 2026-09-22 and 2026-09-23 rows), resolved by keeping both, master's first; `git reset -q --` the three so they are unstaged again. Checks: `git merge-base --is-ancestor 1087f30 HEAD` exits 0; `HEAD` = `origin/master` = `5825531`; `.agents/config.json` read `"framework_version": "1.4.1"`; the added lines are identical to the saved patch (`diff` of the `+` lines empty); the review log parses (187 lines).
- The first attempt at the dance passed the three paths as one zsh variable (`$F`); zsh does not word-split, so `git diff` wrote a 0-line patch and `git checkout` refused the one-word pathspec. Nothing changed (`HEAD` `1087f30`, same 15 insertions). The second attempt spelled the paths out and refused to continue unless the patch had 42 lines. Recorded in LESSONS at step 12.
- **Upgrade.** `python3 <the framework checkout's literal absolute path>/bin/framework upgrade <the worktree's literal absolute path> --dry-run`: header named the worktree; `installed 1.4.1 -> 1.5.0`; 12 `plan payload` lines (WORKFLOW.md, config.example.json, init-project, office-hours SKILL + `brief-intake.md`, ship SKILL + `human-docs.md`, templates/AGENTS.md, the four `templates/human/*`), then `config modules.human_docs = true`, `write docs/human/README.md`, three `create docs/human/<sub>/`, `config doc_map.exempt += docs/human/**`, `.gitignore append: .obsidian/`; `git status` unchanged afterwards. Apply printed the same 19 lines as `done`, exit 0; the main checkout's `git status` was empty before and after.
- **Idempotence (success criteria 3 and 9).** Second `upgrade`: header plus `ok installed 1.5.0 -> 1.5.0` only; 0 lines mention `docs/human` or `.obsidian`; `config.json`, `.gitignore` and every file under `docs/human/` byte-identical to after the first run (`cmp`, `shasum`); `.gitignore` holds exactly one `.obsidian/` line.
- **Doctor.** `framework doctor <literal path>`: `0 failure(s), 1 warning(s)`; the warning is `registry plan:human-docs: implementing on branch human-docs` (this plan, mid-execution); no human-docs warning; `helper tests pass`.
- **Host suite.** `python3 -m pytest .agents/tests -q` → **636 passed in 82.34 s**.
- **Diff (§11 step 3).** The 12 installed payload files are byte-identical to framework `f6b3577`'s `payload/` (`cmp`); `office-hours/SKILL.md` is 500 lines. `.agents/config.json`: `"docs/human/**"` appended after `"infra/*.md"` in `doc_map.exempt`, `framework_version` 1.4.1 → 1.5.0, `"human_docs": true` in `modules`. `.agents/manifest.json`: hashes of the changed and new files, version, `generated_at`. `.gitignore`: `.obsidian/` as its last line. `docs/human/README.md` renders `# todo-app — human docs` and `todo-app-notes/`, no `{{`; three `.gitkeep`s. Nothing from 1.4.x appears.
- `doc-guard --explain`: `docs/human/features/x.md`, `.gitignore`, `AGENTS.md` and `.agents/skills/ship/SKILL.md` all print `exempt` (success criterion 2's check, on this repository).
- Deviations: the catch-up was a fast-forward and covered three files (above). Docker backend and frontend suites not run: nothing under `backend/`, `frontend/` or `infra/` differs from `origin/master`; CI runs them on the pull request.

### Step 12 — hand edits (2026-09-28T20:53:58Z)
- `AGENTS.md`: the template's line "Plain-English pages for people live in `docs/human/` (see its README)." added directly after the "Plans live in …" line, where `templates/AGENTS.md` puts it (the installer never rewrites an existing `AGENTS.md`).
- `.agents/docs/LESSONS.md` (on top of the two uncommitted Decisions rows from office-hours and Eng review 2, both present):
  - Patterns That Work: the patch-dance bullet (the canonical rule) gains every uncommitted file master touched, checking the saved patch before the discard, literal paths under zsh, and `git reset -q --` after `--3way`; a new bullet for scoping a rewrite verb in skill text ("fill it whole").
  - Test isolation gotchas: new subsection "A lint that selects its input by pattern passes on what the pattern misses".
  - Corrections Log: 2026-09-28, self, the zsh `$F` pathspec.
  - Bug Log: 2026-09-23, framework `tests/test_skill_lint.py::bash_blocks`, the column-0 fence pattern.
- Verification: `git diff -U0` shows one `AGENTS.md` insertion and five LESSONS insertions (18+/1−); each of the Corrections Log, Bug Log and Decisions tables keeps 5 columns in every row (script check).
- Deviation from assumption 5 as stated: the "fill it whole" lesson is a Patterns That Work bullet, as stated; the patch-dance extension and its Corrections Log row are additions this run taught.

## Doc impact

- Steps 1–10 changed files in `../framework` only; no todo-app doc section is touched by them.
- PR-T (steps 11–12), expected: `.agents/**` (upgrade output) and `docs/human/**` (scaffold) are doc-map exempt; `.gitignore` gains `.obsidian/` (exempt); `AGENTS.md` gains the one line from the template (exempt path, but a documented surface: `/update-docs` decides whether it counts, per plan §11 step 5); `LESSONS.md` gains the rows step 12 records. No mapped code path changes, so the plan's expected `DOC IMPACT` is `none` with the §11 step 5 trailer, unless `/update-docs` counts `AGENTS.md`.
- Steps 11–12, actual (2026-09-28): `doc-guard --explain` prints `exempt` for `docs/human/**`, `.gitignore`, `AGENTS.md` and `.agents/skills/**`; the rest of the diff is `.agents/**` (upgrade output, plan, summary, test artifact, registry entry, review log) and `.agents/docs/LESSONS.md` / `TODOS.md`. No doc records the framework version (grep of `TECH_STACK.md`, `IMPLEMENTATION_PLAN.md`, `PRD.md`, `APP_FLOW.md`), so the 1.4.1 → 1.5.0 bump leaves no product doc stale.

## Update-docs conclusion

Run 2026-09-28 at the end of step 12; the index is staged (`git add -A`), nothing committed.

```
DOC SYNC REPORT — default — human-docs vs master — 2026-09-28

| Doc | Section | Action | Summary |
|---|---|---|---|
| AGENTS.md | Project Overview | updated | new top-level docs/human/ gets its one-line pointer ("Plain-English pages for people live in `docs/human/` (see its README).") after the plans/state/vault line; written at /execute-plan step 12, verified here as the step-5 structure pointer |
| development-commands.md | Framework Helper Tests | no change | no command, service, port or env var changed; `python3 -m pytest .agents/tests -q` still correct (636 passed) |
| TECH_STACK.md | Dependencies | no change | no manifest changed; no doc records the framework version, so 1.4.1 → 1.5.0 leaves nothing stale |
| IMPLEMENTATION_PLAN.md | roadmap | no change | workflow plans carry no roadmap row (precedent: workflow-rereview-utc); plan not shipped |
| LESSONS.md | Corrections Log, Bug Log, Patterns, Test isolation, Decisions | no change | the branch's rows were written by /office-hours, /plan-eng-review and /execute-plan step 12; this skill does not edit them |
| TODOS.md | P3 entries | no change | P3 "/quickfix writes to docs/human/" written at office-hours |
| config.json | doc_map | no change | `docs/human/**` added to exempt by the framework installer; no unmapped directory |

Guard: doc-guard --staged --dry-run -> staged changes touch no documented areas
Questions: 0 asked
Unmapped: none
Placeholders: REVIEW_CHECKLIST.md:410 `${{ secrets.NAME }}` is GitHub Actions syntax, not a template slot

DOC IMPACT: updated 1 docs
```

This takes the plan's §11 step 5 fork: `AGENTS.md` counts as a documented surface (it now describes a new top-level directory), so the verdict is `updated` and the record commit needs no `Docs:` trailer. The plan's fallback trailer ("no documented surface changed") would be inaccurate with that line in the diff. Every changed path is doc-map `exempt`, so `doc-guard` passes either way.

### `/ship` run — 2026-09-29

Re-run at ship step 4, after the 1.6.1 bump and both final reviews; same verdict.

```
DOC SYNC REPORT — default — human-docs vs master — 2026-09-29

| Doc | Section | Action | Summary |
|---|---|---|---|
| AGENTS.md | Project Overview | updated | the one-line `docs/human/` pointer (written at /execute-plan step 12) is present after the plans/state/vault line and still correct |
| development-commands.md | Framework Helper Tests | no change | no command, service, port or env var changed; `python3 -m pytest .agents/tests -q` still correct (636 passed) |
| TECH_STACK.md | Dependencies | no change | no manifest changed; no doc records the framework version, so 1.4.1 → 1.6.1 leaves nothing stale |
| IMPLEMENTATION_PLAN.md | roadmap | no change | workflow plans carry no roadmap row (precedent: workflow-rereview-utc, workflow-review-resolution) |
| LESSONS.md | Corrections Log, Bug Log, Patterns, Test isolation, Decisions | no change | the branch's rows were written by /office-hours, /plan-eng-review, /execute-plan step 12 and /final-review; this skill does not edit them |
| REVIEW_CHECKLIST.md | Framework helpers | no change | its three new checks were written by /review-implementation and /final-review 2 |
| TODOS.md | P3 entries | no change | P3 "/quickfix writes to docs/human/" written at office-hours |
| config.json | doc_map | no change | `docs/human/**` exempt (framework installer); no unmapped directory |

Guard: doc-guard --staged --dry-run -> staged changes touch no documented areas
Questions: 0 asked
Unmapped: none
Placeholders: REVIEW_CHECKLIST.md:410 `${{ secrets.NAME }}` is GitHub Actions syntax, not a template slot

DOC IMPACT: updated 1 docs
```

## Completion

- Session ended 2026-09-23T03:11:41Z: **STATUS BLOCKED** (waiting on an operator step, not a failure). Steps 1–10 done with evidence; PR-F https://github.com/willdoucet/framework/pull/13 (framework 1.5.0) is open. Steps 11–12 (PR-T: the upgrade into this worktree, `doctor`, the `.agents/tests` suite, the `AGENTS.md` line and the LESSONS rows) wait until framework `origin/main` reads `VERSION` 1.5.0, per the test artifact's deployment guard. Resume: merge PR-F, then run `/execute-plan` on `human-docs`.
- Tests so far: framework `python3 -m pytest tests payload/tests -q` → **1097 passed** on `7200cb6` (1057 at `311ffbd`). todo-app host suite and Docker suites not run in this session: nothing in todo-app changed except this summary and the plan's state.
- `/update-docs` has not run: it runs when the last box is ticked (after step 12).

### Completed 2026-09-28T20:57:14Z — STATUS DONE
- **Built.** Framework 1.5.0 (PR-F, https://github.com/willdoucet/framework/pull/13, merged as `f6b3577`) teaches `/ship` to write a plain-English feature page and a per-pull-request log entry under `docs/human/`, and `/office-hours` to take a parked brief from `docs/human/briefs/`. PR-T brings it into todo-app: the branch was fast-forwarded to `origin/master` `5825531`, then `framework upgrade` installed the 12 changed payload files, turned `modules.human_docs` on, scaffolded `docs/human/` (README and three folders), exempted `docs/human/**` from the doc map and ignored `.obsidian/`. `AGENTS.md` points at the new folder; LESSONS carries what the run taught.
- **Tests.** Host `python3 -m pytest .agents/tests -q` → **636 passed** (82.34 s after the upgrade, 88.31 s after step 12). `framework doctor` → 0 failures, 1 warning (this plan `implementing`, expected). Framework suite on PR-F: 1097 passed (step 9). Docker backend and frontend suites not run: no path under `backend/`, `frontend/` or `infra/` differs from `origin/master` (assumption 4, stated and not corrected); CI runs them on the pull request.
- **Success criteria covered here:** 3 (dry run lists every write; second upgrade silent; doctor 0 failures), 9 (exactly one `.obsidian/` line, byte-identical after the second run), 2's `doc-guard --explain … exempt` on this repository. Criteria 4 and 5 (the first real human-docs write) belong to `/ship` of PR-T, per §11 steps 6–8: diff the worktree's `ship` skill against the main checkout's first, and answer B ("this pull request completes the plan") if step 1 asks about parts.
- **Test-artifact gaps:** none new in PR-T. Critical path 3 (the first real ship) and the completion gate "`/ship` lands both files in the record commit" remain for `/ship`.
- **Deviations from the plan:** (1) §11 step 1's catch-up was a fast-forward (0 commits ahead), not a merge commit; (2) its patch dance covered `TODOS.md` and `review-log.jsonl` as well as LESSONS; (3) `/update-docs` returned `updated 1 docs` (`AGENTS.md`), the plan's §11 step 5 alternative, so no `Docs:` trailer is needed; (4) steps 1–10's deviations are in their notes above.
- **Index:** staged by `/update-docs` (`git add -A`); nothing committed. `/ship` owns the commits.

### Framework 1.5.0 → 1.6.1 bump before `/ship` (2026-09-29T19:08:19Z)
- **Why.** Framework `origin/main` reached 1.6.1 after step 11 (#17 1.6.0: an optional companion folder `docs/human/briefs/<slug>/` beside a parked brief, moved to `sources/<slug>/` in the plan's directory on approval; #20 1.6.1). The user asked for the bump before `/ship` so this pull request does not land a release behind. **This branch installs framework 1.6.1; the pull request's title and Summary say 1.6.1.** The feature itself was built and released as 1.5.0 (PR-F, https://github.com/willdoucet/framework/pull/13).
- **Source.** The framework checkout on `main` at `da8aaa0` = `origin/main`, clean, `VERSION` 1.6.1. `git describe --tags` prints `v1.6.1-2-gda8aaa0`: the two commits after the tag change only the framework repository's own `.agents/config.json` and `.agents/manifest.json` (its self-upgrade), nothing under `payload/`.
- **Upgrade.** `framework upgrade <the worktree's literal absolute path> --dry-run`: the header named the worktree; `installed 1.5.0 -> 1.6.1`; four `plan payload` lines. Apply: the same four as `done`, exit 0; the main checkout's `git status` stayed empty. No migrations between the two versions.
- **Diff.** Exactly the four expected payload files, `WORKFLOW.md`, `skills/office-hours/references/brief-intake.md`, `templates/human/README.md` and `templates/human/brief.md`, each byte-identical to framework `v1.6.1:payload/` (`cmp`); framework `git diff f6b3577 v1.6.1 -- payload` names the same four. Besides them: `config.json` `framework_version` 1.5.0 → 1.6.1, and `manifest.json` (four hashes, version, `generated_at`). Unchanged: `modules.human_docs: true`, `docs/human/**` in `doc_map.exempt`, and the `.gitignore` lines (`.obsidian/`, `docs/human/briefs/*`, `!docs/human/briefs/.gitkeep`). The `briefs/*` line also keeps a companion folder local until it is committed with `git add -f`, the same as its brief.
- **Hand edit.** `docs/human/README.md` is written only when absent, so the upgrade left its `briefs/` row at the 1.5.0 text. With the user's OK, the row gained the 1.6.1 template's sentence about the companion folder; the file now equals the 1.6.1 template rendered for todo-app (`diff` empty). The installer's gap (same root cause as item 14 of https://github.com/willdoucet/framework/issues/16) is reported there with the user's OK: https://github.com/willdoucet/framework/issues/16#issuecomment-5897113421.
- **Doctor.** `framework doctor <literal path>`: 0 failures, 1 warning (`registry plan:human-docs: ready-for-review on branch human-docs`, expected).
- **Tests.** `python3 -m pytest .agents/tests -q` → **636 passed** (77.66 s); `python3 -m pytest infra/tests -q` → **170 passed** (0.86 s); `docker-compose exec frontend npm run test:run` → **632 passed**, 61 files (6.27 s); `docker-compose exec api uv run pytest` → **1059 passed, 3 skipped** (11.09 s). The Docker suites ran in the main checkout's dev stack, whose bind mounts hold `master` `5825531`, this branch's `HEAD`; nothing under `backend/` or `frontend/` is changed here. The first backend run, alongside the frontend run, reported 95 failed and 264 errors in 55.66 s; `tests/integration/test_uploads_api.py` alone then passed 18/18 and the full rerun above was clean. That points at the shared `todo_app_test` database, not this branch.

### Final review — 2026-09-29 UTC

- **Status:** DONE_WITH_CONCERNS; review result `issues_open`. Three findings, none critical:
  two fixed, one open pending the user's decision. No commit, push, or `/ship`.
- **Independence:** Codex / GPT-6 versus the first review's Claude Code / Claude Opus 5.5.
- **Scope and plan completion:** all 12 pre-ship implementation steps have evidence; no
  partial or missing implementation step. Steps 1–10 were delivered by framework PR-F;
  steps 11–12 are the installed payload, scaffold, config, and project pointers. The
  subsequent 1.6.1 bump and rendered README update were authorized and recorded above.
  Success criteria 4–5 and critical path 3 remain the first real `/ship`'s responsibility.
- **Fixed:** replaced all three added lines containing machine-specific home paths or
  home-directory shortcuts with descriptive placeholders. Updated the registry title
  through `obsidian-workflow`; its reason is byte-for-byte unchanged. Added explicit
  current PR title/Summary copy and a plan pointer to it, retaining every historical
  release reference.
- **Open:** companion PNGs are omitted by `git add -A` after approval moves them into
  plan sources, because the repository ignores PNGs globally. The fresh-context
  adversarial subagent reproduced this with the installed approval block under zsh.
  The primary reviewer independently reproduced the staging failure and tested
  `!.agents/plans/**/sources/**/*.png`: two plan PNGs (direct and nested) stage,
  while a parked companion PNG and an ordinary screenshot stay ignored. The proposed
  exception is not applied; the apply-or-defer question is pending. This is a new
  companion-folder finding, not one of the earlier accepted upstream deferrals.
- **Adversarial synthesis:** large tier. One new actionable subagent finding (PNG
  staging), independently confirmed. The subagent hit its usage limit before its final
  synthesis; the primary reviewer completed the comparison. The destination-collision
  case was not counted as a new defect: the reference explicitly leaves the folder
  parked and reports DONE_WITH_CONCERNS. Shared older concerns (epic brief provenance,
  unset lookup context, regex branch lookup, and interrupted-ship resumption) already
  have accepted upstream deferrals. No upstream message was sent.
- **First-review comparison:** its three local fixes remain present (file count,
  cross-date sorting qualifier, Obsidian ignore comment), as does the parked-brief
  mitigation. Four shared historical concerns remain covered by the accepted upstream
  issue; three findings are unique to this pass (including the two user-requested fixes).

Verification:

```text
Installed payload
  146/146 manifest hashes match
  12/12 changed payload files equal upstream v1.6.1
  Rendered docs/human/README.md equals the installed template
Framework helpers
  636 passed in 62.09 s; no skipped tests
Human-docs and companion behavior (upstream v1.6.1 scratch checkout)
  48 passed, 436 deselected in 11.38 s
  Installer on/off, idempotence, dry-run, doctor, slug validation,
  log lookup under bash/zsh, companion approval/abandon and guards
Public-record and state checks
  0 added-line home-path matches after corrections
  Registry reason unchanged; current title says framework 1.6.1
  Historical release occurrence counts preserved
Documentation
  All 28 changed paths doc-map exempt; no application surface changed
  doc-guard --range master..HEAD: no commits in range
  doc-guard --staged --dry-run: staged changes touch no documented areas
```

The standard host pytest command crashed before collection in this machine's native
`readline` extension, both inside and outside the sandbox. The successful runs disabled
only that optional import, keeping pytest capture and every test enabled:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys; sys.modules["readline"] = None; import pytest; raise SystemExit(pytest.main([".agents/tests", "-q", "-p", "no:cacheprovider"]))'
```

The upstream run used the same wrapper on a scratch archive of `v1.6.1`, selecting
`tests/test_cli.py tests/test_skill_lint.py -k 'human_docs or brief or companion or feature_slug or approval or abandon'`.
The archive, tests, and fixtures introduced no files into this repository. No new persistent
tests were needed for the mechanical record fixes. The existing hand-run page-writing
evidence remains a manual check; this review does not claim a full automated skill harness.
Application suites were not repeated: application and infrastructure code are unchanged,
and their earlier same-day results remain recorded above. Gitignored workspace files were
not opened or staged.

### Final review 2 — 2026-09-29 UTC

- **Status:** DONE_WITH_CONCERNS; review result `clean`. Claude Code / Claude Opus 5.5, re-run
  at the user's request (same harness and model as the implementation review; warned).
- **Fixed (user decisions):** `.gitignore` gains `!.agents/plans/**/sources/**/*.png`, which
  closes the first final review's open item. The log-entry title for this ship names 1.6.1
  (see Current PR-T shipping copy). **Fixed:** the test artifact's `.obsidian` invariant.
  REVIEW_CHECKLIST gains a check for ignore rules that drop moved files.
- **Deferred with approval:** 11 framework 1.6.x findings, in
  https://github.com/willdoucet/framework/issues/16#issuecomment-5898630504. A companion
  folder holding a directory the repository ignores (`screenshots/`, `build/`) still loses
  those files on approval until that comment's item 1 lands.
- **Evidence:** 12 changed payload files equal `v1.6.1`; 146/146 manifest hashes match;
  `framework doctor` (v1.6.1) 0 failures; `.agents/tests` 636 passed; `infra/tests` 170
  passed; `doc-guard` range, staged and worktree pass; `git check-ignore` confirms plan
  `sources/` PNGs are tracked, while parked briefs, their folders, `.DS_Store` and other
  PNGs stay ignored.
