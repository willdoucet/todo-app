# Product Requirements Document (PRD)
# {{PROJECT_NAME}}

> {{PROJECT_TAGLINE}}

<!-- guidance: This doc owns WHAT is being built, for whom, scope, acceptance criteria, business
rules, and roadmap versions. Stack facts live in TECH_STACK.md; schema and endpoint facts live in
BACKEND_STRUCTURE.md. Link to them, never paste them here. In new mode say once under Project
Status that everything is planned; in adopt mode mark each feature Built / Rebuilding / Planned /
Not Started. Every v1 feature named here is a phase in IMPLEMENTATION_PLAN.md with the same name. -->

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Target Users](#3-target-users)
4. [Success Criteria](#4-success-criteria)
5. [Feature Specifications](#5-feature-specifications)
6. [Non-Goals & Out of Scope](#6-non-goals--out-of-scope)
7. [Technical Requirements](#7-technical-requirements)
8. [Data Model](#8-data-model)
9. [User Flows](#9-user-flows)
10. [Edge Cases & Business Rules](#10-edge-cases--business-rules)
11. [Future Roadmap](#11-future-roadmap)
- [Appendix A: API Endpoints](#appendix-a-api-endpoints)
- [Appendix B: Glossary](#appendix-b-glossary)
- [Document Version History](#document-version-history)

---

## 1. Executive Summary

<!-- guidance: one paragraph: what the product is, who uses it, and the sentence a user would use
to describe it to a friend. -->

### Core Value Proposition

> <!-- guidance: one quotable sentence. -->
> <!-- example: One place to see everything: what needs to be done, who is doing it, and what is for dinner. -->

### Project Status

- **Current state:** <!-- guidance: new mode: "Nothing built; Phase 1 creates the skeleton." adopt mode: what runs today and where. -->
- **Target state:** <!-- guidance: what v1 looks like when shipped and who can reach it. -->
- **Stack:** {{FRONTEND_FRAMEWORK}} frontend, {{BACKEND_FRAMEWORK}} backend, {{DB}} — versions in [TECH_STACK.md](./TECH_STACK.md)

---

## 2. Problem Statement

### The Pain

<!-- guidance: 3-6 bullets describing what is broken or tedious today, in the user's words, plus
what people do instead (the status quo the product must beat). -->

-

### The Solution

<!-- guidance: numbered list; one line per pain point above, limited to the v1 surface. -->

1.

### The "Aha Moment"

<!-- guidance: the moment a user realises the product is worth keeping. One or two sentences. -->

---

## 3. Target Users

### Primary Persona: <role>

**Demographics:**
**Situation:** <!-- guidance: the moment they open the app. -->
**Goals:**
-
**Frustrations:**
-
**Usage Pattern:**
- Daily:
- Weekly:

<!-- conditional: add one `### Secondary Persona: <role>` block per additional user type with the
same fields; remove the block for single-persona products. -->

### Household / Group Composition

<!-- conditional: keep when the product is used by a group (family, team, class). Say which group
shapes are supported and which are not. Remove for single-user products. -->

---

## 4. Success Criteria

### Primary Metric

**<!-- guidance: one measurable sentence with a time window. -->**

### Secondary Metrics

| Metric | Target | Measurement |
|---|---|---|
| | | |

### Qualitative Success

-

---

## 5. Feature Specifications

### Priority Ranking

<!-- guidance: P0 = v1 cannot ship without it; P1 = v1 target; P2 = post-launch; P3 = someday.
Status is one of Built / Rebuilding / Planned / Not Started. Plan is `—` until /office-hours
creates a plan file, then a relative link to it. /ship keeps the Status and Plan columns current. -->

| Priority | Feature | Status | Plan |
|---|---|---|---|
| P0 | | Not Started | — |

---

### 5.1 <Feature Name>

**Purpose:** <!-- guidance: one sentence. -->

#### Features

<!-- guidance: acceptance criteria must be checkable by a review: a visible result, a persisted
state, a recorded timestamp, an error shown. No "works correctly". -->

| Feature | Description | Acceptance Criteria |
|---|---|---|
| | | |

<!-- guidance: add `#### <Behavior Name>` subsections for non-obvious behaviors (shared ownership
semantics, recurrence logic, what a toggle is for). Each one is a business rule; mirror it in
section 10. -->

#### Data Constraints

<!-- guidance: field: required or optional, length or range, uniqueness, defaults. These must
match BACKEND_STRUCTURE.md → Data Validation exactly. -->

-

<!-- guidance: repeat `### 5.N <Feature Name>` for every feature in the ranking table, in
priority order. Planned features get the same shape with fewer rows, never a paragraph. -->

---

## 6. Non-Goals & Out of Scope

### Explicitly Out of Scope for v1

<!-- guidance: things a reasonable person would expect and will not get in v1, each with a
short reason. Deferred items also appear in IMPLEMENTATION_PLAN.md → Deferred. -->

-

### What This App Is NOT

-

---

## 7. Technical Requirements

### Architecture

<!-- guidance: three sentences or a small box diagram: frontend, backend, database, job runner
if any, and how they talk (REST, cookies, websockets). Deployment topology belongs in
TECH_STACK.md → Production Deployment. -->

```
[ {{FRONTEND_FRAMEWORK}} ] --HTTP--> [ {{BACKEND_FRAMEWORK}} ] --> [ {{DB}} ]
```

### Tech Stack

See [TECH_STACK.md](./TECH_STACK.md). Versions are not listed here.

### Performance Requirements

| Metric | Target |
|---|---|
| Page load | |
| API response (p95) | |
| Database query (average) | |
| Concurrent users | |

### Security Model

**Auth model:** {{AUTH_MODEL}}

<!-- guidance: how identity is established, who can see what, how a session ends, tenancy in one
line (single instance per group, multi-tenant, public). Cross-reference BACKEND_STRUCTURE.md →
API Endpoints → Auth for the enforcement pattern. -->

#### Invariants

<!-- guidance: rules that must never be violated. Each becomes a test or a structural check
somewhere and is referenced from REVIEW_CHECKLIST.md. -->

-

<!-- example: access tokens are never written to browser storage; refresh-token plaintext is never
persisted; every non-public route carries the auth dependency; auth failures return
byte-identical bodies so nothing can be enumerated. -->

### Deployment Requirements

| Requirement | Description |
|---|---|
| Web accessible | |
| Tenancy | |
| CI/CD | |
| Hosting | |
| Database | |
| File storage | |

---

## 8. Data Model

<!-- guidance: entity level only. Column lists live in BACKEND_STRUCTURE.md → Data Model. -->

### Entity Relationship Diagram

<!-- guidance: boxes with entity names and relationship lines (1:many, many:many). No columns. -->

```
```

Full table definitions: [BACKEND_STRUCTURE.md → Data Model](./BACKEND_STRUCTURE.md#1-data-model).

### Enums

<!-- guidance: one block per enum: name and values. Must match the DB CHECK constraints and the
API schema enums in BACKEND_STRUCTURE.md. -->

```
```

---

## 9. User Flows

<!-- guidance: short numbered narratives, one per key journey, `### 9.N <Persona>: <Journey>`.
Step-level detail with desktop/mobile variants and error copy lives in APP_FLOW.md; link there. -->

### 9.1 <Persona>: <Journey>

1.
2.

Detailed steps: [APP_FLOW.md](./APP_FLOW.md).

---

## 10. Edge Cases & Business Rules

<!-- guidance: the rules code must enforce, grouped by entity. Each rule appears once here and is
enforced (and tested) per BACKEND_STRUCTURE.md → Data Validation. -->

### <Entity> Rules

-

### Data Validation

-

---

## 11. Future Roadmap

<!-- guidance: versions after v1 with their themes and the features they carry. Phases in
IMPLEMENTATION_PLAN.md reference these version labels. -->

### v1.0 (<theme>)

-

### v1.1 (<theme>)

-

### Future Considerations

-

---

## Appendix A: API Endpoints

The endpoint index lives in [BACKEND_STRUCTURE.md → API Endpoints](./BACKEND_STRUCTURE.md#2-api-endpoints) and is not duplicated here.

## Appendix B: Glossary

| Term | Definition |
|---|---|
| | |

---

## Document Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 Draft | {{DATE}} | {{AUTHOR}} | Initial PRD |
