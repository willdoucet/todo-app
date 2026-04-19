# Frontend Structure

> Frontend directory layout, component inventory, routes, and key patterns for the React app.

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
├── App.jsx               # Top-level route table
├── App.css               # Legacy app-level stylesheet (present, not currently imported)
├── main.jsx              # React entry point; mounts BrowserRouter + root providers
├── index.css             # Global styles, utilities, and theme tokens
│
├── pages/
│   ├── FamilyMembersPage.jsx   # Settings page shell
│   ├── ListsPage.jsx           # Lists page shell
│   ├── MealboardPage.jsx       # Mealboard shell + nested routes
│   └── ResponsibilitiesPage.jsx # Responsibilities page shell
│
├── components/
│   ├── calendar/           # Calendar dashboard (20 files — see Section 2)
│   ├── family-members/     # Family member management (1 file — see Section 7)
│   ├── layout/             # App shell chrome (4 files — see Section 8)
│   ├── lists/              # Task list UI (11 files — see Section 6)
│   ├── mealboard/          # Mealboard UI + helpers (26 files — see Section 3)
│   ├── responsibilities/   # Responsibilities UI (5 files — see Section 5)
│   ├── settings/           # Settings surfaces (8 files — see Section 4)
│   └── shared/             # Cross-cutting UI + providers (10 files — see Section 9)
│
├── contexts/
│   ├── DarkModeContext.jsx       # Dark mode provider + hook
│   └── DarkModeContext.test.jsx  # Context tests
│
├── hooks/
│   ├── useDebounce.js       # Debounce callback invocation
│   ├── useDelayedFlag.js    # Delay loading indicators to avoid spinner flash
│   ├── useFormShortcut.js   # Cmd/Ctrl+S form submit helper
│   ├── useItems.js          # Unified Item-model CRUD hook for mealboard
│   ├── useMediaQuery.js     # Responsive breakpoint hook
│   └── usePageTitle.js      # Sets document title
│
└── assets/
    └── react.svg
```

Tests are split between co-located files under `frontend/src/` and feature-focused tests in `frontend/tests/components/`.

---

## 2. Calendar Dashboard

**Route:** `/`

`App.jsx` routes the home page directly to `components/calendar/CalendarPage.jsx` rather than a `pages/CalendarPage.jsx` wrapper.

### Files (20)

| File | Purpose |
|------|---------|
| `CalendarPage.jsx` | Top-level orchestrator for calendar state, handlers, and view switching |
| `CalendarHeader.jsx` | Prev/next/today controls plus Month/Week/Day toggle |
| `FamilyMemberFilter.jsx` | Filter events and tasks by family member |
| `MonthView.jsx` | Month grid with overflow handling |
| `WeekViewDesktop.jsx` | Desktop week view with shared time grid |
| `WeekViewMobile.jsx` | Mobile week view with mobile-specific day navigation |
| `DayView.jsx` | Single-day time-grid view |
| `TimeGrid.jsx` | Shared timed-slot renderer for week/day layouts |
| `AllDaySection.jsx` | All-day event row above timed slots |
| `CalendarItem.jsx` | Individual task/event card inside the calendar |
| `MonthDayPopover.jsx` | Overflow popover for crowded month cells |
| `QuickAddPopover.jsx` | Empty-slot quick-add chooser for task vs event |
| `MobileDayList.jsx` | Mobile list rendering for a day’s items |
| `EventFormModal.jsx` | Create/edit event modal with calendar selection |
| `TaskFormModal.jsx` | Create/edit task modal from the calendar |
| `calendarUtils.js` | Date math, formatting, and grid helpers |
| `calendarUtils.test.js` | Utility tests |
| `useCalendarData.js` | Loads events/tasks and polls while sync is pending |
| `useCalendarData.test.js` | Data-hook tests |
| `useCalendarNavigation.js` | Current date, view mode, and prev/next/today logic |

### Behavioral Notes

- Clicking a task or event opens its edit modal; nested controls use `stopPropagation` to avoid accidental row clicks.
- Empty day/slot clicks open `QuickAddPopover`, which then hands off to the relevant modal.
- The view system is Month / Week / Day, with desktop/mobile week layouts split at the `768px` breakpoint.
- Event creation supports selecting synced iCloud calendars.
- `useCalendarData` polls every `10s` while any item has `sync_status === 'PENDING_PUSH'`.

---

## 3. Mealboard

**Routes:** `/mealboard/planner`, `/mealboard/recipes`, `/mealboard/finder`

`/mealboard/shopping` no longer has its own view; direct hits redirect to `/lists`.

### Files (27 total: 1 page shell + 26 mealboard files)

| File | Location | Purpose |
|------|----------|---------|
| `MealboardPage.jsx` | `pages/` | Mealboard shell with nested routes, responsive nav, and the `/mealboard/shopping -> /lists` redirect |
| `MealboardNav.jsx` | `components/mealboard/` | Sidebar nav at desktop widths and dropdown nav on smaller screens |
| `MealPlannerView.jsx` | `components/mealboard/` | Planner orchestrator: week state, slot types, entries, filters, add/edit/delete/undo flows |
| `WeekSelector.jsx` | `components/mealboard/` | Prev/next/today week navigation |
| `FamilyStrip.jsx` | `components/mealboard/` | Family-member filter pill strip |
| `ShoppingCard.jsx` | `components/mealboard/` | Linked shopping-list card with sync status, warnings, and navigation into `/lists` |
| `ShoppingLinkModal.jsx` | `components/mealboard/` | Two-step modal for linking or creating a shopping list |
| `SwimlaneGrid.jsx` | `components/mealboard/` | Desktop planner grid: rows are slot types, columns are week days |
| `MobileDayView.jsx` | `components/mealboard/` | Mobile planner view: one day at a time with swipe/day-pill navigation |
| `MealCard.jsx` | `components/mealboard/` | Individual meal entry card inside planner cells |
| `UndoMealCard.jsx` | `components/mealboard/` | Inline undo card shown while a planner delete is pending |
| `AddMealPopover.jsx` | `components/mealboard/` | Add-meal picker for recipes, food items, or custom meal names |
| `ProgressTracker.jsx` | `components/mealboard/` | Weekly slot-by-slot completion summary |
| `WelcomeCard.jsx` | `components/mealboard/` | Empty-state onboarding card for a blank planner |
| `lane-cell-merge.js` | `components/mealboard/` | Helper that merges live entries and pending-deletes in planner cells |
| `RecipesView.jsx` | `components/mealboard/` | Catalog surface with tabs for Recipes vs Food Items |
| `FoodItemsView.jsx` | `components/mealboard/` | Food-item library with filtering, view toggle, and undo delete flow |
| `ItemCard.jsx` | `components/mealboard/` | Grid-card presentation for recipe and food-item records |
| `ItemRow.jsx` | `components/mealboard/` | List-row presentation for recipe and food-item records |
| `ItemDetailDrawer.jsx` | `components/mealboard/` | Side drawer / bottom sheet for item details (currently recipe-centric) |
| `ItemFormModal.jsx` | `components/mealboard/` | Unified create/edit modal for both recipes and food items |
| `ItemIcon.jsx` | `components/mealboard/` | Shared item icon renderer (emoji, image, or fallback) |
| `ToolbarCount.jsx` | `components/mealboard/` | Reusable count badge/label for catalog toolbars |
| `RecipeImageUpload.jsx` | `components/mealboard/` | Recipe image input/upload control |
| `UnitCombobox.jsx` | `components/mealboard/` | Ingredient unit picker |
| `itemDeleteCopy.jsx` | `components/mealboard/` | Shared delete-confirm copy helpers for item deletion |
| `RecipeFinderView.jsx` | `components/mealboard/` | Placeholder “coming soon” recipe finder screen |

### Behavioral Notes

- `MealboardPage.jsx` owns nested routing; the planner, catalog, and finder are separate subroutes.
- `MealboardNav.jsx` uses an `xl` sidebar on large screens and a dropdown menu below that breakpoint.
- `MealPlannerView.jsx` loads `app-settings`, `meal-slot-types`, `family-members`, items, and week-specific `meal-entries`.
- The planner uses the unified **Item** model: recipes and food items share `useItems`, `ItemFormModal`, `ItemCard`, and `ItemRow`.
- Planner delete UX is inline: deleting a meal swaps the `MealCard` for an `UndoMealCard` in the same lane cell before the entry is purged.
- Catalog delete UX is global: recipe and food-item deletes use the app-level `UndoToastProvider`.
- Compact planner mode kicks in below `768px`, where the weekly swimlane grid is replaced by `MobileDayView`.
- Shopping-list linking now lives inside planner UI (`ShoppingCard` + `ShoppingLinkModal`) and ultimately points to the canonical task-list surface at `/lists`.
- `RecipeFinderView` is present in the nav but intentionally disabled / placeholder.

---

## 4. Settings

**Route:** `/settings`

The `/settings` route is implemented by `pages/FamilyMembersPage.jsx`, which renders a full settings page with multiple cards: family members, timezone, calendar integrations, and mealboard settings.

### Settings Components (8)

| File | Purpose |
|------|---------|
| `ICloudSettings.jsx` | Connect/disconnect iCloud integrations, validate credentials, select calendars, and manage reminder syncing |
| `TimezoneSettings.jsx` | App-wide timezone selection |
| `CalendarSelector.jsx` | Presentational checkbox list for iCloud calendars |
| `ReminderListSelector.jsx` | Presentational checkbox list for iCloud reminder lists |
| `MealboardSettings.jsx` | Mealboard preferences plus meal-slot CRUD |
| `MealSlotCard.jsx` | Editable card for one meal slot type |
| `DayPreview.jsx` | Live one-day preview of active/hidden meal slots |
| `ReminderListSelector.test.jsx` | Reminder-list selector tests |

### Behavioral Notes

- `FamilyMembersPage.jsx` sets the page title to `Settings` and renders all settings surfaces in one page shell.
- `ICloudSettings.jsx` supports both calendar syncing and reminders syncing.
- `MealboardSettings.jsx` loads meal-slot types, family members, and app settings together.
- Mealboard settings use a two-column layout at `lg`, with a sticky `DayPreview` sidebar on larger screens.

---

## 5. Responsibilities

**Route:** `/responsibilities`

`pages/ResponsibilitiesPage.jsx` is the route shell; `components/responsibilities/` contains the reusable feature UI.

### Component Files (5)

| File | Purpose |
|------|---------|
| `ResponsibilityCard.jsx` | Responsibility display card with swipe interactions |
| `ResponsibilityForm.jsx` | Create/edit form for responsibility metadata |
| `ScheduleView.jsx` | Daily schedule grouped by category and family member |
| `ResponsibilityCard.test.jsx` | Card tests |
| `ResponsibilityForm.test.jsx` | Form tests |

### Behavioral Notes

- The page toggles between `Daily View` and `Edit Responsibilities`.
- `ScheduleView.jsx` is the daily tracker surface; editing happens in the separate edit tab.
- Completion state is date-based and loaded alongside family members and responsibilities.
- An additional `ScheduleView` test lives in `frontend/tests/components/ScheduleView.test.jsx`.

---

## 6. Lists

**Route:** `/lists`

`pages/ListsPage.jsx` owns data loading, responsive shell layout, modal state, and task/list API calls. `components/lists/` contains the reusable list UI.

### Files (11)

| File | Purpose |
|------|---------|
| `ListPanel.jsx` | List sidebar as desktop aside and mobile drawer |
| `TaskListView.jsx` | Main sectioned task-list renderer |
| `TaskItem.jsx` | Individual task row with inline editing and expand/collapse behavior |
| `TaskActionArea.jsx` | Sync badges, indicators, and action buttons for a task row |
| `InlineTaskFields.jsx` | Expanded due date, description, assignee, and priority fields |
| `AddTaskRow.jsx` | Reusable “Add a task” row |
| `SectionHeader.jsx` | Inline-editable section header with collapse control |
| `TodoForm.jsx` | Task create/edit modal form |
| `TaskItem.test.jsx` | Task item tests |
| `TodoForm.test.jsx` | Todo form tests |
| `iCloudBadges.test.jsx` | Badge/sync-state tests for list tasks |

### Behavioral Notes

- `ListsPage.jsx` persists the selected list in `localStorage`.
- The mobile/desktop split happens at the Tailwind `sm` breakpoint (`640px`), not `768px`.
- Lists poll every `10s` while any task has `sync_status === 'PENDING_PUSH'`, mirroring the calendar sync pattern.
- The page loads family members once and threads them into task editing surfaces.

---

## 7. Family Members

**Route surface:** `/settings`

Family member management is not a standalone page; it is the first card inside `pages/FamilyMembersPage.jsx`.

### Files (1 source file + tests elsewhere)

| File | Purpose |
|------|---------|
| `FamilyMemberManager.jsx` | Family member CRUD, photo upload, color selection, and avatar handling |

### Notes

- The manager uses shared helpers like `PhotoUpload`, `MemberAvatar`, and `ColorPicker`.
- Tests live in `frontend/tests/components/family-members/FamilyMemberManager.test.jsx`.

---

## 8. Layout

App shell components used across pages.

### Files (4)

| File | Purpose |
|------|---------|
| `Header.jsx` | Top header bar used on most pages |
| `Sidebar.jsx` | Primary app navigation; bottom bar on mobile, left rail on larger screens |
| `DarkModeToggle.jsx` | Shared dark-mode toggle control |
| `AddButton.jsx` | Floating action button for create flows |

---

## 9. Shared

Cross-cutting UI components, helpers, and providers used across multiple features.

### Files (10)

| File | Purpose |
|------|---------|
| `ConfirmDialog.jsx` | Reusable confirmation modal |
| `ToastProvider.jsx` | General toast provider + `useToast` hook |
| `UndoToast.jsx` | Global undo-toast provider + hook for soft-delete flows |
| `EmptyState.jsx` | Shared empty-state components |
| `SwipeableItem.jsx` | Swipe-to-reveal action wrapper |
| `PhotoUpload.jsx` | Image upload with preview |
| `Tooltip.jsx` | Tooltip and truncated-text helpers |
| `ColorPicker.jsx` | Shared family-member color picker |
| `MemberAvatar.jsx` | Avatar/photo fallback renderer for family members |
| `EmojiPicker.jsx` | Lazy-loaded emoji picker built on `emoji-mart` |

---

## 10. Key Patterns

- **Stack:** Vite 7, React 19, React Router 7, Tailwind 4, Axios, Headless UI, Vitest, Testing Library, and MSW.
- **Routing:** `main.jsx` mounts `BrowserRouter`; `App.jsx` owns top-level routes; `MealboardPage.jsx` owns nested `/mealboard/*` routes.
- **Root providers:** `DarkModeProvider`, `ToastProvider`, and `UndoToastProvider` all wrap the app in `main.jsx`.
- **HTTP/data fetching:** Axios is the standard client (`VITE_API_BASE_URL`). In `src/`, data flow is currently driven by component state and custom hooks, not TanStack Query.
- **State management:** Local `useState` / `useEffect`, lightweight context (`DarkModeContext`, toast providers), and some `localStorage` persistence for UI preferences.
- **Unified item model:** Mealboard recipes and food items share the `Item` API surface and frontend primitives such as `useItems`, `ItemFormModal`, `ItemCard`, and `ItemRow`.
- **Responsive patterns:** Tailwind breakpoints are the default pattern, but some features also use explicit media checks (`useMediaQuery`, `window.innerWidth < 768`) for mode switching.
- **Testing layout:** Tests are split between co-located component tests and `frontend/tests/components/` feature tests.
- **Design system:** See [FRONTEND_GUIDELINES.md](./FRONTEND_GUIDELINES.md) for colors, spacing, dark mode, and component styling patterns.
