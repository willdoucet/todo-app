# Backend Structure

<!-- guidance: This doc owns the schema, endpoints, code organization, validation rules, error
handling, and storage. Business rules are stated once in PRD.md and enforced here; link back.
Framework: {{BACKEND_FRAMEWORK}}; ORM: {{ORM}}; migrations: {{MIGRATION_TOOL}}; database: {{DB}}. -->

## Table of Contents

1. [Data Model](#1-data-model)
2. [API Endpoints](#2-api-endpoints)
3. [Code Organization](#3-code-organization)
4. [Data Validation](#4-data-validation)
5. [Error Handling](#5-error-handling)
6. [Storage & Assets](#6-storage--assets)

---

## 1. Data Model

### Entity Overview

<!-- guidance: one row per table. Key Fields names the columns a reader needs to understand the
entity, including FKs with their delete behavior. -->

| Entity | Purpose | Key Fields |
|---|---|---|
| | | |

### Entity Relationship Diagram

<!-- guidance: text boxes with columns and relationship lines; mark cardinality and delete
behavior (CASCADE / SET NULL / RESTRICT) on each edge. -->

```
```

### Table Definitions

<!-- guidance: one `#### <table_name>` per table: columns with type, constraints (PK, FK with
delete behavior, UNIQUE, NOT NULL, DEFAULT, INDEX, CHECK), description; then relationships and
the business rules the table enforces. Timestamps are timezone-aware. -->

#### <table_name>

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTO | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NULLABLE | |

**Relationships:**

**Business rules:**
-

**Indexes:**
-

### Enums

<!-- guidance: enum name, values, and whether it is enforced by a DB CHECK, a native enum type,
or application code only. Must match PRD.md → Data Model → Enums. -->

| Enum | Values | Enforced by |
|---|---|---|
| | | |

---

## 2. API Endpoints

### Base URL

```
Development: http://localhost:{{APP_PORT}}
```

Every endpoint below is prefixed by the base URL. Auth requirement per resource is stated once
in the Auth section; resources not listed there are public.

<!-- guidance: one `### <Resource>` per resource in schema order. Every row states request body,
response, and error codes; "Purpose" is one clause. -->

### <Resource>

| Method | Endpoint | Purpose | Request | Response | Errors |
|---|---|---|---|---|---|
| GET | `/<resource>` | List | query: | `[<Read>]` | 401 |
| GET | `/<resource>/{id}` | Get one | — | `<Read>` | 401, 404 |
| POST | `/<resource>` | Create | `<Create>` | `<Read>` 201 | 401, 409, 422 |
| PATCH | `/<resource>/{id}` | Update | `<Update>` | `<Read>` | 400, 401, 404, 409, 422 |
| DELETE | `/<resource>/{id}` | Delete | — | 204 | 400, 401, 404 |

**Notes:**
-

### Auth

<!-- conditional: keep when {{AUTH_MODEL}} is anything other than "none". Remove and add one line
"No authentication; single-user per instance." otherwise. -->

**Model:** {{AUTH_MODEL}}

| Method | Endpoint | Purpose | Request | Response | Errors |
|---|---|---|---|---|---|
| POST | `/auth/login` | | | | 401, 422 |
| POST | `/auth/logout` | | | 204 | 401 |
| GET | `/auth/status` | Public; drives the sign-in vs. set-up screen | — | | — |

**Contract notes:**
- All credential failures return one status with a byte-identical body; only body-shape errors return 422.
- Every auth request emits exactly one structured log line (event, outcome, reason, request id, latency); never the credential.
- Tokens: <!-- guidance: what is a JWT and what is opaque, lifetimes, where each is stored (cookie attributes, memory only on the client). -->

#### Enforcement pattern

Auth is enforced in one place so that "is this route gated?" has one answer.

<!-- guidance: describe the mechanism for the framework: a wrapping router with the auth
dependency, a middleware with an allowlist, a decorator applied by a base class. State the rule
for new routes (added on the protected router = gated automatically; added on the app = public)
and how to enumerate the public surface (one grep). Interactive API docs endpoints bypass
router-level dependencies; disable or gate them explicitly. -->

Two tests pin the gate from both ends:
- **Structural:** walks the route table and asserts every non-allowlisted route carries the auth dependency.
- **Behavioral:** hits real endpoints and asserts 401 without a token and with a malformed one; asserts the public surface stays 200.

#### Auth subsystem layout

```
{{BACKEND_DIR}}/app/auth/
├── __init__.py       # exports router + the auth dependency (the only public surface)
├── config.py         # settings loaded fail-closed in production
├── models.py         # user + session/token tables
├── schemas.py        # request/response models
├── service.py        # business logic
├── dependencies.py   # the auth dependency
├── routes.py         # /auth/* endpoints
└── errors.py         # single source for identical failure responses
```

---

## 3. Code Organization

### Directory Structure

```
{{BACKEND_DIR}}/
├── app/
│   ├── main.py            # app factory, router registration, lifespan
│   ├── database.py        # engine + session dependency
│   ├── models.py          # ORM models (or models/ package)
│   ├── schemas.py         # request/response schemas (or schemas/ package)
│   ├── crud_<entity>.py   # persistence per entity
│   ├── routes/            # one module per resource
│   ├── services/          # multi-entity business logic
│   └── auth/              # see section 2
├── <migrations dir>/      # {{MIGRATION_TOOL}}
└── tests/
    ├── unit/
    └── integration/
```

### Persistence Pattern

<!-- guidance: the canonical query builder every read goes through (filters soft-deletes,
eager-loads what the response needs), and the CRUD function signatures. Show one real example
once the first entity exists. -->

```
```

### Route Pattern

<!-- guidance: router declaration with prefix and tags, dependency injection for the session,
response models, and how IntegrityError becomes 409. -->

```
```

### Background Job Pattern

<!-- conditional: keep when the stack has a job runner. State: how tasks get a DB session (fresh
event loop per task if async; dispose the engine before the loop closes), that task arguments
are ids not objects, idempotency, retry policy, and where the schedule is declared. -->

```
```

---

## 4. Data Validation

### Schema Pattern

<!-- guidance: Base (shared fields, from_attributes), Create (adds required nested detail),
Update (all optional; immutable discriminators absent), Read (adds id, timestamps, nested
detail). Cross-field rules live in a model validator AND a DB CHECK. -->

```
```

### Validation Rules

<!-- guidance: one row per rule; must match PRD.md → Data Constraints and APP_FLOW.md → Form
Validation. Note where each is enforced (schema, DB, both). -->

| Entity | Field | Validation | Enforced by |
|---|---|---|---|
| | | | |

---

## 5. Error Handling

### HTTP Status Codes

| Code | Usage |
|---|---|
| 200 | Successful GET, PATCH |
| 201 | Successful POST (create) |
| 204 | Successful DELETE |
| 400 | Business-rule rejection |
| 401 | Missing or invalid credentials |
| 404 | Resource not found |
| 409 | Conflict (unique constraint) |
| 422 | Request body failed schema validation |
| 500 | Unhandled server error |

### Error Response Format

```json
{ "detail": "<message>" }
```

Validation errors (422) return `detail` as an array of `{loc, msg, type}` objects; clients must
normalize before displaying.

### Custom Exceptions

<!-- guidance: any exception class that maps to a status, and the one place identical-body
failures are produced. -->

```
```

---

## 6. Storage & Assets

<!-- conditional: keep when the app stores files. Remove and write one line "No file storage in
v1." otherwise. -->

### Backend

<!-- guidance: the storage abstraction (protocol with put/get/delete), the backends it selects by
env, and the default. -->

### Object Keys

<!-- guidance: key shape (`<subdir>/<uuid>.<ext>`), the allowed subdirectories, and which are
managed (tracked in a manifest table) vs. bundled/unmanaged. -->

### Upload Flow

<!-- guidance: validation (magic bytes, allowed types, size caps per kind) → store → manifest
row, with the compensating delete on DB failure. -->

### Lifecycle

<!-- guidance: how an upload becomes referenced (adopt on entity write, in transaction), how it
is released (delete object + row, post-commit; keep the row if the delete fails so a sweep can
retry), and the abandoned-upload sweep schedule. -->

### Read Path

<!-- guidance: public static mount vs. authenticated proxy; which one v1 uses and why. -->

### Environment Variables

Names and generation live in [development-commands.md](./development-commands.md#full-stack).
