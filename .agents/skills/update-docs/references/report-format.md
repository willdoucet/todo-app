# Doc sync report

Printed at the end of every run. Callers paste it verbatim into the summary file under
`## Update-docs conclusion`, into the quickfix log, and into the pull request body, so the
shape is fixed.

```
DOC SYNC REPORT — <default | full> — <branch> vs <base branch> — <utc-date>

| Doc | Section | Action | Summary |
|---|---|---|---|
| BACKEND_STRUCTURE.md | API Endpoints | updated | added POST /items/{id}/icon; removed PUT /items/{id}/image |
| TECH_STACK.md | Dependencies | updated | object-storage client 1.4.2 added (backend, integrations) |
| APP_FLOW.md | Screen Inventory | no change | /settings/storage already listed with its auth requirement |
| PRD.md | Feature Specifications | asked (declined) | code allows 10 MB uploads, doc says 5 MB; user kept the doc, drift recorded |
| IMPLEMENTATION_PLAN.md | Phase 7 | updated | M3 row: shipped 2026-09-09, pull request #41; status 3/5 |
| AGENTS.md | Development Commands | no change | pointer to development-commands.md still correct |
| config.json | doc_map | updated | mapped infra/ to development-commands.md (Full Stack) |

Guard: doc-guard --staged --dry-run -> would pass
Questions: 2 asked, 1 applied, 1 declined
Unmapped: none

DOC IMPACT: updated 3 docs
```

Rows:

- One row per `(doc, section)` visited. The full audit lists every doc in the ownership table,
  including those with no change, so the reader can see the audit covered the set.
- Action is one of `updated`, `no change`, `asked (applied)`, `asked (declined)`.
- Summary states the facts that changed, not the edit mechanics. Short; the diff is the detail.
- `config.json` and `AGENTS.md` get rows when touched. Neither counts as a doc for the total,
  except `AGENTS.md`, which does.

Trailing lines:

- `Guard:` is the decisive line from `"$BIN/doc-guard" --staged --dry-run`, verbatim: `would
  pass`, `staged changes touch no documented areas`, or `would block without a Docs: trailer`
  followed by the docs it named.
- `Questions:` counts asked, applied, declined.
- `Unmapped:` lists top-level directories still unresolved, or `none`.

The last line is exactly one of:

```
DOC IMPACT: updated <n> docs
DOC IMPACT: none - <one-line reason>
```

`<n>` is the number of distinct files edited under `$DOCS_DIR` plus `AGENTS.md`. The reason
after `none -` is pasted by callers after `Docs: n/a - `, so it must be one line a reader of
the git log understands on its own. Good reasons: `test-only change`, `internal rename, no
documented surface changed`, `owning docs already describe this change`, `on the base branch
with no changes`. A reason that does not say why (`no changes needed`) is not acceptable.

When a question was declined and drift remains, the status is `DONE_WITH_CONCERNS`, the row
says `asked (declined)`, and `DOC IMPACT` still counts what was updated.
