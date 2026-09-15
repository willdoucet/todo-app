# Design Source of Truth section

Loaded by `plan-design-review` at step 8E. Add the section near the top of the plan body,
after the problem statement and constraints (or the equivalent intro sections) and before the
per-component implementation sections. On a rerun, update it in place; never append a second
copy. The **Approach** value is parsed by `/execute-plan` and `/review-implementation`; use
one of the three spellings below exactly.

Artifact paths are relative to the plan file, so they survive a move of the plan folder.

## Prototype bundle

```markdown
## Design Source of Truth

- **Approach:** Prototype bundle
- **Prototype (live):** <handoff URL>
- **Prototype (offline):** ./prototype/<entry point, usually index.html>
- **Handoff prompt:** <one-line summary copied from the bundle README>
- **Linked codebase scope:** <the frontend directory named by `layout.frontend_dir` in config>
- **Design system pin SHA:** <DESIGN_PIN_SHA>
- **Captured at:** <TIMESTAMP from ctx>
- **Sync state at capture:** clean | stale (drift accepted)
```

When the user chose `skip`, the section carries `**Prototype:** DEFERRED, to be captured
before /execute-plan runs` in place of the two prototype lines; the pin SHA is still recorded.

## HTML mockups

```markdown
## Design Source of Truth

- **Approach:** HTML mockups
- **Mockups:**
  - <ComponentName> → ./mockups/<component-slug>-option-<letter>.html
  - <ComponentName> → ./mockups/<component-slug>-option-<letter>.html
- **Design system pin SHA:** <DESIGN_PIN_SHA>
- **Captured at:** <TIMESTAMP from ctx>
```

One line per non-trivial component from 8A, pointing at the single selected option.

## None

```markdown
## Design Source of Truth

- **Approach:** None
- **Rationale:** <the user's one- or two-sentence reason from 8C-C>
- **Captured at:** <TIMESTAMP from ctx>
```

## Rules

- Every non-trivial item identified in 8A is accounted for: a prototype that covers it, a
  mockup line, or the rationale for none.
- The pin SHA is the last commit touching the watched design files, printed by
  `"$BIN/design-sync-check" --pin-sha`: `design_watched_files` in config, or
  `$DOCS_DIR/FRONTEND_GUIDELINES.md` plus the token source file it names (passed as arguments)
  when that list is empty. An empty pin is never recorded. Downstream skills compare it with
  the current SHA of the same files and warn on drift; they never block.
- When both `mockups/` and `prototype/` exist under the plan folder, this section is the
  single statement of which is current; the other is history.
