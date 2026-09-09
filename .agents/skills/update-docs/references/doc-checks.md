# Doc checks

Loaded by update-docs step 3 and the full audit. For each doc: the shape to preserve, what to
reconcile from the change set in default mode, and what the full audit compares against the
tree. Ownership is in `_shared/docs-contract.md`; the blueprint shapes come from
`/init-project`. Section names are the defaults; the map in `config.json` wins.

## PRD.md

- Shape: feature specifications with user stories, acceptance criteria, and a status; a
  priority table; non-goals; a roadmap of versions; an endpoint index that links.
- Change set: only a feature's status line when its phase ships. Everything else in this doc
  is scope and is a question.
- Full audit: every v1 feature has a phase of the same name in `IMPLEMENTATION_PLAN.md`; the
  data model section links to the schema rather than listing columns; the endpoint index
  links rather than lists. A feature the code contradicts is a question.

## APP_FLOW.md

- Shape: a screen inventory table (route, page, purpose, auth), a page hierarchy, one flow per
  feature with numbered steps and exact error copy, an error-handling section.
- Change set: routes added, removed, or renamed; flows whose steps or decision points changed;
  error copy that changed in the code.
- Full audit: every route in the router has a row and every row has a route; every error
  string the docs quote exists in the code verbatim; every flow's pages exist.

## TECH_STACK.md

- Shape: grouped dependency tables with exact versions; development tools; infrastructure
  with services, ports, env var names, CI jobs, deployment targets; version constraints.
- Change set: manifest lines and their lockfile versions; CI jobs; env var names; a service
  or port.
- Full audit: every dependency in each manifest appears with the lockfile version and nothing
  listed is absent from a manifest; CI jobs match the workflow files job for job; env var
  names match the example env file; ports match the compose or container files.

## FRONTEND_GUIDELINES.md

- Shape: tokens with values and the file that defines them; typography; spacing; breakpoints
  with what changes at each; component patterns with their classes or tokens; motion;
  accessibility.
- Change set: a token value; a breakpoint; a new reusable pattern; a keyframe.
- Full audit: every token value in the doc matches the token file; breakpoints match; every
  pattern's named classes or tokens exist. A pattern the code no longer uses is a question.

## FRONTEND_STRUCTURE.md

- Shape: the directory tree with one line per directory; one section per feature area with
  its file inventory and behavioral notes; layout and shared sections; key patterns with the
  file that exemplifies each.
- Change set: files and directories added, removed, or moved under mapped paths; a feature
  whose ownership changed.
- Full audit: the tree matches the directory listing; every inventoried file exists; every
  feature directory has a section; every exemplar file named under key patterns exists.

## BACKEND_STRUCTURE.md

- Shape: one table definition per entity; one endpoint table per resource; the directory tree
  with purposes; validation patterns; error handling; storage and background-job sections.
- Change set: per the classification table: endpoints, tables and columns, validation, code
  organization, storage keys, job schedules.
- Full audit: every table in the models or migrations has a definition and every definition
  has a table; every registered route has a row and every row has a route; the tree matches
  the directories; every enum's values match the code.

## IMPLEMENTATION_PLAN.md

- Shape: `## Phase N: <title>`, a `**Goal:**` line, a `**Status:**` line drawn from
  `not-started | in-progress | shipped <date> | deferred | subsumed`, a `**Plan:**` line with
  the repo-relative plan path, scope bullets. An epic phase adds an `epic:` link, a
  `status: <shipped>/<total> milestones shipped` line, and the milestone table
  `| # | Milestone | Size | Status | Branch | Plan | Shipped |`.
- Change set: the phase this plan belongs to. Status is `in-progress` while the summary has
  open boxes or the registry says `implementing` or `ready-for-review`; `shipped <date>` when
  the registry says `shipped`, with the pull request URL appended to the Plan line. For an
  epic child, update its milestone row from `epic-get`: Status from the derived status, Branch,
  Plan link, and Shipped as the date plus the pull request; then refresh the `status:` count.
  Never write step-level detail into this doc; a phase is feature-sized.
- Full audit: every phase's status agrees with `"$BIN/workflow-state" --history` and
  `--epics`; every plan link resolves to a file; no phase carries step-level detail (a
  question, since removing text is a removal).

## LESSONS.md

- Shape: canonical rules by topic; a Corrections Log table; a Bug Log table; `## Decisions`
  with dated entries linking their plans; patterns that work and do not.
- Change set: rows only from the caller's `--correction`, `--bug`, and `--decision`
  arguments. Nothing else.
- Full audit: cross-references resolve; a lesson duplicated across sections is a question;
  narrative is never edited.

## TODOS.md

- Shape: the format in the file's own header (What, Why, Context, Effort, Priority P0 to P4,
  Depends on; a Completed section at the end).
- Change set: nothing. The review skills write entries; `/ship` moves completed ones.
- Full audit: an item whose Context names files that no longer exist is reported as
  informational; the doc is not edited.

## development-commands.md

- Shape: the command policy sentence and its exceptions; full stack start, rebuild, stop with
  services and ports; required env vars by name with how to generate each; per-layer install,
  dev, build, lint, type check, test, single test; database commands; CI parity.
- Change set: a service, port, command, or env var; a test command; a CI job's command.
- Full audit: every service in the compose or container files has a line; every CI job's
  command appears under CI parity; env var names match the example env file; every command
  is copy-pasteable for the documented command policy.

## REVIEW_CHECKLIST.md

- Shape: one heading per technology, each with checks a reviewer can answer yes or no.
- Change set: a technology added to the manifests with no heading here is a question
  (drafting checks is narrative); a technology removed from the manifests makes its heading a
  removal, also a question.
- Full audit: every technology in `TECH_STACK.md` has a heading and every heading has a
  technology.

## AGENTS.md

Per SKILL.md step 5: commands, structure, dependencies, env vars, build and test procedures.
It links; it does not duplicate. Its doc table must list every doc in the ownership table
that exists.
