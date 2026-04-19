# Frontend Guidelines

> Complete design system documentation for consistent UI development.

---

## Table of Contents

1. [Color Palette](#1-color-palette)
2. [Typography](#2-typography)
3. [Spacing & Layout](#3-spacing--layout)
4. [Responsive Breakpoints](#4-responsive-breakpoints)
5. [Component Patterns](#5-component-patterns)
6. [Dark Mode](#6-dark-mode)
7. [Icons](#7-icons)
8. [Animations](#8-animations)

---

## 1. Color Palette

All colors are defined in `frontend/src/index.css` using Tailwind v4's `@theme` directive.

### Background Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `warm-cream` | #FAF7F2 | Primary app background |
| `warm-beige` | #F5F0E8 | Secondary background, hover states |
| `warm-sand` | #EBE5DA | Tertiary background, sidebar |
| `card-bg` | #FFFDFB | Card backgrounds |
| `card-border` | #E8E2D9 | Card and divider borders |

### Primary Accent (Terracotta)

| Token | Hex | Usage |
|-------|-----|-------|
| `terracotta-50` | #FEF3F0 | Light background tint |
| `terracotta-100` | #FCE4DE | Subtle emphasis |
| `terracotta-200` | #FAC9BD | Hover backgrounds |
| `terracotta-500` | #D97452 | Primary buttons, links |
| `terracotta-600` | #C4613F | Active states, text |
| `terracotta-700` | #A34E32 | Dark emphasis |

### Active/Selected (Peach)

| Token | Hex | Usage |
|-------|-----|-------|
| `peach-100` | #FFE8DF | Active sidebar item background |
| `peach-200` | #FFD4C4 | Hover on active items |

### Success (Sage Green)

| Token | Hex | Usage |
|-------|-----|-------|
| `sage-50` | #F4F7F4 | Completed item background |
| `sage-100` | #E5EDE6 | Success tint |
| `sage-200` | #C8DBC9 | Success border |
| `sage-500` | #6B9A70 | Success icons, checkmarks |
| `sage-600` | #588D5E | Success text |
| `sage-700` | #4A7A50 | Dark success emphasis |

### Text Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `text-primary` | #3D3833 | Primary text, headings |
| `text-secondary` | #6B645A | Secondary text, labels |
| `text-muted` | #9A9287 | Placeholder, disabled text |

### Category Labels

| Token | Hex | Usage |
|-------|-----|-------|
| `label-green` | #5D8A61 | Category badges |

### Family Member Colors

10-color "Soft Contemporary" palette for family member avatars. Defined in `frontend/src/constants/familyColors.js`.

| Name | Hex |
|------|-----|
| Soft Red | #D4695A |
| Apricot | #D4915A |
| Ochre | #BFA04A |
| Sage | #5E9E6B |
| Teal | #4A9E9E |
| Steel Blue | #5A80B0 |
| Lavender | #8A60B0 |
| Rose | #B06085 |
| Olive | #7A8A55 |
| Mocha | #9A7055 |

Use `<ColorPicker>` from `components/shared/ColorPicker.jsx` for selection UI. Use `getFirstUnusedColor(existingColors)` to auto-pick the next available color.

---

## 2. Typography

### Font Stack

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
  'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
```

### Font Weights

| Weight | Class | Usage |
|--------|-------|-------|
| 400 | `font-normal` | Body text |
| 500 | `font-medium` | Card titles, emphasis |
| 600 | `font-semibold` | Section headings |
| 700 | `font-bold` | Page titles |

### Text Sizes

| Class | Size | Usage |
|-------|------|-------|
| `text-xs` | 0.75rem | Badges, meta info |
| `text-sm` | 0.875rem | Card content, secondary text |
| `text-base` | 1rem | Body text |
| `text-lg` | 1.125rem | Card titles |
| `text-xl` | 1.25rem | Section headings |
| `text-2xl` | 1.5rem | Page titles |

### Line Height

Default: `line-height: 1.5`

Use `leading-tight` for headings in constrained spaces.

---

## 3. Spacing & Layout

### Spacing Scale

Using Tailwind's default spacing scale (1 unit = 0.25rem = 4px):

| Class | Value | Common Usage |
|-------|-------|--------------|
| `p-1` / `m-1` | 4px | Tight button padding |
| `p-2` / `m-2` | 8px | Icon buttons, small gaps |
| `p-3` / `m-3` | 12px | Card padding |
| `p-4` / `m-4` | 16px | Standard padding |
| `p-6` / `m-6` | 24px | Section spacing |
| `p-8` / `m-8` | 32px | Large section gaps |

### Gap Utilities

| Class | Usage |
|-------|-------|
| `gap-1` | Tight inline elements |
| `gap-2` | Icon + text pairs |
| `gap-3` | Form field groups |
| `gap-4` | Card grids |
| `gap-6` | Section separations |

### Border Radius

| Class | Value | Usage |
|-------|-------|-------|
| `rounded` | 0.25rem | Small badges |
| `rounded-lg` | 0.5rem | Buttons, inputs |
| `rounded-xl` | 0.75rem | Cards |
| `rounded-full` | 9999px | Avatars, circular buttons |

---

## 4. Responsive Breakpoints

### Standard Tailwind Breakpoints

| Prefix | Min Width | Usage |
|--------|-----------|-------|
| (none) | 0px | Mobile-first base styles |
| `sm:` | 640px | Show sidebar |
| `md:` | 768px | Two-column layouts, calendar grid |
| `lg:` | 1024px | Three-column layouts |
| `xl:` | 1280px | Full desktop layouts |

### Custom Breakpoints

Defined in `index.css` for specific features:

| Breakpoint | Min Width | Usage |
|------------|-----------|-------|
| Mealboard Nav | 1200px | Show left panel navigation |
| Right Panel | 1525px | Show meal planner right panel |

### Implementation

```css
/* Mealboard calendar - vertical on mobile, 7-column grid on desktop */
.meal-calendar {
  display: flex;
  flex-direction: column;
}

@media (min-width: 768px) {
  .meal-calendar {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
  }
}
```

---

## 5. Component Patterns

### Cards

```jsx
<div className="bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 rounded-xl p-3">
  {/* Card content */}
</div>
```

**Hover state:**
```jsx
className="... hover:shadow-md transition-all"
```

**Completed state:**
```jsx
className={`... ${isCompleted ? 'bg-sage-50 dark:bg-green-900/20 border-sage-200' : ''}`}
```

### Buttons

**Primary button:**
```jsx
<button className="px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 text-white rounded-lg transition-colors">
  Action
</button>
```

**Secondary button:**
```jsx
<button className="px-4 py-2 bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige rounded-lg transition-colors">
  Secondary
</button>
```

**Icon button:**
```jsx
<button className="p-1.5 rounded-full bg-warm-sand dark:bg-gray-700 text-text-muted hover:bg-terracotta-100 hover:text-terracotta-600 transition-colors">
  <svg className="w-4 h-4" ... />
</button>
```

### Inputs

```jsx
<input
  type="text"
  className="w-full px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-card-bg dark:bg-gray-800 text-text-primary dark:text-gray-100 placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-terracotta-500"
  placeholder="Placeholder text..."
/>
```

### Badges

**Category badge:**
```jsx
<span className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
  BREAKFAST
</span>
```

**Meal category colors:**
```javascript
const CATEGORY_COLORS = {
  BREAKFAST: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  LUNCH: 'bg-sage-100 text-sage-700 dark:bg-green-900/30 dark:text-green-400',
  DINNER: 'bg-peach-100 text-terracotta-700 dark:bg-orange-900/30 dark:text-orange-400'
}
```

### Sidebar Navigation Item

```jsx
<Link
  className={`
    flex flex-col items-center justify-center w-14 h-14 rounded-xl
    transition-all duration-200
    ${isActive
      ? 'bg-peach-100 text-terracotta-600 dark:bg-blue-600 dark:text-white shadow-lg'
      : 'text-text-secondary dark:text-gray-400 hover:bg-warm-beige dark:hover:bg-gray-800 hover:text-terracotta-600'
    }
  `}
>
```

### Modal / Dialog

Using Headless UI `Dialog`:

```jsx
<Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-card-bg dark:bg-gray-800 p-6 text-left align-middle shadow-xl transition-all">
  <Dialog.Title className="text-lg font-medium text-text-primary dark:text-gray-100">
    Modal Title
  </Dialog.Title>
  {/* Content */}
</Dialog.Panel>
```

---

## 6. Dark Mode

### Implementation

Dark mode uses class-based toggling via `DarkModeContext`:

```jsx
// Toggle dark class on document root
document.documentElement.classList.toggle('dark')
```

### Color Mapping

| Light Mode | Dark Mode |
|------------|-----------|
| `bg-warm-cream` | `dark:bg-gray-900` |
| `bg-card-bg` | `dark:bg-gray-800` |
| `border-card-border` | `dark:border-gray-700` |
| `text-text-primary` | `dark:text-gray-100` |
| `text-text-secondary` | `dark:text-gray-400` |
| `text-text-muted` | `dark:text-gray-500` |
| `bg-terracotta-500` | `dark:bg-blue-600` |
| `text-terracotta-600` | `dark:text-blue-400` |
| `bg-sage-50` | `dark:bg-green-900/20` |

### Pattern

Always pair light and dark classes:

```jsx
className="bg-card-bg dark:bg-gray-800 text-text-primary dark:text-gray-100"
```

---

## 7. Icons

### Icon Library

Using inline SVGs with Tailwind classes. Standard sizes:

| Class | Usage |
|-------|-------|
| `w-3.5 h-3.5` | Meta info icons (clock, etc.) |
| `w-4 h-4` | Action buttons |
| `w-5 h-5` | Form icons |
| `w-6 h-6` | Navigation icons |

### Icon Pattern

```jsx
<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="..." />
</svg>
```

Icons inherit color from text (`currentColor`), so apply color via parent's `text-*` class.

---

## 8. Animations

### Defined Keyframes

In `index.css`:

```css
@keyframes fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes scale-in {
  from { transform: scale(0); }
  to { transform: scale(1); }
}
```

### Transition Utilities

| Class | Usage |
|-------|-------|
| `transition-all` | General transitions |
| `transition-colors` | Color-only changes |
| `transition-opacity` | Fade effects |
| `duration-150` | Fast interactions |
| `duration-200` | Standard transitions |

### Hover Reveal Pattern

For action buttons that appear on hover:

```css
.meal-card-actions {
  opacity: 0;
  transition: opacity 150ms ease-in-out;
}

.meal-card:hover .meal-card-actions,
.meal-card:focus-within .meal-card-actions {
  opacity: 1;
}
```

---

## 9. Accessibility

### Focus States

All interactive elements should have visible focus:

```jsx
className="... focus:outline-none focus:ring-2 focus:ring-terracotta-500"
```

### Color Contrast

- Text colors meet WCAG AA contrast ratios against their backgrounds
- `text-primary` (#3D3833) on `warm-cream` (#FAF7F2): 7.5:1
- Never use `text-muted` for critical information

### Interactive Targets

Minimum touch target size: 44x44px for mobile. Use `p-2` or larger on icon buttons.

---

## 10. File Organization

```
frontend/src/
├── components/
│   ├── [SharedComponent].jsx    # Reusable across features
│   ├── calendar/                # Calendar dashboard (18 components)
│   │   ├── CalendarPage.jsx     # Orchestrator with modal + edit state
│   │   ├── CalendarItem.jsx     # Row item with click + checkbox toggle
│   │   └── ...
│   └── mealboard/               # Mealboard feature components
│       ├── MealCard.jsx
│       └── ...
├── pages/
│   └── [FeaturePage].jsx        # Route-level components
├── contexts/
│   └── DarkModeContext.jsx      # Global state providers
└── index.css                    # Global styles + Tailwind theme
```

### Naming Conventions

- Components: PascalCase (`MealCard.jsx`)
- Test files: `[Component].test.jsx`
- Contexts: `[Name]Context.jsx`
