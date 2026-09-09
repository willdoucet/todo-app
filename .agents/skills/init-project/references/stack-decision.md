# Stack decision: option archetypes per layer

Loaded by `init-project` step N2. Each layer lists the archetypes to present, the axes that
decide between them, and what each teaches. Concrete products and versions are **never taken
from this file or from memory**: for every layer, web search for the current leading candidate
in each archetype and its latest stable version, and quote the search date. Present the layer
as one question in the shared format: two or three options with pros, cons, fit for this
project, `Completeness: X/10`, `Teaches:` when learning goals exist, then `RECOMMENDATION`.

Fit is judged against the interview: persona count, scale, data sensitivity, budget, solo or
team, learning goals, hosting preference, deployment intent. Say which interview answer drove
the recommendation.

## 1. Backend language and framework

| Archetype | Pros | Cons | Fits when |
|---|---|---|---|
| Batteries-included full-stack framework in a dynamic language (ORM, migrations, auth, jobs, admin by convention) | Most ground covered, largest tutorial base, fastest to v1 | Convention lock-in, heavier runtime, the seams are hidden | Solo builder, CRUD-heavy product, wants to ship |
| Minimal API framework plus explicit libraries for ORM, migrations, jobs | Every seam visible, small surface per library, natural with a separate frontend | More decisions, more glue, you own the integration gotchas | API-first product, learner who wants to see how layers meet |
| Statically typed compiled language with standard-library HTTP and a thin router | Performance, single-binary deploys, compile-time safety | More boilerplate per CRUD resource, fewer batteries for auth and admin | Compute-heavy or latency-sensitive, learner interested in types and concurrency |

Decide by: language fluency, learning goal, CRUD-to-compute ratio, hosting target, async needs.

## 2. ORM, database, and migrations

Three sub-decisions, presented as one question with combined options.

- **Database.** Relational server (transactions, constraints, concurrent writers, needs a
  service) versus embedded file database (zero ops, single writer, ideal for local-first and
  tests) versus document store (flexible shape, weak relational guarantees). Default to a
  relational server for anything with users and money; embedded for single-user or local-only.
- **ORM.** Full ORM with identity map and relationship loading versus query builder versus raw
  driver. Full ORM teaches the most and hides the most; query builder is the middle.
- **Migrations.** The ORM's native tool versus a standalone migration tool versus plain SQL
  files. Whichever is chosen, the doc must state: forward-only or reversible, how the schema
  is versioned, and how CI runs them.

## 3. Background jobs

| Archetype | Pros | Cons | Fits when |
|---|---|---|---|
| None: do it in the request, or a scheduled command | Nothing to operate | Slow requests, no retries | No email, sync, or imports in v1 |
| Database-backed queue in the same database | No new service, transactional enqueue | Polling, lower throughput | Small scale, wants retries without a broker |
| Broker-backed worker (in-memory data store or message queue) | Throughput, schedules, retries, mature tooling | One more service to run and pay for, idempotency is on you | Periodic sync, heavy imports, real scale |
| Hosted queue or function scheduler from the hosting provider | Zero ops | Lock-in, local dev is awkward | Already on that provider |

## 4. Frontend framework and build tool

| Archetype | Pros | Cons | Fits when |
|---|---|---|---|
| Component single-page app with a bundler dev server, served static | Clean split from the API, simplest hosting, huge ecosystem | Client-side routing and data fetching are yours to wire | `web-split`, API-first, static host for the frontend |
| Meta-framework with routing, server rendering, and data loading built in | Fast first paint, conventions for data | Blurs the backend boundary, needs a server runtime for the frontend | SEO matters, wants one framework for both |
| Server-rendered templates with light client interactivity | Least JavaScript, one codebase | Rich interactions get awkward | Backend framework already renders views |

Under `web-split`, the first archetype is the default; say so and explain the trade.

## 5. Styling

Utility-first CSS with a token configuration (fast, consistent, tokens live in one file that
`design_watched_files` can watch) versus plain CSS with custom properties and modules (no build
step, teaches CSS) versus a component library with a theme (fastest to a decent look, hardest
to make distinctive). Whatever is chosen, `FRONTEND_GUIDELINES.md` must hold the tokens with
values and the file that defines them.

## 6. State and data fetching

Server-state cache library plus minimal local state (handles loading, errors, retries,
invalidation; teaches the server-state model) versus a global store (explicit, verbose, good
for complex client state) versus framework-native loaders (only with a meta-framework). Name
the pattern for optimistic updates and error toasts in the decision.

## 7. Testing per layer

Present as one question with a recommended matrix:

- Backend: unit tests plus integration tests against a real database (a container per test
  run or an embedded database), API tests through the framework's test client.
- Frontend: component tests with a DOM emulator and request mocking; the test runner that
  ships with the build tool.
- End to end: a browser automation tool for the flows in `APP_FLOW.md`; visual regression is
  an optional later phase.
- The exact commands go in `development-commands.md`; the categories reviewers check go in
  `REVIEW_CHECKLIST.md`.

Boil the lake: recommend the full matrix. Tests are the cheapest lake there is.

## 8. Containerization and command policy

Multi-service compose file for dev with a multi-target image (dev and prod from one file,
parity with production, containers-only command policy is possible) versus host development
with only the database in a container (faster loops, drift risk) versus no containers. The
command policy is a separate one-line decision recorded in `development-commands.md` and
`AGENTS.md`; the framework helpers in `.agents/bin` are always host-side regardless.

## 9. CI

Hosted CI on the git host: lint, type check, backend tests, frontend tests, build, and the
`doc-guard --range` job. Ask only whether CI runs on every push or on pull requests only, and
whether the base branch gets protection (require CI, squash merge). Record in `TECH_STACK.md`
under CI and in `IMPLEMENTATION_PLAN.md` Phase 1.

## 10. Hosting and deploy targets

| Archetype | Pros | Cons | Fits when |
|---|---|---|---|
| Platform-as-a-service for the backend plus a static host or CDN for the frontend | Managed database and secrets, simple scaling, free tiers | Split-origin cookies and CORS must be designed on purpose | Public or private deployment on a budget |
| One virtual machine running the compose file | Cheapest at small scale, one origin, full control | You are the ops team; backups and TLS are yours | Comfortable with servers, wants parity |
| Serverless functions and managed database | Scale to zero | Cold starts, long jobs are awkward, lock-in | Spiky traffic, already on that provider |

Include managed database, secrets handling, and the environment variable list in the decision.

## 11. Object storage

None in v1 (no uploads) versus local disk behind the app (simple, does not survive a redeploy
on most platforms) versus an S3-compatible bucket behind a storage abstraction (private reads
through the app, keyed objects, the atomic write-then-record pattern). If uploads are in v1,
recommend the abstraction with a local-disk implementation for dev.

## 12. Auth approach

| Archetype | Pros | Cons | Fits when |
|---|---|---|---|
| None, or an edge access gate in front of everything | Nothing to build | Not per-user; no audit | Single user, private deployment |
| First-party email and password: hashed passwords, short-lived access token, rotating refresh token in an HttpOnly cookie | Full control, teaches the most, no vendor | Security is on you: hashing, rotation, revocation, rate limits | Household or small group, learner wants to understand auth |
| Hosted identity provider | Fastest, MFA and social login for free | Vendor dependency, cost at scale, less learning | Public sign-up, wants MFA now |

Whatever is chosen, `BACKEND_STRUCTURE.md` gets the auth endpoints and token rules, and every
later plan touching it carries the `auth` risk tag.

## Closing the decision

After the last layer, present the whole stack as one table: layer, choice, version, search
date, and the interview answer that drove it. One confirmation question. Record each
learning-driven or non-obvious choice in `LESSONS.md` under Decisions with the reason.
