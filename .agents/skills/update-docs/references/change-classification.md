# Change classification

Loaded by update-docs step 2. Turns a diff into the facts the docs must state. The cues are
stack-neutral; the doc map in `config.json` says which files carry each kind of fact, and the
section names below are the blueprint defaults the map may have refined. When a cue is
ambiguous, read the whole file rather than the hunk.

| Category | Owner (doc, section) | Cues in the diff | Fact to extract, with file:line |
|---|---|---|---|
| Endpoint | `BACKEND_STRUCTURE.md`, API Endpoints | A file the map assigns to API Endpoints; a route registration, decorator, or router entry added, removed, or changed; a handler's parameters, auth dependency, or response type changed | Method, path, purpose, request shape, response shape, auth requirement, error codes |
| Table or column | `BACKEND_STRUCTURE.md`, Database Schema | Model files, migration files; a table or class definition, a column, index, foreign key, enum value, default, or nullability change | Table, column, type, nullability, default, index, foreign key and its delete behavior |
| Validation schema | `BACKEND_STRUCTURE.md`, Data Validation | Schema or serializer files; a field added or a constraint changed | Field and rule |
| Service, job, storage, auth | `BACKEND_STRUCTURE.md`, Code Organization | A new module under services, jobs, storage, or auth; a schedule; an idempotency key; a storage key format; a transaction boundary | Module purpose; schedule; idempotency or transaction rule; storage key layout |
| Page or route | `APP_FLOW.md`, Screen Inventory | The router file or pages directory; a route path added, removed, or renamed; a guard or redirect; user-facing error copy | Route, page name, purpose, auth requirement; the flow's steps; error copy verbatim |
| Component, hook, shared lib | `FRONTEND_STRUCTURE.md`, Directory Overview | Files under components, features, hooks, or lib; a new directory | File and purpose; the feature that owns it; whether it is shared |
| Token or pattern | `FRONTEND_GUIDELINES.md`, Color Palette and its sibling sections | The token file, global stylesheet, or theme config; a color, spacing step, breakpoint, font, or keyframe | Token name and value; the pattern and where it is used |
| Dependency | `TECH_STACK.md`, Dependencies | A manifest line added, removed, or version-changed | Package, exact version (from the lockfile when present), group: core, UI, data, utilities, dev, testing |
| Env var | `development-commands.md`, Full Stack; `TECH_STACK.md`, Infrastructure | The example env file, container files, a settings module reading the environment | Name, purpose, required or optional, how to generate it; never a value |
| Command or service | `development-commands.md`, Full Stack | Compose or container files, task-runner files, CI workflow; a service, port, or command | The exact copy-pasteable command; service name and port |
| CI job | `TECH_STACK.md`, CI/CD Pipeline | Workflow files under the git host's directory | Job name, what it runs, when it runs |
| Phase or milestone status | `IMPLEMENTATION_PLAN.md`, the phase entry | Not in the diff. From `$SUMMARY_FILE` boxes, `workflow-state --history`, and `epic-get` | Status, branch, plan link, pull request, date |
| Deferred work | `TODOS.md` | Not in the diff. From the summary's deviations and the reviews' TODO capture | Title only; the review skills and `/ship` write and move the entries |

Rules:

- A rename is a removal plus an addition. The doc loses the old name; a stale name is drift.
- A deleted file is a fact: the things it defined are gone from the docs too.
- Test-only and lockfile-only changes are exempt by the map and yield no fact, except that a
  lockfile confirms the version a manifest change introduced.
- A changed path that is `unmapped` goes to step 6 before it is classified.
- Every fact carries the file and line that proves it. A fact you cannot point at is a guess.
- When two categories claim one hunk (a migration that also seeds a setting, a route that also
  adds an env var), extract both facts; each has its own owner.
