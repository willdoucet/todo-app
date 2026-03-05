# Frontend Structure

> Frontend directory layout, component inventory, and key patterns for the React app.

---

## Table of Contents

1. [Directory Overview](#1-directory-overview)
2. [Calendar Dashboard](#2-calendar-dashboard)
3. [Mealboard](#3-mealboard)
4. [Settings](#4-settings)
5. [Responsibilities](#5-responsibilities)
6. [Lists](#6-lists)
7. [Family Members](#7-family-members)
8. [Layout](#8-layout)
9. [Shared](#9-shared)
10. [Key Patterns](#10-key-patterns)

---

## 1. Directory Overview

```
frontend/src/
├── App.jsx               # Root component + React Router routes
├── App.css               # App-level styles
├── main.jsx              # React entry point (renders App)
├── index.css             # Global styles + Tailwind @theme (custom colors, dark mode)
│
├── pages/
│   ├── FamilyMembersPage.jsx
│   ├── ListsPage.jsx
│   ├── MealboardPage.jsx
│   └── ResponsibilitiesPage.jsx
│
├── components/
│   ├── calendar/           # Calendar dashboard (20 files — see Section 2)
│   ├── family-members/     # Family member management (1 file — see Section 7)
│   ├── layout/             # App shell: header, sidebar, nav (4 files — see Section 8)
│   ├── lists/              # Task lists feature (4 files + 2 tests — see Section 6)
│   ├── mealboard/          # Mealboard feature (12 files — see Section 3)
│   ├── responsibilities/   # Responsibilities feature (3 files + 2 tests — see Section 5)
│   ├── settings/           # Settings components (3 files — see Section 4)
│   └── shared/             # Cross-cutting UI components (5 files — see Section 9)
│
├── contexts/
│   └── DarkModeContext.jsx  # Dark mode toggle provider (class on document root)
│
├── hooks/
│   └── usePageTitle.js      # Sets document title
│
└── assets/
    └── react.svg
```

Tests live alongside components (`*.test.jsx`) and in `frontend/tests/` (MSW mocks, setup, integration tests).

---

## 2. Calendar Dashboard

**Route:** `/` (home page)

### Files (20)

| File | Purpose |
|------|---------|
| `CalendarPage.jsx` | Top-level orchestrator — state, handlers, view switching |
| `CalendarHeader.jsx` | Navigation (prev/next/today), view toggle (Month/Week/Day) |
| `FamilyMemberFilter.jsx` | Filter events by family member |
| `MonthView.jsx` | Month grid with day cells, overflow popover |
| `WeekViewDesktop.jsx` | Desktop week view (>=768px) with time grid |
| `WeekViewMobile.jsx` | Mobile week view (<768px) with swipeable days |
| `DayView.jsx` | Single-day view with time grid |
| `TimeGrid.jsx` | Shared time-slot grid for Week/Day views |
| `AllDaySection.jsx` | All-day event row above time grid |
| `CalendarItem.jsx` | Renders a single task or event on the calendar |
| `MonthDayPopover.jsx` | Overflow popover for days with many events (month view) |
| `QuickAddPopover.jsx` | Click-on-empty-slot popover — choose Task or Event |
| `MobileDayList.jsx` | Day event list for mobile week view |
| `EventFormModal.jsx` | Create/edit calendar event modal (includes calendar selector dropdown) |
| `TaskFormModal.jsx` | Create/edit task modal from calendar |
| `calendarUtils.js` | Date math, grid generation, formatting helpers |
| `calendarUtils.test.js` | Tests for utils |
| `useCalendarData.js` | Data fetching hook (events + tasks, auto-polling for pending syncs) |
| `useCalendarData.test.js` | Tests for data hook |
| `useCalendarNavigation.js` | Navigation state (current date, view mode, prev/next/today) |

### Behavioral Notes

- **Click-to-edit:** Clicking any task/event opens its edit modal; task checkbox toggles completion with `stopPropagation`; MonthDayPopover closes before opening edit modal
- **Quick add:** Clicking empty day/slot opens QuickAddPopover (Task or Event choice), then opens the appropriate form modal
- **Views:** Month (desktop default), Week, Day — responsive switch at 768px breakpoint
- **Calendar selector:** EventFormModal has a dropdown of iCloud calendars (fetched from `GET /calendars/`); setting `calendar_id` triggers MANUAL-to-ICLOUD source transitions
- **Sync polling:** `useCalendarData` auto-refetches every 10s when any event has `sync_status === 'PENDING_PUSH'`

---

## 3. Mealboard

**Routes:** `/mealboard/planner`, `/mealboard/recipes`, `/mealboard/shopping`, `/mealboard/finder`

### Files (13)

| File | Location | Purpose |
|------|----------|---------|
| `MealboardPage.jsx` | `pages/` | Main layout with responsive navigation |
| `MealboardNav.jsx` | `components/mealboard/` | Left panel (>=1200px) or dropdown menu (<1200px) |
| `MealPlannerView.jsx` | `components/mealboard/` | Weekly calendar view with meal slots |
| `MealPlannerRightPanel.jsx` | `components/mealboard/` | Recipe suggestions panel (>=1525px sidebar, <1525px modal) |
| `MealDayColumn.jsx` | `components/mealboard/` | Single day column in planner grid |
| `MealCard.jsx` | `components/mealboard/` | Individual meal slot card |
| `AddMealModal.jsx` | `components/mealboard/` | Modal for adding meals to a slot |
| `WeekSelector.jsx` | `components/mealboard/` | Week navigation (prev/next/current) |
| `RecipesView.jsx` | `components/mealboard/` | Recipe catalog with filtering and sorting |
| `RecipeCard.jsx` | `components/mealboard/` | Recipe card in catalog |
| `RecipeFormModal.jsx` | `components/mealboard/` | Create/edit recipe modal |
| `ShoppingListView.jsx` | `components/mealboard/` | Shopping list linked from existing lists |
| `RecipeFinderView.jsx` | `components/mealboard/` | Placeholder for AI-powered recipe discovery |

### Responsive Breakpoints

- **1200px (xl:):** Desktop nav panel vs mobile dropdown menu
- **1525px:** Right panel sidebar vs modal for recipe suggestions

---

## 4. Settings

Components in `src/components/settings/`:

| File | Purpose |
|------|---------|
| `ICloudSettings.jsx` | iCloud calendar integration management (connect/disconnect, calendar selection) |
| `TimezoneSettings.jsx` | App-wide timezone configuration (IANA timezone picker) |
| `CalendarSelector.jsx` | Calendar checkbox list for selecting which iCloud calendars to sync |

---

## 5. Responsibilities

**Route:** `/responsibilities`

### Files (3 + 2 tests)

| File | Purpose |
|------|---------|
| `ResponsibilityCard.jsx` | Responsibility display card with swipe-to-complete |
| `ResponsibilityForm.jsx` | Responsibility create/edit form (categories, frequency, icon) |
| `ScheduleView.jsx` | Daily responsibility schedule grouped by category and family member |
| `ResponsibilityCard.test.jsx` | Tests for ResponsibilityCard |
| `ResponsibilityForm.test.jsx` | Tests for ResponsibilityForm |

### Behavioral Notes

- **Daily vs Edit tabs:** ResponsibilitiesPage toggles between ScheduleView (daily tracker) and edit list
- **Category filter:** ScheduleView has filter pills (Morning/Afternoon/Evening/Chore)
- **Mobile:** Tab bar for family member selection; Desktop: side-by-side member cards

---

## 6. Lists

**Route:** `/lists`

### Files (4 + 2 tests)

| File | Purpose |
|------|---------|
| `ListPanel.jsx` | Task list sidebar (desktop aside, mobile slide-in drawer) |
| `TaskItem.jsx` | Single task row with checkbox, swipe-to-delete |
| `TaskListView.jsx` | Task list rendering with empty state |
| `TodoForm.jsx` | Task create/edit form (also used by calendar's TaskFormModal) |
| `TaskItem.test.jsx` | Tests for TaskItem |
| `TodoForm.test.jsx` | Tests for TodoForm |

---

## 7. Family Members

**Route:** `/settings` (rendered inside FamilyMembersPage)

### Files (1)

| File | Purpose |
|------|---------|
| `FamilyMemberManager.jsx` | Family member CRUD UI with photo upload |

---

## 8. Layout

App shell components used by all pages.

### Files (4)

| File | Purpose |
|------|---------|
| `Header.jsx` | App header with dark mode toggle |
| `Sidebar.jsx` | App sidebar navigation (bottom bar on mobile, left rail on desktop) |
| `DarkModeToggle.jsx` | Dark/light mode switch (used by Header and Sidebar) |
| `AddButton.jsx` | Floating action button for creating new items |

---

## 9. Shared

Cross-cutting UI components used across multiple features.

### Files (5)

| File | Purpose |
|------|---------|
| `ConfirmDialog.jsx` | Reusable confirmation modal (used by responsibilities, lists, mealboard) |
| `EmptyState.jsx` | Empty state placeholder variants (tasks, responsibilities, daily view) |
| `SwipeableItem.jsx` | Swipe-to-reveal actions wrapper (used by TaskItem, ResponsibilityCard) |
| `PhotoUpload.jsx` | Image upload with preview (used by ResponsibilityForm, FamilyMemberManager) |
| `Tooltip.jsx` | Tooltip and TruncatedText components (used by ListPanel) |

---

## 10. Key Patterns

- **HTTP client:** Axios for all API calls (configured with `VITE_API_BASE_URL`)
- **Server state:** TanStack Query installed but not fully integrated; most components use direct Axios calls with `useEffect`/`useState`
- **Routing:** React Router v7 with route-level components in `src/pages/`; calendar is the home route (`/`)
- **State management:** Local state (`useState`) + context (`DarkModeContext`); no global store
- **Callback threading:** CalendarPage defines handlers, passes to views, views pass to leaf components. Uses `stopPropagation` for nested click targets (e.g., checkbox vs row click)
- **Headless UI:** `@headlessui/react` for modals and popovers (render props for programmatic close)
- **Design system:** See [FRONTEND_GUIDELINES.md](./FRONTEND_GUIDELINES.md) for colors, spacing, dark mode, and component patterns
