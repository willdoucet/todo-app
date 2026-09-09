# Application Flow

<!-- guidance: This doc owns every screen, route, navigation path, user flow, and the exact
user-facing error copy. Component file inventories live in FRONTEND_STRUCTURE.md; design tokens
live in FRONTEND_GUIDELINES.md. Every route here maps to a file there. -->

## Table of Contents

1. [Screen Inventory](#1-screen-inventory)
2. [Navigation Structure](#2-navigation-structure)
3. [User Flows](#3-user-flows)
4. [Authentication Flow](#4-authentication-flow)
5. [Error Handling](#5-error-handling)
6. [Decision Points Summary](#6-decision-points-summary)

---

## 1. Screen Inventory

### Routes & Pages

<!-- guidance: one row per route, including nested and placeholder routes. "Auth required" is
yes / no / public-when-unauthenticated. The Page Component column names the file in
FRONTEND_STRUCTURE.md. -->

| Route | Page Component | Purpose | Auth required |
|---|---|---|---|
| `/` | | | |

### Page Hierarchy

<!-- guidance: a tree from the root layout down: persistent chrome (sidebar, header, providers),
then the routed content. Mark protected layouts. -->

```
App (root layout)
├── <persistent navigation>
└── <main content area>
    └── [current page]
```

---

## 2. Navigation Structure

### Global Navigation

**Location:** <!-- guidance: sidebar / top bar / bottom tabs, and what it becomes at each breakpoint from FRONTEND_GUIDELINES.md. -->

**Elements:**
1. **<Label>** — <icon> → `<route>`

**Behavior:**
- Active route indication:
- Collapsed / mobile behavior:

<!-- conditional: add a `### <Area> Sub-Navigation` section for any feature with its own tabs or
side panel: location, elements with routes, default entry. -->

---

## 3. User Flows

<!-- guidance: one `### 3.N <Feature> Flow` per feature in PRD.md, with one `####` block per
action (create, complete, edit, delete, filter). Every block uses the fields below. Write the
exact copy the user sees on error. When desktop and mobile differ, list both step sequences;
otherwise write "Same as desktop." -->

### 3.1 <Feature> Flow

#### <Action>

**Trigger:** <!-- guidance: the control the user activates and where it is. -->

**Steps (Desktop):**
1.

**Steps (Mobile):**
1.

**On Success:**
-

**On Error:**
- <!-- guidance: what the UI shows, the exact copy, and what input is preserved for retry. -->

**Decision Point:** <!-- guidance: the branch condition, if any, and both outcomes; also add it to section 6. -->

---

## 4. Authentication Flow

<!-- conditional: keep when the app has sign-in. Remove entirely (leave one line: "No
authentication; the app is single-user per instance.") when it does not. -->

**Auth model:** {{AUTH_MODEL}}

#### First Run / Account Creation

**Trigger:**
**Steps:**
1.
**On Success:**
**On Error:**

#### Sign In

**Trigger:**
**Steps:**
1.
**On Success:** <!-- guidance: where the user lands, how `return_to` is honored and validated. -->
**On Error:** <!-- guidance: one generic message for every credential failure; never say which part was wrong. -->

#### Session Expiry / Silent Refresh

<!-- guidance: what happens on a 401 mid-session: refresh once, then redirect once. -->

#### Sign Out

**Trigger:**
**On Success:**

---

## 5. Error Handling

### API Error States

<!-- guidance: one row per class of failure the UI distinguishes; copy is what the user reads. -->

| Error Type | User Message | Recovery Action |
|---|---|---|
| Network error | | Retry button |
| 400 Bad Request | | Highlight fields |
| 401 Unauthorized | | Redirect to sign-in |
| 404 Not Found | | Refresh list |
| 409 Conflict | | |
| 422 Validation | | |
| 500 Server Error | | Retry button |

### Form Validation

<!-- guidance: one row per validated field; the rule must match BACKEND_STRUCTURE.md → Data
Validation and the message must match what the API returns or what the client shows first. -->

| Field | Validation | Error Message |
|---|---|---|
| | | |

### Optimistic Updates

**Pattern:**
1. Update the UI immediately
2. Send the request
3. On success, keep the UI state
4. On error, revert and show the error toast

**Applied to:**
-

---

## 6. Decision Points Summary

<!-- guidance: every branch named in a flow above, collected once. -->

| Scenario | Decision | Outcome A | Outcome B |
|---|---|---|---|
| | | | |
