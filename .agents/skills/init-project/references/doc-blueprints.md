# Doc blueprints

Loaded by `init-project` steps N4 and A4. The templates at `.agents/templates/docs/` carry the
headings and placeholders; this file says what each doc must contain to count as a
**blueprint** rather than a stub, and the rules that keep the set consistent. Ownership per
doc is in `_shared/docs-contract.md`; do not restate it here.

## The quality bar

A blueprint is something Phase 1 can be built from without asking a question. Test each doc
against this: could a fresh session, given only this doc set, create the file, table, route,
or component it describes exactly as intended? If the answer needs the interview transcript,
the doc is missing something.

- Facts live in one doc and are linked from the others. Never paste a schema into the PRD or a
  version list into `development-commands.md`.
- Every table has real column names, types, nullability, and relationships. Every endpoint has
  a method, path, request shape, response shape, and error cases. Every page has a route.
  Every token has a value.
- Status is explicit. New mode: everything is `not-started` or `planned`; say so once at the
  top of the doc rather than on every line. Adopt mode: state what exists with a file path.
- Placeholders that have nothing to say get one line explaining why, not deletion. The
  headings are what the doc map and `/update-docs` look up.

## PRD.md

- Executive summary: the one-sentence description, the core value proposition, project status.
- Problem statement: the pain, what people do today instead, the solution, the "aha" moment.
- Target users: one section per persona with role, situation, goals, frustrations, and the
  moment they open the app. Household or group composition when relevant.
- Success criteria: one primary metric, a few secondary, and qualitative signs of success.
- Feature specifications: a priority ranking table, then one section per feature with a
  description, user stories, acceptance criteria that a review can check, and status. Every
  v1 feature here is a phase in `IMPLEMENTATION_PLAN.md`, same name.
- Non-goals and out of scope: what v1 will not do, and what the product is not.
- Technical requirements: architecture in three sentences with a link to `TECH_STACK.md`;
  performance, security, and deployment requirements as bullets.
- Data model: a link to the schema in `BACKEND_STRUCTURE.md` plus a one-paragraph entity
  overview. No column lists here.
- Key user flows: short narratives, linked to the detailed flows in `APP_FLOW.md`.
- Edge cases and business rules: the rules code must enforce, grouped by entity.
- Future roadmap: versions after v1 with their themes.
- Appendix: an endpoint index linking to `BACKEND_STRUCTURE.md`, not duplicating it.

## APP_FLOW.md

- Screen inventory: a table of route, page name, purpose, and auth requirement; a page
  hierarchy tree.
- Navigation structure: the global navigation and any sub-navigation, with what appears where
  at each breakpoint.
- User flows: one per feature. Trigger, numbered steps, decision points, what happens on
  success, what happens on error including the exact copy shown. Include first run and sign-in
  flows when auth exists.
- Error handling: API error states and how the UI shows them, form validation rules and
  messages, optimistic update behavior and rollback.
- Decision points summary: the branching conditions collected in one table.

## TECH_STACK.md

- Frontend dependencies grouped (core, UI, data and state, utilities, dev, testing), each with
  the exact version and the search date in new mode, the lockfile version in adopt mode.
- Backend dependencies grouped the same way (core, database, background jobs, auth,
  integrations, utilities, dev, testing).
- Development tools: package managers, containerization, database tooling, with versions.
- Infrastructure: services with ports, environment variables (name, purpose, required or
  optional, never a value), the CI pipeline job by job, production deployment targets,
  external integrations.
- Version constraints: why these versions, the upgrade policy, which files lock them.
- API contracts: base URL per environment, content types, auth scheme, rate limits.
- Browser support and a file-structure pointer to the structure docs.

## FRONTEND_GUIDELINES.md

- Color palette with hex values and usage, including semantic colors and any per-entity color
  sets. Say which file defines them.
- Typography: font stack, weights, size scale, line heights.
- Spacing scale, gap conventions, border radii.
- Responsive breakpoints with values and what changes at each.
- Component patterns: cards, buttons, inputs, badges, navigation items, modals, with the
  classes or tokens each uses.
- Dark mode strategy and the color mapping, or one line saying it is out of scope.
- Icons: the library and the usage pattern.
- Motion: keyframes, transitions, the rule for when motion is allowed.
- Accessibility: focus states, contrast targets, touch target sizes.
- File organization and naming conventions for styles.

## FRONTEND_STRUCTURE.md

- Directory overview: the full tree under the frontend source directory with a one-line
  purpose per directory. In new mode this is the layout Phase 1 will create.
- One section per feature area: the files it owns (name and purpose), behavioral notes (what
  is non-obvious), and the components it shares.
- Layout and shared sections: shells, navigation, providers, utilities.
- Key patterns: data fetching, forms, error display, routing, testing conventions, with the
  file that exemplifies each.

## BACKEND_STRUCTURE.md

- Database schema: entity overview, a relationship diagram (text is fine), then one table
  definition per entity with columns, types, nullability, defaults, indexes, foreign keys and
  their delete behavior, and enums.
- API endpoints: base URL, then one table per resource with method, path, purpose, request
  body, response, auth requirement, and error codes.
- Code organization: the backend directory tree with purposes; the pattern for a query or
  CRUD module; the pattern for a route module; where jobs, storage, and auth live.
- Data validation: the schema pattern (base, create, update, response) and validation rules.
- Error handling: status codes used, the error response shape, custom exceptions.
- Storage and background jobs sections when the stack has them: object keys, transaction
  boundaries, idempotency rules, schedules.

## IMPLEMENTATION_PLAN.md

Phases only, never steps; a phase is feature-sized and maps to one plan or one epic.

- `## 1. Current State`: new mode says "nothing built; Phase 1 creates the skeleton". Adopt
  mode lists completed features and known gaps with file paths.
- One section per phase in intended order: `## Phase N: <name>`, a `**Goal:**` line, a
  `**Status:** not-started | in-progress | shipped <date> | deferred | subsumed` line, a
  `**Plan:**` line (`—` until office-hours creates one), three to six scope bullets (in and
  out), and for an epic a milestone table (id, name, status, plan link).
- Phase 1 is always "Project skeleton": repo layout per the structure docs, container setup,
  CI with the doc-guard job, a hello-world endpoint and page wired end to end, both test
  harnesses running one passing test each. `Status: not-started`.
- Explicitly deferred: the items pushed past v1 with the reason.
- Testing strategy: what each phase must prove before it ships, with a link to the commands in
  `development-commands.md`.

## LESSONS.md

Keep the template's generic rules (verify before claiming status, explicit paths override
context, merge artifacts instead of replacing, verify behavior not declarations, the secrets
rule, one canonical rule per topic). Add a `## User Preferences` section from the interview
(learning goals, command policy, review appetite) and a `## Decisions` section holding every
stack or scope decision made during init with its reason. The Corrections Log and Bug Log
tables start empty with their headers. In adopt mode, fold in gotchas from any prior rules
file, one canonical rule per topic.

## TODOS.md

The template's format header only (What, Why, Context, Effort, Priority P0 to P4, Depends on;
a Completed section at the end). New mode: no items. Adopt mode: existing TODO files
converted into this format, one question per item whose priority or effort is unclear.

## development-commands.md

- The command policy in one bold sentence at the top, with its exceptions (framework helpers
  under `.agents/bin` are host-side always).
- Full stack: start, rebuild, stop; the services with ports; the required environment
  variables by name with how to generate each (never a value).
- Per layer: install, dev server, build, lint, type check, test (unit, integration, end to end),
  and how to run one test file.
- Database: create, migrate, roll back, seed, reset.
- CI parity: the exact command CI runs for each job.
- Every command is copy-pasteable for the chosen stack. In adopt mode, run each one once and
  note any that fails.

## REVIEW_CHECKLIST.md

Assembled, not written: one snippet per chosen technology from `.agents/templates/checklists/`,
concatenated under a heading per technology, in stack order (backend, database, jobs, frontend,
styling, testing, infrastructure). Each snippet's checks are what `/review-implementation` and
`/final-review` run for that technology. When a snippet is missing, the drafted replacement
follows the same shape: a heading, then checks grouped by category (migration safety, query
efficiency, background-job idempotency, render efficiency, accessibility, security, test
coverage), each check one line a reviewer can answer yes or no.

## AGENTS.md (from `.agents/templates/AGENTS.md`)

Short. The session-start line first, then the overview, the doc table, the command policy with
a link, the routing summary, principles, and guardrails. Everything else is a link into
`$DOCS_DIR`. If it grows past roughly one screen, something belongs in a doc instead.
