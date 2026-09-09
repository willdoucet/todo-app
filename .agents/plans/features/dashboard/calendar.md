# Calendar Dashboard - Implementation Plan

> **Feature**: Replace placeholder Dashboard (`/`) with a unified calendar view

---

## Context

The home page (`/`) is currently a placeholder with navigation cards (`frontend/src/pages/Dashboard.jsx`). This plan builds a full calendar dashboard showing tasks with due dates and standalone calendar events, color-coded by family member, with month/week/day views.

---

## Design Decisions (from user)

| Decision | Choice |
|----------|--------|
| Member colors | Add `color` DB field + auto-assign from standard distinct palette |
| Views | Month + Week + Day (all three, all devices) |
| Scope | Full: Tasks + CalendarEvent model + sync prep (source enum) |
| Library | Build from scratch (no third-party calendar) |
| Tasks on calendar | All-day bars at top of day (no time positioning) |
| "Everyone" color | Terracotta (app accent) |
| Week start | Sunday |
| Month density | Colored dots only |
| Desktop month click | Popover with summary + link to day view |
| Family filter | Avatar row with toggles |
| CalendarEvent ownership | Assignable to family member (optional) |
| Completed tasks | Show with visual distinction (strikethrough/faded) |
| Time layout | Time-grid (6am-10pm) for week and day views |
| Quick-add | Click day → popover ('New Task' / 'New Event') → modal form |
| Drag & drop | Not in v1 (note in PRD for future) |
| Recurrence | One-off events only |
| Task vs Event distinction | Different icon (checkbox vs clock) |
| Mobile month | Compact grid with dots, tap → day events below (split view) |
| Mobile week | Horizontal date strip with dot indicators + selected day details |
| Mobile day | Same as desktop (single column scales naturally) |

---

## Phase 1: Backend - FamilyMember Color Field

### 1A. Model change
**File**: `backend/app/models.py` (line 40, after `photo_url`)

Add `color = Column(String, nullable=True)` to `FamilyMember`.

### 1B. Schema changes
**File**: `backend/app/schemas.py`
- `FamilyMemberBase` (line 21): Add `color: Optional[str] = None`
- `FamilyMemberUpdate` (line 30): Add `color: Optional[str] = None`
- `FamilyMember` response inherits from Base, gets `color` automatically

### 1C. Migration
```bash
cd backend && alembic revision --autogenerate -m "add_color_to_family_members"
```
In the migration's `upgrade()`, after adding the column, auto-assign colors to existing non-system members:

```python
DEFAULT_COLORS = [
    "#3B82F6",  # blue
    "#EF4444",  # red
    "#10B981",  # green
    "#8B5CF6",  # purple
    "#F97316",  # orange
    "#14B8A6",  # teal
    "#EC4899",  # pink
    "#6366F1",  # indigo
]
```

### 1D. Tests
- Update `backend/tests/conftest.py` fixtures to include `color` field
- Update `backend/tests/integration/conftest.py` test fixtures
- Add test in `test_family_members_api.py`: PATCH color, verify GET response

---

## Phase 2: Backend - CalendarEvent Model + CRUD + Routes

### 2A. Model
**File**: `backend/app/models.py`

New enum:
```python
class CalendarEventSource(PyEnum):
    MANUAL = "MANUAL"
    ICLOUD = "ICLOUD"
    GOOGLE = "GOOGLE"
```

New model `CalendarEvent`:
- `id` (PK), `title` (String, not null), `description` (String, nullable)
- `date` (Date, indexed, not null)
- `start_time` (String, nullable, HH:MM format) — null = all-day
- `end_time` (String, nullable, HH:MM format) — null = all-day
- `all_day` (Boolean, default False)
- `source` (Enum, default MANUAL)
- `external_id` (String, nullable, unique) — for future sync dedup
- `assigned_to` (FK → family_members.id, nullable) — for color-coding
- `family_member` relationship
- `created_at`, `updated_at`

### 2B. Schemas
**File**: `backend/app/schemas.py`

Follow existing Base/Create/Update/Response pattern:
- `CalendarEventBase`: title, description, date, start_time (regex `^\d{2}:\d{2}$`), end_time, all_day, source, external_id, assigned_to
- `CalendarEventCreate(CalendarEventBase)`
- `CalendarEventUpdate`: all fields optional, source/external_id NOT updatable
- `CalendarEvent(CalendarEventBase)`: + id, family_member (nested), created_at, updated_at

### 2C. CRUD
**New file**: `backend/app/crud_calendar_events.py`

Follow pattern from `crud_tasks.py`:
- `get_calendar_events(db, start_date, end_date, assigned_to=None)` — date range query + optional member filter, `selectinload(CalendarEvent.family_member)`
- `get_calendar_event(db, event_id)`
- `create_calendar_event(db, event)`
- `update_calendar_event(db, event_id, event)`
- `delete_calendar_event(db, event_id)`

### 2D. Routes
**New file**: `backend/app/routes/calendar_events.py`

Follow pattern from `routes/tasks.py`:
- `GET /calendar-events/?start_date=&end_date=&assigned_to=` — date range required
- `GET /calendar-events/{id}`
- `POST /calendar-events/`
- `PATCH /calendar-events/{id}` — reject if source != MANUAL (400)
- `DELETE /calendar-events/{id}` — reject if source != MANUAL (400)

### 2E. Register router
**File**: `backend/app/main.py` — add `app.include_router(calendar_events.router)`

### 2F. Migration
```bash
alembic revision --autogenerate -m "add_calendar_events_table"
```

### 2G. Tests
**New file**: `backend/tests/integration/test_calendar_events_api.py`
- Full CRUD tests, date-range filtering, assigned_to filtering
- Test PATCH/DELETE rejected for non-MANUAL source
- Update `conftest.py` with calendar event fixtures

---

## Phase 3: Backend - Task Date-Range Filtering

### 3A. CRUD change
**File**: `backend/app/crud_tasks.py` — `get_tasks()` (line 7)

Add optional params: `start_date: date = None`, `end_date: date = None`, `assigned_to: int = None`

Filter logic:
- `start_date`: `where(Task.due_date >= datetime.combine(start_date, time.min))`
- `end_date`: `where(Task.due_date <= datetime.combine(end_date, time(23, 59, 59)))` — Task.due_date is DateTime, so end_date must include full day
- `assigned_to`: `where(Task.assigned_to == assigned_to)`

### 3B. Route change
**File**: `backend/app/routes/tasks.py` — `get_tasks()` (line 15)

Add query params: `start_date: date = None`, `end_date: date = None`, `assigned_to: int = None`

### 3C. Tests
**File**: `backend/tests/integration/test_tasks_api.py`
- Test date-range filtering returns correct tasks
- Test assigned_to filtering
- Test params are optional (existing behavior unchanged)

---

## Phase 4: Frontend - Calendar Infrastructure

### 4A. New directory: `frontend/src/components/calendar/`

### 4B. Utility functions
**New file**: `src/components/calendar/calendarUtils.js`

| Function | Purpose |
|----------|---------|
| `getMonthGrid(year, month)` | 6x7 grid of dates, Sunday-start, includes prev/next month padding |
| `getWeekDates(date)` | 7 dates starting from Sunday of the week containing `date` |
| `getTimeGridHours()` | Array `[6, 7, ..., 22]` for 6am-10pm |
| `getTimePosition(timeStr)` | Vertical % position for "HH:MM" within 6am-10pm axis |
| `getEventHeight(startTime, endTime)` | Height % for event duration |
| `formatDateKey(date)` | Format to `YYYY-MM-DD` for API calls and grouping |
| `getMemberColor(member)` | Resolve color: system → terracotta, assigned → member.color, unassigned → gray |
| `groupByDate(items, dateKey)` | Group tasks/events into `{ 'YYYY-MM-DD': [...] }` map |

### 4C. Custom hook: data fetching
**New file**: `src/components/calendar/useCalendarData.js`

Fetches in parallel (following `MealPlannerView.jsx` pattern):
- `GET /tasks?start_date=X&end_date=Y` (tasks with due dates)
- `GET /calendar-events?start_date=X&end_date=Y`
- `GET /family-members`

Returns: `{ tasks, events, familyMembers, loading, error, refetch }`

Client-side filtering by active members (avoids N API calls).

### 4D. Custom hook: navigation
**New file**: `src/components/calendar/useCalendarNavigation.js`

State: `currentDate`, `viewMode` ('month' | 'week' | 'day'), `selectedDate` (for mobile split view)

Computed: `startDate`/`endDate` for the current view range (used by data hook).

Methods: `goToday()`, `goNext()`, `goPrev()`, `setView()`, `setDate()`

### 4E. Route update
**File**: `frontend/src/App.jsx` (line 2, 11)

Replace `Dashboard` import with `CalendarPage`:
```jsx
import CalendarPage from './components/calendar/CalendarPage'
// ...
<Route path="/" element={<CalendarPage />} />
```

### 4F. MSW mock handlers
**File**: `frontend/tests/mocks/handlers.js`

Add calendar-events handlers (GET/POST/PATCH/DELETE), update tasks handler to support date params, add `color` to mock family members.

---

## Phase 5: Frontend - Calendar Views

### 5A. CalendarPage (orchestrator)
**New file**: `src/components/calendar/CalendarPage.jsx`

Top-level component wiring hooks, filter state, and view rendering:
- Uses `useCalendarNavigation()` and `useCalendarData()`
- Renders: `Sidebar` + `Header` + `CalendarHeader` + `FamilyMemberFilter` + active view
- Manages quick-add/modal state
- Responsive: `isMobile` state via resize listener (768px breakpoint, same as `MealPlannerView.jsx`)
- Layout matches existing pages: `min-h-screen bg-gradient-to-br from-warm-cream to-warm-beige dark:from-gray-900 dark:to-gray-800 sm:pl-20`

### 5B. CalendarHeader
**New file**: `src/components/calendar/CalendarHeader.jsx`

- Left: Period label ("February 2026" / "Feb 2 - 8, 2026" / "Sat, Feb 7")
- Center: Prev / Today / Next navigation buttons
- Right: View switcher (Month | Week | Day) as segmented button group

### 5C. FamilyMemberFilter
**New file**: `src/components/calendar/FamilyMemberFilter.jsx`

- Horizontal row of avatar circles with member colors
- Photo or first-letter initial in colored circle
- Click toggles member on/off
- Active = full opacity + color ring, inactive = reduced opacity
- "Everyone" shows terracotta-colored avatar
- Horizontally scrollable on mobile

### 5D. MonthView
**New file**: `src/components/calendar/MonthView.jsx`

**Desktop (>=768px)**:
- 7-column grid (Sun-Sat headers)
- Each cell: day number + up to 4 colored dots (member colors) + "+N" overflow
- Today: terracotta circle behind number
- Click day → `MonthDayPopover`
- Days outside month: muted text

**Mobile (<768px)**:
- Compact grid (smaller cells, 4px dots)
- Tap date → select it (filled terracotta circle)
- Below grid: `MobileDayList` showing selected day's tasks/events (split view)

### 5E. MonthDayPopover (desktop)
**New file**: `src/components/calendar/MonthDayPopover.jsx`

Headless UI Popover anchored to clicked cell:
- Date label
- Task list (checkbox icon + color dot + title, strikethrough if completed)
- Event list (clock icon + color dot + title + time)
- "View full day" link → navigates to day view
- "+" button → triggers quick-add

### 5F. MobileDayList
**New file**: `src/components/calendar/MobileDayList.jsx`

Renders below month/week grid on mobile:
- Full list of tasks and events for selected day
- Each item: icon (checkbox/clock) + title + time + member color dot
- Completed tasks: strikethrough + faded
- "+" button for quick-add

### 5G. WeekViewDesktop
**New file**: `src/components/calendar/WeekViewDesktop.jsx`

- 7-column layout with day headers (Sun-Sat + date number)
- Top: `AllDaySection` — tasks render as colored horizontal bars
- Below: `TimeGrid` per column (6am-10pm, 60px/hour)
- Events positioned vertically via `getTimePosition()`/`getEventHeight()`
- Today column: subtle background highlight
- Click empty slot → quick-add with pre-filled date + time

### 5H. WeekViewMobile
**New file**: `src/components/calendar/WeekViewMobile.jsx`

- Top: horizontal strip of 7 day pills (abbreviation + number)
- Each pill: colored dot indicators below if events/tasks exist
- Selected pill: terracotta background
- Below: `MobileDayList` for selected day

### 5I. DayView
**New file**: `src/components/calendar/DayView.jsx`

- Top: `AllDaySection` with task bars
- Below: Single-column `TimeGrid` (6am-10pm)
- Events as positioned blocks
- Works on both desktop and mobile
- Click empty slot → quick-add with date + time

### 5J. TimeGrid (shared)
**New file**: `src/components/calendar/TimeGrid.jsx`

Reusable vertical time axis:
- Left gutter: hour labels (6 AM ... 10 PM)
- Main area: horizontal lines at each hour, 60px/hour = 960px total
- Events positioned absolutely using `top: getTimePosition()%`, `height: getEventHeight()%`
- Event styling: member color bg at 20% opacity, solid left border in member color
- v1: overlapping events get equal-width columns (simple approach)

### 5K. AllDaySection
**New file**: `src/components/calendar/AllDaySection.jsx`

- Horizontal bars for tasks (due date on this day)
- Each bar: member color bg (faded) + checkbox icon + title
- Completed: strikethrough + extra opacity reduction

### 5L. CalendarItem
**New file**: `src/components/calendar/CalendarItem.jsx`

Small reusable component for a single task or event:
- Icon: checkbox (task) or clock (event)
- Title, time (if applicable), member color dot
- Strikethrough if completed task

---

## Phase 6: Frontend - Quick-Add & Event Modal

### 6A. QuickAddPopover
**New file**: `src/components/calendar/QuickAddPopover.jsx`

Headless UI Popover with two buttons: "New Task" (checkbox icon) + "New Event" (clock icon). Clicking opens the respective modal with pre-filled date (and time if from time slot).

### 6B. Task Quick-Add
Reuse existing `TodoForm` component (`src/components/TodoForm.jsx`) wrapped in Headless UI Dialog:
- Pre-fill `due_date` from clicked calendar date
- Include list selector (dropdown of available lists)
- On save: `POST /tasks`, then `refetch()`

### 6C. EventFormModal
**New file**: `src/components/calendar/EventFormModal.jsx`

Headless UI Dialog (pattern from `AddMealModal.jsx`):
- Fields: Title, Description, Date, All Day toggle, Start Time, End Time (hidden when all-day), Assigned To dropdown
- Create: `POST /calendar-events`
- Edit: `PATCH /calendar-events/{id}`
- Delete: `DELETE /calendar-events/{id}` with confirmation
- On success: `refetch()`

---

## Phase 7: Polish, Dark Mode & Tests

### 7A. CSS additions
**File**: `frontend/src/index.css`

Minimal additions:
```css
.calendar-hour-row { height: 60px; border-bottom: 1px solid var(--color-card-border); }
.dark .calendar-hour-row { border-color: #374151; }
.calendar-month-grid { display: grid; grid-template-columns: repeat(7, 1fr); }
```

### 7B. Dark mode
Follow existing pattern throughout all components:
- `bg-card-bg dark:bg-gray-800`, `text-text-primary dark:text-gray-100`
- Active/accent: terracotta → blue in dark mode (consistent with Sidebar, MealPlanner)

### 7C. Frontend tests

| Test file | Coverage |
|-----------|----------|
| `tests/components/calendar/calendarUtils.test.js` | All pure functions (getMonthGrid, getWeekDates, getTimePosition, getMemberColor, etc.) |
| `tests/components/calendar/CalendarHeader.test.jsx` | View switcher, navigation callbacks |
| `tests/components/calendar/FamilyMemberFilter.test.jsx` | Avatar rendering, toggle interaction |
| `tests/components/calendar/MonthView.test.jsx` | Grid rendering, dots, today highlight |
| `tests/components/calendar/TimeGrid.test.jsx` | Hour labels, event positioning |
| `tests/components/calendar/EventFormModal.test.jsx` | Form submission, validation |

---

## Build Order (Dependency Graph)

```
Phase 1 (Color migration) ──┐
Phase 2 (CalendarEvent)   ──┼──> Phase 4 (Frontend infra) ──> Phase 5 (Views) ──> Phase 6 (Modals) ──> Phase 7 (Polish)
Phase 3 (Task date filter) ──┘
```

- **Phases 1, 2, 3**: Can all execute in parallel (different backend files, except both 1 and 2 touch `models.py` in different sections)
- **Phase 4**: Depends on backend APIs existing
- **Phase 5**: Depends on Phase 4 hooks/utils
- **Phase 6**: Depends on Phase 5 views (modals are triggered from view interactions)
- **Phase 7**: Can overlap with Phase 5/6 (utils tests can be written early)

---

## Files Summary

### Backend - Modified
| File | Change |
|------|--------|
| `backend/app/models.py` | Add FamilyMember.color, CalendarEvent model + enum |
| `backend/app/schemas.py` | Add color to FamilyMember schemas, CalendarEvent schemas |
| `backend/app/main.py` | Register calendar_events router |
| `backend/app/crud_tasks.py` | Add start_date, end_date, assigned_to params |
| `backend/app/routes/tasks.py` | Add start_date, end_date, assigned_to query params |
| `backend/tests/conftest.py` | Update fixtures with color, add calendar event fixtures |
| `backend/tests/integration/conftest.py` | Add calendar event test data |
| `backend/tests/integration/test_tasks_api.py` | Add date-range filter tests |
| `backend/tests/integration/test_family_members_api.py` | Add color field tests |

### Backend - New
| File | Purpose |
|------|---------|
| `backend/app/crud_calendar_events.py` | CalendarEvent CRUD |
| `backend/app/routes/calendar_events.py` | CalendarEvent API routes |
| 2 Alembic migrations | color field + calendar_events table |
| `backend/tests/integration/test_calendar_events_api.py` | Integration tests |

### Frontend - Modified
| File | Change |
|------|--------|
| `frontend/src/App.jsx` | Replace Dashboard import with CalendarPage |
| `frontend/src/index.css` | Add calendar CSS classes |
| `frontend/tests/mocks/handlers.js` | Add calendar-events handlers, update tasks/family-members |

### Frontend - New (18 files)
| File | Purpose |
|------|---------|
| `src/components/calendar/CalendarPage.jsx` | Top-level orchestrator |
| `src/components/calendar/CalendarHeader.jsx` | Nav bar + view switcher |
| `src/components/calendar/FamilyMemberFilter.jsx` | Avatar toggle row |
| `src/components/calendar/MonthView.jsx` | Month grid (desktop + mobile) |
| `src/components/calendar/MonthDayPopover.jsx` | Desktop day click popover |
| `src/components/calendar/MobileDayList.jsx` | Mobile day detail list |
| `src/components/calendar/WeekViewDesktop.jsx` | 7-column time grid |
| `src/components/calendar/WeekViewMobile.jsx` | Date strip + day details |
| `src/components/calendar/DayView.jsx` | Single-column time grid |
| `src/components/calendar/TimeGrid.jsx` | Reusable time axis component |
| `src/components/calendar/AllDaySection.jsx` | All-day task bars |
| `src/components/calendar/CalendarItem.jsx` | Single task/event render |
| `src/components/calendar/QuickAddPopover.jsx` | New Task / New Event choice |
| `src/components/calendar/EventFormModal.jsx` | CalendarEvent form modal |
| `src/components/calendar/useCalendarData.js` | Data fetching hook |
| `src/components/calendar/useCalendarNavigation.js` | Navigation state hook |
| `src/components/calendar/calendarUtils.js` | Pure date/color functions |

### Frontend - New Tests (6 files)
| File |
|------|
| `tests/components/calendar/calendarUtils.test.js` |
| `tests/components/calendar/CalendarHeader.test.jsx` |
| `tests/components/calendar/FamilyMemberFilter.test.jsx` |
| `tests/components/calendar/MonthView.test.jsx` |
| `tests/components/calendar/TimeGrid.test.jsx` |
| `tests/components/calendar/EventFormModal.test.jsx` |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Task.due_date is DateTime not Date — grouping must strip time | `formatDateKey()` uses `.split('T')[0]` consistently |
| Time-grid event overlap rendering | v1: simple equal-width columns for overlapping events |
| Month dot overflow on busy days | Cap at 4 dots + "+N" indicator |
| Sunday vs Monday week start inconsistency with meal planner | Separate implementations — calendar uses Sunday, meal planner keeps Monday |
| Two migrations in one branch | Create Phase 1 migration first, then Phase 2 (sequential alembic revisions) |

---

## Verification

### Backend
```bash
cd backend
alembic upgrade head                          # Apply migrations
uv run pytest tests/unit -v                   # Unit tests pass
uv run pytest tests/integration -v            # Integration tests pass (requires Docker)
```

Manual API checks:
- `GET /family-members` returns `color` field
- `POST /calendar-events` creates event
- `GET /calendar-events?start_date=2026-02-01&end_date=2026-02-28` returns events
- `GET /tasks?start_date=2026-02-01&end_date=2026-02-28` returns tasks with due dates

### Frontend
```bash
cd frontend
npm run test:run                              # All tests pass
npm run dev                                   # Dev server starts
```

Manual UI checks:
- Navigate to `/` → calendar loads (not placeholder dashboard)
- Month/Week/Day view switching works
- Colored dots appear for days with tasks/events
- Family member filter toggles work
- Quick-add creates tasks and events
- Mobile views render correctly at <768px
- Dark mode looks correct in all views

---

## PRD Update Note

Add to PRD.md future roadmap: "Drag-and-drop to reschedule calendar events and tasks" (agreed to defer from v1).
