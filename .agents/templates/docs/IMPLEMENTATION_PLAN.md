# Implementation Plan

<!-- guidance: This is the roadmap: feature-sized phases in intended order, each with a status
line and a plan link. PHASES ONLY, NEVER STEPS. Step detail lives in the plan file /office-hours
creates. /ship updates the status line and the milestone rows; /update-docs adds phases that
were discovered. Every v1 feature in PRD.md is a phase here with the same name. -->

## Table of Contents

1. [Current State](#1-current-state)
2. [Phases](#phase-1-project-skeleton)
3. [Deferred](#deferred)
4. [Out of Scope](#out-of-scope)
5. [Prioritization](#prioritization)
6. [Testing Strategy](#testing-strategy)

---

## 1. Current State

### Completed Features

<!-- guidance: new mode: one line, "Nothing built; Phase 1 creates the skeleton." adopt mode:
one row per shipped feature with the layers it covers. -->

| Feature | Backend | Frontend | Tests |
|---|---|---|---|
| | | | |

### Known Gaps

<!-- guidance: adopt mode: what exists but is incomplete, with a file path each. -->

1.

---

<!-- guidance: phase entry format. Status values: not-started | in-progress | shipped <date> (#PR)
| deferred | subsumed. Plan is `—` until /office-hours creates the plan file, then a relative
link into .agents/plans/. Branch is the branch the plan runs on. Goal is one paragraph; scope
is three to six bullets, in and out. An epic phase adds an `**Epic:**` link and a milestone
table; milestone status is derived from each child's registry entry. -->

## Phase 1: Project skeleton

**Status:** not-started · **Plan:** — · **Branch:** —

**Goal:** Repository layout per the structure docs, container setup, CI with the doc-guard job,
a hello-world endpoint and page wired end to end, and both test harnesses running one passing
test each. Nothing product-shaped ships in this phase.

- In: directory layout from FRONTEND_STRUCTURE.md and BACKEND_STRUCTURE.md; {{CONTAINER_TOOL}} services from development-commands.md; `{{CI_PROVIDER}}` jobs from TECH_STACK.md → CI/CD Pipeline
- In: `GET /healthz` returning 200 and a root page that renders it
- In: one passing {{TEST_RUNNER_BACKEND}} test and one passing {{TEST_RUNNER_FRONTEND}} test
- Out: any feature from PRD.md; auth; migrations beyond the empty baseline

---

## Phase 2: <Feature name from PRD.md>

**Status:** not-started · **Plan:** — · **Branch:** —

**Goal:**

- In:
- Out:

---

## Phase N: <Epic name>

<!-- conditional: epic phase. Keep this shape only for phases too big for one plan. -->

**Status:** not-started · **Plan:** — · **Branch:** — · **Epic:** <link to .agents/plans/epics/<slug>/...>

**Goal:**

| # | Milestone | Size | Status | Branch | Plan | Shipped |
|---|---|---|---|---|---|---|
| M1 | | quickfix | not-started | | — | |
| M2 | | feature | not-started | | — | |

---

## Deferred

<!-- guidance: items pushed past v1 with the reason and the version they target. Mirror PRD.md →
Non-Goals. -->

-

## Out of Scope

<!-- guidance: things this roadmap will not do at all, with the reason. -->

-

## Prioritization

<!-- guidance: phases grouped by urgency; strike through shipped ones. -->

### Critical for v1 Launch

1. **Phase 1** — Project skeleton

### High Priority (v1 Polish)

-

### Post-v1

-

## Testing Strategy

<!-- guidance: what every phase must prove before /ship: unit and integration suites green,
the phase's acceptance criteria from PRD.md exercised, docs updated. -->

Commands: [development-commands.md → Testing](./development-commands.md#testing).

- Backend: `{{TEST_COMMAND_BACKEND}}`
- Frontend: `{{TEST_COMMAND_FRONTEND}}`
