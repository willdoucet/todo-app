# Frontend Guidelines

<!-- guidance: This doc owns design tokens, typography, spacing, breakpoints, component patterns,
theming, icons, motion, and accessibility. Every token has a value and one defining file:
`{{TOKEN_SOURCE_PATH}}`. Component file inventories live in FRONTEND_STRUCTURE.md. Styling
system: {{STYLING}}. -->

## Table of Contents

1. [Color Palette](#1-color-palette)
   - [Background Colors](#background-colors)
   - [Primary Accent](#primary-accent)
   - [Active / Selected](#active--selected)
   - [Semantic Colors](#semantic-colors)
   - [Text Colors](#text-colors)
   - [Entity Colors](#entity-colors)
2. [Typography](#2-typography)
3. [Spacing & Layout](#3-spacing--layout)
4. [Responsive Breakpoints](#4-responsive-breakpoints)
5. [Component Patterns](#5-component-patterns)
   - [Cards](#cards)
   - [Buttons](#buttons)
   - [Inputs](#inputs)
   - [Badges](#badges)
   - [Navigation Item](#navigation-item)
   - [Modal / Dialog](#modal--dialog)
   - [Toast](#toast)
   - [Empty State](#empty-state)
6. [Theming](#6-theming)
7. [Icons](#7-icons)
8. [Motion](#8-motion)
9. [Accessibility](#9-accessibility)
10. [File Organization](#10-file-organization)

---

## 1. Color Palette

All color tokens are defined in `{{TOKEN_SOURCE_PATH}}`. That file is the single source; no hex
literal appears in a component. When a token changes, change it there and note it here.

<!-- guidance: one table per group; Token is the name used in class names or CSS variables. -->

### Background Colors

| Token | Hex | Usage |
|---|---|---|
| | | Primary app background |
| | | Secondary background, hover |
| | | Card background |
| | | Card and divider border |

### Primary Accent

| Token | Hex | Usage |
|---|---|---|
| | | Light tint |
| | | Hover background |
| | | Primary buttons, links |
| | | Active state, text |

### Active / Selected

| Token | Hex | Usage |
|---|---|---|
| | | Active navigation item background |

### Semantic Colors

<!-- guidance: success, warning, danger, info; each with tint, border, and solid values. -->

| Token | Hex | Usage |
|---|---|---|
| | | Success background |
| | | Success icon / text |
| | | Warning / overdue |
| | | Danger / destructive |

### Text Colors

| Token | Hex | Usage |
|---|---|---|
| | | Primary text |
| | | Secondary text |
| | | Muted text (never for critical information) |

### Entity Colors

<!-- conditional: keep when entities (users, categories, calendars) get an assigned color from a
palette. List the palette in assignment order and say how assignment happens. -->

| Token | Hex | Assignment |
|---|---|---|
| | | |

---

## 2. Typography

### Font Stack

```css
```

### Font Weights

| Weight | Class / token | Usage |
|---|---|---|
| 400 | | Body |
| 500 | | Labels, navigation |
| 600 | | Headings, emphasis |

### Text Sizes

| Size | Class / token | Usage |
|---|---|---|
| | | Captions, badges |
| | | Body |
| | | Section headings |
| | | Page titles |

### Line Height

-

---

## 3. Spacing & Layout

### Spacing Scale

<!-- guidance: the steps actually used and what each is for (card padding, section gap, page gutter). -->

| Step | Value | Usage |
|---|---|---|
| | | |

### Gap Utilities

-

### Border Radius

| Token | Value | Usage |
|---|---|---|
| | | Buttons, inputs |
| | | Cards |
| | | Pills, avatars |

---

## 4. Responsive Breakpoints

### Standard Breakpoints

| Prefix | Min width | What changes |
|---|---|---|
| (none) | 0 | Mobile-first base |
| `sm` | 640px | |
| `md` | 768px | |
| `lg` | 1024px | |
| `xl` | 1280px | |

### Custom Breakpoints

<!-- conditional: feature-specific breakpoints defined in `{{TOKEN_SOURCE_PATH}}`; say which
component switches at each. Remove when there are none. -->

| Breakpoint | Min width | Usage |
|---|---|---|
| | | |

### Implementation

<!-- guidance: the default pattern (utility prefixes vs. a media-query hook) and when each is used. -->

---

## 5. Component Patterns

<!-- guidance: each pattern shows the canonical class set or token usage and its states. Keep
examples short enough to copy. -->

### Cards

```
```

**Hover state:**
**Selected / completed state:**

### Buttons

**Primary:**
```
```

**Secondary:**
```
```

**Icon button:**
```
```

**Destructive:**
```
```

### Inputs

```
```

**Error state:**

### Badges

```
```

### Navigation Item

**Default:**
**Active:**
**Collapsed (icon only):**

### Modal / Dialog

<!-- guidance: the library or primitive, the overlay treatment, focus trapping, and the transition used. -->

```
```

### Toast

<!-- guidance: position, duration, variants, undo affordance if any. -->

### Empty State

<!-- guidance: icon + one line + one action; never rendered while loading. -->

---

## 6. Theming

<!-- guidance: dark mode strategy (class on root, media query, or none) and the color mapping.
If out of scope, keep the heading and write one line saying so. -->

### Implementation

```
```

### Color Mapping

| Light | Dark |
|---|---|
| | |

### Pattern

Always pair light and dark classes on the same element.

---

## 7. Icons

### Icon Library

| Library | Version | Style |
|---|---|---|
| | | |

### Icon Pattern

```
```

---

## 8. Motion

### Defined Keyframes

<!-- guidance: name, duration, easing, where used. Keyframes are defined in
`{{TOKEN_SOURCE_PATH}}` (or the styles directory) in a way the build will not tree-shake. -->

| Keyframe | Duration | Usage |
|---|---|---|
| | | |

### Transition Utilities

-

### When Motion Is Allowed

- Motion communicates a state change (enter, leave, reorder, success). Decorative motion is not added.
- Mount and unmount animations use the transition primitive the component library provides; CSS `transition` alone does nothing on mount.
- Every animation is verified in the browser (computed `animation-name`), not by the presence of a class.

### Reduced-Motion Policy

All motion respects `prefers-reduced-motion: reduce`: transitions collapse to instant state changes and keyframe animations are disabled. Use the reduced-motion variant or a media query on every animated element.

---

## 9. Accessibility

### Focus States

All interactive elements have a visible focus ring:

```
```

### Color Contrast

- Text meets WCAG AA (4.5:1 body, 3:1 large) against its background.
- Muted text is never used for critical information.

### Interactive Targets

Minimum touch target 44×44px on mobile; icon buttons use padding to reach it.

### Semantics

- Icon-only buttons carry `aria-label`.
- Dialogs trap focus and restore it on close.
- Lists of actions are buttons, not clickable divs.

---

## 10. File Organization

```
{{FRONTEND_DIR}}/src/
├── {{TOKEN_SOURCE_PATH}}   # tokens, keyframes, global styles
├── components/
│   └── shared/             # cross-feature UI
└── ...                     # see FRONTEND_STRUCTURE.md
```

### Naming Conventions

- Components: PascalCase files
- Test files: `<Component>.test.<ext>`
- Contexts / providers: `<Name>Context.<ext>`
- Utility classes: kebab-case, defined in `{{TOKEN_SOURCE_PATH}}`
