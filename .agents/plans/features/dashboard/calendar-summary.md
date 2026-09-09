# Calendar Dashboard - Execution Summary

> Tracking execution of `calendar.md` plan

---

## Progress

- [x] **Phase 1**: Backend - FamilyMember color field
- [x] **Phase 2**: Backend - CalendarEvent model + CRUD + routes
- [x] **Phase 3**: Backend - Task date-range filtering
- [x] **Phase 4**: Frontend - Calendar infrastructure
- [x] **Phase 5**: Frontend - Calendar views
- [x] **Phase 6**: Frontend - Quick-add & event modal
- [x] **Phase 7**: Polish, dark mode & tests

---

## Phase Notes

### Phase 1: Backend - FamilyMember Color Field

**Status**: Complete

- Added `color` column (String, nullable) to `FamilyMember` model in `models.py`
- Added `color` field to `FamilyMemberBase` and `FamilyMemberUpdate` schemas
- Migration: `9f725bf2eef2_add_color_to_family_members.py` — adds column + auto-assigns 8-color palette to existing non-system members
- Updated `conftest.py` fixtures with `color` field
- Added integration test: PATCH color → GET verifies response

### Phase 2: Backend - CalendarEvent Model + CRUD + Routes

**Status**: Complete

- New enum `CalendarEventSource` (MANUAL, ICLOUD, GOOGLE) in `models.py`
- New model `CalendarEvent` with: id, title, description, date, start_time (HH:MM), end_time (HH:MM), all_day, source, external_id, assigned_to (FK), family_member relationship, timestamps
- New file: `crud_calendar_events.py` — full CRUD with date-range + assigned_to filtering, `selectinload(family_member)`
- New file: `routes/calendar_events.py` — GET (list/detail), POST, PATCH, DELETE with source-based edit restrictions (only MANUAL events editable/deletable)
- Registered router in `main.py`
- Migration: `a5510f8157a2_add_calendar_events_table.py`
- Pydantic schemas with HH:MM regex validation, end_time > start_time validator
- New test file: `test_calendar_events_api.py` — full CRUD, date-range filtering, assigned_to filtering, PATCH/DELETE rejection for non-MANUAL source

### Phase 3: Backend - Task Date-Range Filtering

**Status**: Complete

- Modified `crud_tasks.py`: added `start_date`, `end_date`, `assigned_to` optional params with DateTime-aware filtering
- Modified `routes/tasks.py`: exposed as query params
- Added integration tests in `test_tasks_api.py`: date-range filtering, assigned_to filtering, params optional (backward compatible)

### Phase 4: Frontend - Calendar Infrastructure

**Status**: Complete

- New directory: `frontend/src/components/calendar/`
- `calendarUtils.js` — 8 exported pure functions: `getMonthGrid`, `getWeekDates`, `getTimeGridHours`, `getTimePosition`, `getEventHeight`, `formatDateKey`, `getMemberColor`, `groupByDate`
- `useCalendarNavigation.js` — state hook: `currentDate`, `viewMode`, `selectedDate`, computed `startDate`/`endDate`, navigation methods
- `useCalendarData.js` — data fetching hook: parallel fetch of tasks + events + familyMembers, client-side activeMembers filtering, returns `{ tasks, events, familyMembers, loading, error, refetch }`
- Updated `App.jsx`: replaced `Dashboard` import with `CalendarPage`, route `/` → `<CalendarPage />`
- Deleted `frontend/src/pages/Dashboard.jsx` (placeholder)
- Updated `tests/mocks/handlers.js`: added calendar-events handlers (GET/POST/PATCH/DELETE with filtering), updated tasks handler with date params, added `color` to mock family members, added mock calendar events data

### Phase 5: Frontend - Calendar Views (12 components)

**Status**: Complete

All 12 components built from scratch (no third-party calendar library):

| Component | Description |
|-----------|-------------|
| `CalendarPage.jsx` | Top-level orchestrator: hooks, filter state, responsive (768px breakpoint), modal state management |
| `CalendarHeader.jsx` | Nav bar: prev/today/next buttons, period label (month/week/day formats), view mode segmented toggle |
| `FamilyMemberFilter.jsx` | Horizontal scrollable avatar row: colored circles with initials, ring for active, opacity for inactive, `aria-pressed` |
| `MonthView.jsx` | 7-column grid: colored dots (max 4 + overflow), today highlight (terracotta), desktop popover, mobile split view |
| `MonthDayPopover.jsx` | Headless UI Popover for desktop day click: CalendarItem list, "View full day" link, quick-add button |
| `MobileDayList.jsx` | Full task+event list for selected day: date heading, CalendarItem rows, quick-add action buttons |
| `WeekViewDesktop.jsx` | 7-column layout: day headers, AllDaySection per column, TimeGrid per column, today highlight |
| `WeekViewMobile.jsx` | Date strip pills (S/M/T/W/T/F/S) with selection highlight + MobileDayList below |
| `DayView.jsx` | Single-column AllDaySection + TimeGrid with empty state message |
| `TimeGrid.jsx` | Vertical 6am–10pm axis (60px/hr, 1020px total), absolutely-positioned events, overlap layout algorithm, 15-min snap slot click |
| `AllDaySection.jsx` | Colored horizontal bars for tasks: member color at 20% opacity + solid left border, strikethrough for completed |
| `CalendarItem.jsx` | Single task/event line: icon (checkbox/clock), member color dot, title, time, strikethrough for completed |

**Key implementation details**:
- Responsive breakpoint at 768px using `useState` + resize listener (matching MealPlannerView pattern)
- Dark mode: all components have `dark:` class pairs (terracotta-500 → blue-600, card-bg → gray-800)
- `layoutEvents()` in TimeGrid handles overlap with equal-width columns
- Grid click handler in TimeGrid calculates time from Y position, snaps to 15-minute intervals

### Phase 6: Frontend - Quick-Add & Event Modal (3 components)

**Status**: Complete

| Component | Description |
|-----------|-------------|
| `QuickAddPopover.jsx` | Headless UI Popover with "New Task" (checkbox icon) and "New Event" (clock icon) buttons |
| `EventFormModal.jsx` | Full Dialog: title, description, date, all-day toggle (hides time inputs), start/end time, assigned-to dropdown. Handles create (POST), edit (PATCH), delete (DELETE). `addOneHour()` helper. Source-based read-only for non-MANUAL events. |
| `TaskFormModal.jsx` | Dialog wrapping existing TodoForm. Fetches lists on open, list selector + TodoForm with pre-filled `due_date`. |

**Wiring**:
- CalendarPage manages modal state (`taskModalOpen`, `eventModalOpen`, `quickAddDate`, `quickAddTime`)
- `handleSlotClick(date, time)` from TimeGrid → opens EventFormModal with pre-filled date+time
- `handleQuickAddTask(date)` / `handleQuickAddEvent(date)` from MonthView/MobileDayList → opens respective modal
- `handleModalSaved()` → calls `refetch()` to refresh calendar data
- MonthDayPopover has "+" task button
- MobileDayList has "+" task and clock event action buttons

### Phase 7: Polish, Dark Mode & Tests

**Status**: Complete

**7A (CSS additions)**: Skipped — all components use inline Tailwind utilities, no custom CSS classes needed.

**7B (Dark mode)**: Already done — all components include `dark:` class pairs throughout.

**7C (Frontend tests)**: 6 test files, 86 tests total:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `calendarUtils.test.js` | 31 | All 8 exported functions: grid generation, date formatting, time positioning, color resolution, grouping |
| `CalendarHeader.test.jsx` | 10 | Period labels (month/week/day), nav button callbacks, view mode toggle + active styling |
| `FamilyMemberFilter.test.jsx` | 9 | Avatar rendering, initials, aria-pressed states, ring/opacity styling, toggle callback, null/empty returns |
| `MonthView.test.jsx` | 13 | 42-cell grid, day headers (desktop/mobile), today highlight, colored dots, mobile tap-to-select + MobileDayList, desktop quick-add popover |
| `TimeGrid.test.jsx` | 9 | Hour labels 6AM–10PM, timed event rendering, all-day skip, slot click with time calculation, empty state |
| `EventFormModal.test.jsx` | 14 | New/Edit titles, date/time pre-fill, all-day toggle hiding time inputs, family member dropdown, POST/PATCH submit, delete for MANUAL only, cancel, closed state |

---

## Bug Fixes During Development

### Timezone Bug in `formatDateKey()`
- **Problem**: Used `.toISOString()` which converts to UTC, causing "today" highlight to show wrong day after 4 PM Pacific
- **Fix**: Changed to local date components (`getFullYear()`, `getMonth()`, `getDate()`)
- **File**: `calendarUtils.js` line 93

### Desktop Month Empty Day Click
- **Problem**: `QuickAddPopover` was built but never wired into `MonthView.jsx`. Empty desktop day cells had no click handler — clicking did nothing.
- **Fix**: Wrapped empty desktop day cells in `QuickAddPopover` so clicking shows "New Task" / "New Event" options
- **File**: `MonthView.jsx` lines 122-150
- **Tests**: Added 3 tests in `MonthView.test.jsx` to cover quick-add popover on empty days

---

## Test Results

```
Frontend: 230 tests passing (86 new calendar + 144 existing)
Backend:  223 tests passing (all existing + new calendar event + task filter tests)
Build:    Clean (no warnings except chunk size advisory)
```

---

## Files Created/Modified

### Backend — Modified (8 files)
| File | Change |
|------|--------|
| `models.py` | Added `FamilyMember.color`, `CalendarEvent` model, `CalendarEventSource` enum |
| `schemas.py` | Added color to FamilyMember schemas, full CalendarEvent schemas with validators |
| `main.py` | Registered `calendar_events` router |
| `crud_tasks.py` | Added `start_date`, `end_date`, `assigned_to` params |
| `routes/tasks.py` | Exposed date-range + assigned_to query params |
| `conftest.py` | Updated fixtures with `color` field |
| `integration/conftest.py` | Added calendar event fixtures |
| `integration/test_tasks_api.py` | Added date-range + assigned_to filter tests |

### Backend — New (5 files)
| File | Purpose |
|------|---------|
| `crud_calendar_events.py` | CalendarEvent CRUD operations |
| `routes/calendar_events.py` | CalendarEvent API endpoints |
| `alembic/.../9f725bf2eef2_*.py` | Color field migration |
| `alembic/.../a5510f8157a2_*.py` | Calendar events table migration |
| `test_calendar_events_api.py` | Integration tests |

### Frontend — Modified (4 files)
| File | Change |
|------|--------|
| `App.jsx` | Route `/` → CalendarPage (was Dashboard) |
| `tests/mocks/handlers.js` | Added calendar-events + updated tasks/family-members mocks |
| `Dashboard.jsx` | Deleted (replaced by CalendarPage) |
| `MealboardNav.test.jsx` | Minor test cleanup |

### Frontend — New Components (18 files in `src/components/calendar/`)
| File | Purpose |
|------|---------|
| `CalendarPage.jsx` | Top-level orchestrator |
| `CalendarHeader.jsx` | Nav bar + view switcher |
| `FamilyMemberFilter.jsx` | Avatar toggle row |
| `MonthView.jsx` | Month grid (desktop + mobile) |
| `MonthDayPopover.jsx` | Desktop day click popover |
| `QuickAddPopover.jsx` | New Task / New Event choice |
| `MobileDayList.jsx` | Mobile day detail list |
| `WeekViewDesktop.jsx` | 7-column time grid |
| `WeekViewMobile.jsx` | Date strip + day details |
| `DayView.jsx` | Single-column time grid |
| `TimeGrid.jsx` | Reusable time axis component |
| `AllDaySection.jsx` | All-day task bars |
| `CalendarItem.jsx` | Single task/event render |
| `EventFormModal.jsx` | CalendarEvent form modal |
| `TaskFormModal.jsx` | Task quick-add modal |
| `calendarUtils.js` | Pure date/color functions |
| `useCalendarData.js` | Data fetching hook |
| `useCalendarNavigation.js` | Navigation state hook |

### Frontend — New Tests (6 files in `tests/components/calendar/`)
| File | Tests |
|------|-------|
| `calendarUtils.test.js` | 31 |
| `CalendarHeader.test.jsx` | 10 |
| `FamilyMemberFilter.test.jsx` | 9 |
| `MonthView.test.jsx` | 13 |
| `TimeGrid.test.jsx` | 9 |
| `EventFormModal.test.jsx` | 14 |

---

## What's Left (Not in this plan)

- iCloud Calendar two-way sync (Phase 2 prep: `source` enum + `external_id` are in place)
- Google Calendar two-way sync
- Drag-and-drop to reschedule events/tasks (deferred from v1, noted in PRD)
- Recurrence for calendar events
- `usePageTitle` hook for "Calendar" page title (already working)
