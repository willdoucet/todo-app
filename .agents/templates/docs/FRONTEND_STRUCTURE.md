# Frontend Structure

<!-- guidance: This doc owns the frontend directory layout, the per-feature file inventory,
behavioral notes, and key patterns. Routes and user flows live in APP_FLOW.md; tokens and
component styling live in FRONTEND_GUIDELINES.md. Do not put file counts in headings; they go
stale on the next commit. Framework: {{FRONTEND_FRAMEWORK}}. -->

## Table of Contents

1. [Directory Overview](#1-directory-overview)
2. [<Feature Area>](#2-feature-area)
3. [Layout](#3-layout)
4. [Shared](#4-shared)
5. [Key Patterns](#5-key-patterns)

---

## 1. Directory Overview

<!-- guidance: the full tree under the frontend source directory with a one-line purpose per
file at the top level and per directory below it. In new mode this is the layout Phase 1
creates. Point each feature directory at its section below. -->

```
{{FRONTEND_DIR}}/src/
├── main.<ext>            # entry point; mounts the router
├── <RootLayout>          # providers + outlet
├── {{TOKEN_SOURCE_PATH}} # tokens and global styles
│
├── lib/
│   ├── api.<ext>         # single HTTP client; auth headers and 401 handling live here
│   └── router.<ext>      # route table; protected layout
│
├── pages/                # route-level shells, one per route in APP_FLOW.md
├── components/
│   ├── <feature>/        # see section 2
│   ├── layout/           # see section 3
│   └── shared/           # see section 4
├── hooks/                # cross-feature hooks
└── contexts/             # providers
```

Tests: <!-- guidance: co-located, under `tests/`, or both; name the convention. -->

---

## 2. <Feature Area>

**Route:** `<route>` <!-- guidance: as listed in APP_FLOW.md → Screen Inventory. -->

### Files

| File | Purpose |
|---|---|
| | |

### Responsive

<!-- guidance: which breakpoint switches which component (from FRONTEND_GUIDELINES.md) and what
the mobile variant is. One line per switch. -->

-

### Behavioral Notes

<!-- guidance: what is non-obvious: click propagation rules, polling conditions, optimistic
update targets, undo windows, state that persists in localStorage. -->

-

<!-- guidance: repeat this section per feature area, numbered in navigation order. -->

---

## 3. Layout

<!-- guidance: the app shell: root layout, navigation chrome, theme toggle, boot fallbacks. -->

### Files

| File | Purpose |
|---|---|
| | |

---

## 4. Shared

<!-- guidance: cross-cutting UI and providers: toasts, modals, pickers, empty states, media hooks. -->

### Files

| File | Purpose |
|---|---|
| | |

---

## 5. Key Patterns

<!-- guidance: one bullet per pattern with the file that exemplifies it. -->

- **Stack:** {{FRONTEND_FRAMEWORK}}, {{STYLING}}, {{TEST_RUNNER_FRONTEND}} — versions in [TECH_STACK.md](./TECH_STACK.md).
- **Routing:**
- **Root providers:**
- **HTTP / data fetching:** one shared client; the only module that reads the API base URL is
- **Auth state:** <!-- conditional: where the token lives (memory, never browser storage), how components subscribe, single-flight refresh, one-shot redirect. -->
- **State management:**
- **Forms:** <!-- guidance: never nest form elements; inner submit-like actions use a div with click and Enter handlers. -->
- **Error display:** <!-- guidance: API validation detail is normalized before it reaches a toast. -->
- **Responsive patterns:**
- **Testing layout:**
- **Design system:** see [FRONTEND_GUIDELINES.md](./FRONTEND_GUIDELINES.md).
