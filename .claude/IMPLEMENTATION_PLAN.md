# Implementation Plan

> Step-by-step build sequence for remaining features and improvements.

---

## Table of Contents

1. [Current State](#1-current-state)
2. [Phase 1: Calendar Dashboard](#2-phase-1-calendar-dashboard)
3. [Phase 2: CI/CD & Deployment](#3-phase-2-cicd--deployment)
4. [Phase 3: Data & State Improvements](#4-phase-3-data--state-improvements)
5. [Phase 4: User Experience Polish](#5-phase-4-user-experience-polish)
6. [Phase 5: Future Features](#6-phase-5-future-features)

---

## 1. Current State

### Completed Features

| Feature | Backend | Frontend | Tests |
|---------|---------|----------|-------|
| Family Members | CRUD API (with color) | Management UI | Unit + Integration |
| Lists | CRUD API | Sidebar + CRUD | Unit + Integration |
| Tasks | CRUD API | Full UI (create, complete, delete) | Unit + Integration |
| Responsibilities | CRUD API + completions | Daily view + edit mode | Unit + Integration |
| Recipes | CRUD API | Catalog view + form (integrated) | Unit + Integration |
| Meal Plans | **Being overhauled** — MealPlan renamed to MealEntry, new MealSlotType + FoodItem models. See [mealboard overhaul plan](./.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260402-164137.md) | Calendar view + add modal (being replaced by swimlane layout) | Unit + Integration |
| Calendar Events | CRUD API (date-range, source restrictions) | Full calendar UI (18 components, click-to-edit) | Integration + Component |
| iCloud Calendar Sync | CalDAV + Celery + sync engine | Settings UI + EventFormModal updates | Unit + Integration + Component |
| Task Model (priority, subtasks, sections) | Priority (0-9), parent_id, section_id, Sections CRUD | Priority flags, section headers, subtask tree | Unit + Integration + Component |
| iCloud Reminders Sync | CalDAV VTODO + Celery + reminders sync engine | Settings UI + iCloud badges | Unit + Integration |
| File Upload | Upload endpoint | Photo upload component | Integration |
| Dark Mode | N/A | Toggle + persistence | Manual |
| Shopping List | Uses Tasks API | Linked list view (compact in planner, full in recipes) | Manual |

### Known Gaps

1. **Missing Features**
   - iCloud Calendar sync - **built** (CalDAV + Celery + two-way sync); Google Calendar sync - not started
   - iCloud Reminders sync - **built** (CalDAV VTODO + Celery + two-way sync with subtask resolution)
   - CI/CD pipeline for production deployment - not started
   - Recipe Finder (AI-powered) - placeholder only
   - ~~Auto-generate shopping list from meal plan ingredients~~ — **addressed by mealboard overhaul** (ingredient aggregation with unit conversion, async Celery sync)
   - Notifications/reminders

2. **Active Overhaul**
   - **Mealboard overhaul** is the next major feature — flexible meal slots, per-person meals, food items, swimlane UI, shopping list auto-sync. See [mealboard-main-page-updates plan](./.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260402-164137.md).

3. **Polish Items**
   - Loading states
   - Error boundaries
   - Optimistic updates
   - Form validation feedback

---

## 2. Phase 1: Calendar Dashboard

**Goal:** Build unified calendar as the home page, integrating tasks and external calendars. Meal plans remain separate in Mealboard.

### Step 2.1: Calendar UI Foundation ✅

**Files created** (18 components in `frontend/src/components/calendar/`):
- CalendarPage, CalendarHeader, FamilyMemberFilter
- MonthView, MonthDayPopover, QuickAddPopover, MobileDayList
- WeekViewDesktop, WeekViewMobile, DayView
- TimeGrid, AllDaySection, CalendarItem
- EventFormModal, TaskFormModal
- calendarUtils.js, useCalendarData.js, useCalendarNavigation.js

**Completed:**
- [x] CalendarPage as home route (`/`), replaced Dashboard
- [x] MonthView with colored dots, desktop popover, mobile split view
- [x] WeekViewDesktop (7-column time grid) + WeekViewMobile (date strip + day list)
- [x] DayView with single-column TimeGrid
- [x] View switching (month/week/day segmented toggle)
- [x] Navigation (prev/today/next with period-aware labels)
- [x] Responsive at 768px breakpoint
- [x] Dark mode throughout

### Step 2.2: Integrate Existing Data ✅

**Completed:**
- [x] Parallel fetch of tasks + events + family members via `useCalendarData` hook
- [x] Color-coded by family member (member.color from palette)
- [x] FamilyMemberFilter toggle row for client-side filtering
- [x] EventFormModal for create/edit/delete calendar events
- [x] TaskFormModal for create and edit (PATCH/DELETE, list selector)
- [x] Quick-add from month grid (click empty day → QuickAddPopover), time grid (click slot → task/event choice popup)
- [x] Click-to-edit: click any item opens edit modal; checkbox toggles task completion
- [x] Callback threading: CalendarPage → views → leaf components (onEditTask/onEditEvent/onToggleComplete)
- [x] AllDaySection: checkbox + click-to-edit on task bars
- [x] TimeGrid: event block click with stopPropagation opens edit modal
- [x] MonthDayPopover: render props for close(), click item closes popover then opens edit
- [x] MobileDayList/CalendarItem: click + toggle complete handlers
- [x] 274 frontend tests across 20 test files

### Step 2.3: Calendar Events Backend ✅

**Files created/modified:**
- `backend/app/models.py` - Added CalendarEventSource enum + CalendarEvent model + FamilyMember color
- `backend/app/schemas.py` - Added CalendarEvent schemas with HH:MM time validation
- `backend/app/crud_calendar_events.py` - CRUD with date-range filtering and eager-loaded family_member
- `backend/app/routes/calendar_events.py` - Full CRUD endpoints with source-based restrictions
- `backend/alembic/versions/9f725bf2eef2_add_color_to_family_members.py`
- `backend/alembic/versions/a5510f8157a2_add_calendar_events_table.py`
- `backend/tests/integration/test_calendar_events_api.py` - 18 integration tests

**Completed:**
- [x] Create CalendarEvent model with source enum (MANUAL, ICLOUD, GOOGLE)
- [x] Create Pydantic schemas with time format + end > start validation
- [x] Implement CRUD operations
- [x] Add API routes (PATCH/DELETE restricted to MANUAL source)
- [x] Create Alembic migrations (color + calendar_events table)
- [x] Add FamilyMember color field with auto-assign palette
- [x] Integration tests (18 tests, all passing)

### Step 2.4: iCloud Calendar Integration ✅

**Completed (9-phase implementation — see `.claude/plans/features/dashboard/icloud-setup-plan-summary.md`):**
- [x] Infrastructure: Celery + Redis for background task processing (10-min beat schedule)
- [x] Data model: CalendarIntegration table, sync columns on CalendarEvent, Fernet encryption
- [x] CalDAV client: connect, list calendars (with color), fetch/create/update/delete events, ICS mapping
- [x] Sync engine: pull_from_icloud (create/update/delete detection), push_to_icloud, conflict resolution (last-write-wins)
- [x] Celery tasks: sync_all_icloud_integrations, sync_single_integration, push_event_to_icloud, push_delete_to_icloud
- [x] API endpoints: 6 endpoints in `/integrations` (validate, connect, list, get, sync, disconnect)
- [x] Frontend: ICloudSettings component (4-state UI), CalendarSelector, connection flow, polling for SYNCING
- [x] EventFormModal: iCloud badge, PENDING_PUSH indicator, confirmation dialogs for edit/delete of synced events
- [x] Tests: 57 new tests (26 unit, 17 backend integration, 14 frontend)

### Step 2.5: Google Calendar Integration

**Tasks:**
- [ ] Set up Google Cloud project and OAuth credentials
- [ ] Create integration settings UI
- [ ] Implement OAuth 2.0 flow
- [ ] Build sync service using Google Calendar API
- [ ] Store external_id for two-way sync
- [ ] Handle conflict resolution

---

## 3. Phase 2: CI/CD & Deployment

**Goal:** Automated testing, deployment pipeline, and easy access for users.

### Step 3.1: CI Pipeline Enhancement

**Files to modify:**
- `.github/workflows/test.yml`

**Tasks:**
- [ ] Ensure all tests run on every PR
- [ ] Add linting step (ESLint + Python linting)
- [ ] Add type checking if applicable
- [ ] Block merge on test failure
- [ ] Add test coverage reporting

### Step 3.2: CD Pipeline Setup

**Files to create:**
- `.github/workflows/deploy.yml`
- `fly.toml` or equivalent hosting config

**Tasks:**
- [ ] Choose hosting platform (Fly.io recommended)
- [ ] Create production environment
- [ ] Set up managed PostgreSQL
- [ ] Configure environment variables securely
- [ ] Build and push Docker images on main branch merge
- [ ] Auto-deploy to staging
- [ ] Manual promotion to production (or auto with approval)

### Step 3.3: Production Infrastructure

**Tasks:**
- [ ] Set up production PostgreSQL (Fly Postgres / Supabase / Railway)
- [ ] Configure S3-compatible storage for uploads (Cloudflare R2 / AWS S3)
- [ ] Set up SSL certificates (auto-provisioned)
- [ ] Configure custom domain (optional)
- [ ] Set up health checks and monitoring
- [ ] Add error tracking (Sentry)

### Step 3.4: Easy User Access

**Tasks:**
- [ ] Deploy to public URL (e.g., familyhub.fly.dev)
- [ ] Create landing page with app access
- [ ] Document self-hosting option with Docker Compose
- [ ] Add one-click deploy buttons (Railway, Render)
- [ ] Write user onboarding guide

**Deployment checklist:**
```
[ ] CI tests pass on all PRs
[ ] CD deploys automatically on main merge
[ ] Production environment accessible via public URL
[ ] Database backups configured
[ ] File uploads working in production
[ ] SSL/HTTPS enabled
[ ] Error tracking active
[ ] Health monitoring in place
```

---

## 4. Phase 3: Data & State Improvements

**Goal:** Improve data fetching patterns and state management.

> Note: This phase can run in parallel with Calendar and CI/CD work.

### Step 2.1: Introduce React Query

**Files to create/modify:**
- `frontend/src/lib/queryClient.js` (new)
- `frontend/src/main.jsx`
- All components with API calls

**Tasks:**
- [ ] Set up QueryClientProvider in main.jsx
- [ ] Create custom hooks for each entity:
  - `useRecipes()`, `useRecipe(id)`
  - `useMealPlans(startDate, endDate)`
  - `useTasks(listId)`
- [ ] Implement mutations with optimistic updates
- [ ] Add stale time and cache configuration

**Example hook:**
```javascript
// hooks/useRecipes.js
export function useRecipes(favoritesOnly = false) {
  return useQuery({
    queryKey: ['recipes', { favoritesOnly }],
    queryFn: () => axios.get('/recipes', { params: { favorites_only: favoritesOnly } })
      .then(res => res.data)
  })
}

export function useCreateRecipe() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data) => axios.post('/recipes', data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recipes'] })
  })
}
```

### Step 2.2: Centralize API Client

**Files to create:**
- `frontend/src/lib/api.js`

**Tasks:**
- [ ] Create axios instance with base URL
- [ ] Add request/response interceptors
- [ ] Centralize error handling
- [ ] Add request timeout

```javascript
// lib/api.js
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
})

api.interceptors.response.use(
  response => response,
  error => {
    // Centralized error handling
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)
```

---

## Phase 3.5: Inline Task Editing & Card Redesign

**Goal:** Replace modal-based task editing with Apple Reminders-style inline editing. Frontend-only change.
**Branch:** `lists-ui-update-inline-edits`
**Plan:** `.claude/plans/features/lists-ui-update-inline-edits/lists-ui-update-inline-edits-plan-20260401-161442.md`
**Mockup:** `.claude/mockups/inline-edit-mockup-b.html`

**Key changes:**
- Click task → edit title inline (no modal on desktop)
- Expand/contract button reveals detail fields (date, description, assignee, priority)
- Auto-save per field on blur (debounced 500ms)
- Per-section "Add a task" rows
- Mobile: inline title editing + modal for full fields
- Desktop: modal removed entirely
- "Crisp Defined" visual treatment with bordered action area, round checkboxes, inset expansion panel

**Status:** Plan approved + CEO reviewed. Ready for implementation.

---

## Phase 3.6: Mealboard Overhaul — Flexible Slots + Per-Person Meals

**Goal:** Replace rigid B/L/D meal planner with user-configurable slot types, per-person meal assignment, first-class simple food items, and a swimlane UI.
**Branch:** `mealboard-main-page-updates`
**Plan:** [`.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260402-164137.md`](./.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260402-164137.md)

### New Models

| Model | Purpose |
|-------|---------|
| `MealSlotType` | User-configurable meal slots (replaces hardcoded B/L/D enum). Ships with smart defaults: Breakfast, Lunch, Dinner, Snack. |
| `FoodItem` | Lightweight non-recipe food items (banana, yogurt). Reusable across meal entries. Browsable via new tab on Recipes page. |
| `MealEntry` | Renamed from `MealPlan`. Links to slot type, recipe OR food item OR custom text. Tracks `was_cooked`, `shopping_sync_status`. |
| `meal_entry_participants` | Junction table for per-person meal assignment. Defaults to "everyone" via 3-level fallback (entry > slot default > all members). |

### Implementation Phases

1. **Phase 1 — Backend data model + API:** MealSlotType + FoodItem models, MealPlan-to-MealEntry migration (hand-written), updated CRUD + routes, predefined unit system, shopping list auto-sync with ingredient aggregation (Celery), Task model additions (`source_meals`, `aggregation_key_name`, `aggregation_unit_group`).
2. **Phase 2 — Settings UI + Food Items:** Meal slot configuration on Settings page (inline editing, color picker, default participants, live day preview). Food Items tab on Recipes page (grid/list view, emoji auto-suggest).
3. **Phase 3 — Planner overhaul:** Horizontal swimlane layout (rows = slot types, cols = days). New MealCard component (recipe + food item variants). Add-meal popover with unified search. Shopping card states. All interaction states per approved mockup.
4. **Phase 4 — Progress tracker + polish:** Multi-slot progress tracker, shopping sync failure warnings, toast notifications, eager loading, mobile responsive pass.

### Key Design Decisions

- **Smart Defaults + Override** approach: works out of the box, customize when needed
- **Predefined unit system** (weight/volume/count/none) replaces freeform text to enable reliable aggregation
- **Shopping list auto-sync** via Celery with aggregation key + unique constraint for concurrency safety
- **Participant resolution** eagerly materialized at write time for simpler queries

**Status:** Phases 1-4 complete (4 commits). Aggregation rework, UX polish, and initial recipes redesign executed in session.

---

## Phase 3.7: Recipes Page Redesign — Card Grid + Toolbar + List View

**Goal:** Redesign the recipes page with dense 5-column card grid, Airbnb-style hearts, toolbar parity with Food Items, list view, tag filters, and recipe image upload.
**Branch:** `mealboard-main-page-updates`
**Plan:** [`.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260405-180444.md`](./.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260405-180444.md)

**Key changes:**
- RecipeCard: 5/row max, `repeat(5, 1fr)`, 16:9 gradient placeholders (no letters/emojis), Airbnb floating hearts, staggered entrance animations (capped 800ms)
- RecipeRow: new list view component with gradient dot, inline heart, hover edit/delete
- Toolbar: mirrors Food Items (search + grid/list toggle + sort pill + add button)
- Tag filter chips: extracted from recipe tags, multi-select
- Recipe image upload UI in RecipeFormModal
- View preference persistence in localStorage
- Shared `recipeGradients.js` utility

**Status:** Plan approved (office hours + CEO review EXPANSION). Eng review required.

---

## Phase 3.8: Mealboard Polish Round 2 — Bugs, UX, Icon Upload, Soft-Delete, AI Suggest

**Goal:** Fix three user-facing bugs, apply consistent UX polish to the meal planner + recipe/food-item surfaces, add recipe delete with cascade, add food-item icon upload (file + URL) as an alternative to emoji, add emoji-mart with search, and introduce soft-delete with 15-second undo toast across recipes + food items + meal entries.
**Branch:** `mealboard-main-page-updates`
**Plan:** [`.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260413-135505.md`](./.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260413-135505.md)

**Key changes (beyond original 13 source tasks — expanded via CEO review 2026-04-13):**

- **Bug fixes:** `step="any"` on recipe ingredient quantity (fixes `0.25 cups` validation), `MealPlannerView` wires `RecipeFormModal` for edit-from-drawer, `RecipeFormModal` useEffect guard to eliminate cancel-flash.
- **UX polish:** Food-item meal card horizontal + shrunk, day/date entrance animation (Framer Motion stagger), "Jump to Today" button relocated outside week selector with inline-above mobile layout, click-to-edit food item cards, smaller Food Items tab cards.
- **New: recipe delete** — drawer + edit modal buttons, destructive confirm dialog, soft-delete with cascade through meal entries.
- **New: food item delete symmetry** — food items also soft-delete + cascade (changed from detach-on-delete per CEO review).
- **New: icon upload** — `icon_url` column on `food_items`, `/uploads/food-item-icon` route, file + URL + XOR emoji/icon toggle, MIME allow-list (PNG/JPEG/WebP — SVG disallowed for security), 1MB max, 512x512 max dimensions, reusable `<ItemIcon>` component.
- **New: emoji picker** — `@emoji-mart/react` replacing hand-rolled picker (gated on bundle size ≤250KB gzipped + keyboard a11y match), with Recently Used section enabled.
- **New: soft-delete + 15s undo** — `deleted_at` columns on recipes + food_items, `soft_hidden_at` on meal_entries, merged undo toast (Gmail-style "N items deleted. Undo all"), Celery beat hard-delete job runs hourly for entries > 24h, feature-flag gated (`MEALBOARD_SOFT_DELETE_ENABLED`).
- **New: AI icon suggest** — `/food-items/suggest-icon` endpoint, Claude Haiku call, permanent DB cache (`icon_suggestions` table keyed by lowercased name), prompt-injection-hardened (instruction-like keywords stripped from input, defensive system prompt), 400ms debounce on the form field, feature-flag gated (`MEALBOARD_AI_SUGGEST_ENABLED`).
- **New: delight adds** — auto-focus + scroll to first form validation error (generic hook), keyboard shortcut hints footer (⌘S save, Esc cancel) wired on all three form modals, cooked-state scale-pulse animation on MealCard.
- **New: query layer** — `active_only()` SQLAlchemy mixin so every SELECT on recipes/food_items/meal_entries filters soft-deleted rows without repetition.

**Migrations (one Alembic revision, six ops):**
1. Add `deleted_at` to `recipes` (nullable)
2. Add `deleted_at` to `food_items` (nullable)
3. Add `soft_hidden_at` to `meal_entries` (nullable)
4. Change `meal_entries.recipe_id` FK to `ON DELETE CASCADE` (drop + recreate)
5. Change `meal_entries.food_item_id` FK from `SET NULL` to `ON DELETE CASCADE` (drop + recreate)
6. Add `icon_url` column to `food_items`
7. Add `icon_suggestions` table (`id`, `name_key UNIQUE`, `emoji`, `created_at`)
8. Partial indexes on `(deleted_at) WHERE deleted_at IS NOT NULL` for recipes and food_items; same on `soft_hidden_at` for meal_entries.

**New feature flags:** `MEALBOARD_SOFT_DELETE_ENABLED`, `MEALBOARD_AI_SUGGEST_ENABLED` (env-var flag, flip to disable on runtime issue).

**New observability:** Counters for `icon_upload.*`, `claude_suggest.cache_hit/miss/latency/failure`, `soft_delete.scheduled/undone`, `hard_delete.completed`. Structured logs with `user_id` + `entity_id` + `op` at entry/exit of soft-delete, undo, hard-delete, upload, suggest.

**Status:** Plan approved (office hours + CEO review EXPANSION 2026-04-13). Eng review required. Review report in plan file.

**Prerequisite chunk in this batch — Unified Item Model Refactor (Chunk 0):** The 2026-04-13 CEO review follow-up promoted the Item model unification from a deferred P1 TODO into the first chunk of this batch. All subsequent chunks now operate on the unified `Item` model with `item_type` discriminators. Schema: `items` table with shared lifecycle fields (name, icon_emoji, icon_url, tags, is_favorite, deleted_at) + `recipe_details` and `food_item_details` tables keyed by `item_id`. `meal_entries.recipe_id` and `meal_entries.food_item_id` collapse into a single `meal_entries.item_id FK`. Data-preserving migration backfills existing recipes and food items into the new schema atomically. Frontend uses thin wrappers (`RecipeCard`, `FoodItemCard`) over shared bases (`ItemCardBase`, `ItemFormBase`). See plan Chunk 0.1-0.8 for full spec. Net effort: adds ~2 weeks human upfront but halves every subsequent chunk.

---

## Phase 3.9: AI Recipe Import from URL

**Goal:** Paste a recipe URL into the add-recipe modal and have AI extract the full recipe (name, ingredients with decomposed quantity/unit/category, instructions, times, servings, tags) into a smart preview card. User confirms, form pre-fills, save via existing flow.
**Branch:** `mealboard-ai-recipe-creator`
**Plan:** [`.claude/plans/features/mealboard-ai-recipe-creator/mealboard-ai-recipe-creator-plan-20260416-151059.md`](./.claude/plans/features/mealboard-ai-recipe-creator/mealboard-ai-recipe-creator-plan-20260416-151059.md)

**Key changes:**
- **Shared AI service layer** — `services/ai_client.py` (Anthropic SDK, structured extraction, retry, cost logging). Foundation for all future AI features.
- **Async extraction pipeline** — Celery task: fetch page (httpx) → clean HTML (BS4) → optional recipe-scrapers pre-processing → Claude API structured extraction → Pydantic validation → Redis result
- **Two new endpoints** — `POST /items/import-from-url` (submit URL, get task ID) + `GET /items/import-status/{task_id}` (poll for result)
- **SSRF protection** — URL validation gate rejecting private/reserved IPs and localhost
- **Source URL tracking** — `source_url` column on `RecipeDetail` + Alembic migration
- **suggest-icon upgrade** — 501 stub replaced with real AI implementation using shared service layer
- **Frontend** — Tab switcher (Manual/From URL) in RecipeFormBody, `RecipeUrlImport` component (4 states: input/loading/preview/error), `useRecipeImport` polling hook, clipboard paste detection
- **New deps** — `anthropic`, `recipe-scrapers`, `beautifulsoup4`, `httpx` (moved from test to prod)

**Status:** Plan approved (office hours + CEO review EXPANSION 2026-04-16). Eng review required.

---

### Phase 3.8: Mealboard Meal-Card Polish (Active — Plan Approved)

**Goal:** Five small UX improvements to the weekly mealboard: expand-on-hover action reveal, remove redundant view-recipe button, in-place 5-second undo after delete, drop servings metadata, fix text-cursor on day-header row.
**Branch:** `mealboard-meal-card-polish`
**Plan:** [`.claude/plans/features/mealboard-meal-card-polish/mealboard-meal-card-polish-plan-20260417-213900.md`](./.claude/plans/features/mealboard-meal-card-polish/mealboard-meal-card-polish-plan-20260417-213900.md)

**Key changes:**
- **New `undo_token` pattern** — column sidecar on `meal_entries` + `POST /meal-entries/{id}/undo` endpoint, 6.5s server window, in-place `UndoMealCard` (not toast). Distinct from cascade soft-delete toast.
- **Shopping-list round-trip on undo** — sync-remove on soft-delete, sync-add on undo (per CEO review Issue 1.1).
- **Hover-expand animation** — `max-height` transition on action zone (desktop only); mobile retains always-expanded buttons; `prefers-reduced-motion` gated.
- **Sweeper extension** — second pass for user-undo entries with 15s grace period.
- **Observability** — structured logs for soft_delete / undo_success / undo_failed / undo_sync_add_failed.

**Status:** Plan approved + CEO review CLEAR (HOLD SCOPE, 2026-04-17). Eng review required before implementation.

---

## 5. Phase 4: User Experience Polish

**Goal:** Improve loading states, error handling, and feedback.

### Step 3.1: Loading States

**Tasks:**
- [ ] Add skeleton loaders for:
  - Recipe grid (3x3 skeleton cards)
  - Meal calendar (skeleton day columns)
  - Task list (skeleton items)
- [ ] Add loading spinner for form submissions
- [ ] Disable buttons during loading

**Example skeleton:**
```jsx
function RecipeCardSkeleton() {
  return (
    <div className="animate-pulse bg-card-bg border border-card-border rounded-xl p-4">
      <div className="h-32 bg-warm-sand rounded-lg mb-3" />
      <div className="h-4 bg-warm-sand rounded w-3/4 mb-2" />
      <div className="h-3 bg-warm-sand rounded w-1/2" />
    </div>
  )
}
```

### Step 3.2: Error Handling

**Tasks:**
- [ ] Create ErrorBoundary component
- [ ] Add toast notifications for:
  - Success: "Recipe saved"
  - Error: "Failed to save. Please try again."
- [ ] Handle network errors gracefully
- [ ] Add retry buttons for failed requests

### Step 3.3: Form Validation Feedback

**Tasks:**
- [ ] Add inline validation messages
- [ ] Highlight invalid fields with red border
- [ ] Show character count for limited fields
- [ ] Disable submit until form is valid

---

## 6. Phase 5: Future Features

### 5.1: Shopping List Generation — Superseded by Mealboard Overhaul

> **This feature is now part of Phase 3.6 (Mealboard Overhaul).** The overhaul implements automatic shopping list sync with ingredient aggregation, unit conversion, and Celery-based async processing. See the [mealboard overhaul plan](./.claude/plans/features/mealboard-main-page-updates/mealboard-main-page-updates-plan-20260402-164137.md) for full spec.

### 5.2: Recipe Finder (AI-Powered)

**Description:** Suggest recipes based on available ingredients or preferences.

**Backend tasks:**
- [ ] Integrate with AI API (OpenAI/Anthropic)
- [ ] Create endpoint `POST /recipes/suggest`
- [ ] Accept: available ingredients, dietary restrictions, cuisine preference
- [ ] Return: list of suggested recipes with instructions

**Frontend tasks:**
- [ ] Build RecipeFinderView with:
  - Ingredient input (multi-select or free text)
  - Preference filters
  - Results display
  - "Add to Recipes" button

### 5.3: Recurring Meal Plans

**Description:** Set meals to repeat weekly/monthly.

**Database changes:**
- [ ] Add `recurrence` column to meal_plans (NULL, WEEKLY, BIWEEKLY, MONTHLY)
- [ ] Add `recurrence_end_date` column

**Backend tasks:**
- [ ] Modify meal plan creation to handle recurrence
- [ ] Create background job to generate future instances
- [ ] Handle deletion of recurring series

### 5.4: Notifications

**Description:** Remind users of upcoming tasks and meal prep.

**Options:**
1. Browser notifications (Web Push API)
2. Email notifications
3. In-app notification center

**Tasks:**
- [ ] Research notification approach
- [ ] Design notification preferences UI
- [ ] Implement backend notification service
- [ ] Create notification triggers for:
  - Task due today
  - Responsibility not completed
  - Meal prep reminder (night before)

---

## Prioritization

### Critical for v1 Launch

1. ~~**Phase 1** - Calendar Dashboard~~ ✅ Complete (18 components, click-to-edit, 289 frontend tests, 273 backend tests)
2. ~~**Phase 1.4** - iCloud Calendar Integration~~ ✅ Complete (CalDAV + Celery + two-way sync + 57 new tests)
3. ~~**Phase 1.6** - Task Model Enhancement~~ ✅ Complete (priority, subtasks, sections, sync metadata)
4. ~~**Phase 1.7** - iCloud Reminders Sync~~ ✅ Complete (CalDAV VTODO + Celery + two-way sync + 26 new tests)
5. **Phase 2** - CI/CD & Deployment (users can access the app)

### High Priority (v1 Polish)

4. **Phase 3.1** - React Query (better data management)
5. **Phase 4.1** - Loading States
6. **Phase 4.2** - Error Handling

### Medium Priority (Post-v1)

7. **Phase 1.5** - Google Calendar Integration
8. ~~**Phase 5.1** - Auto-generate Shopping List from Recipes~~ (superseded by Phase 3.6 Mealboard Overhaul)
9. **Phase 3.2** - Centralize API Client

### Lower Priority (Future)

10. **Phase 4.3** - Form Validation Feedback
11. **Phase 5.2** - Recipe Finder (AI)
12. **Phase 5.3** - Recurring Meal Plans
13. **Phase 5.4** - Notifications

---

## Testing Strategy

### For Each Phase

1. **Unit tests** for new utility functions
2. **Component tests** for new UI components
3. **Integration tests** for API interactions
4. **Manual QA checklist**:
   - [ ] Works on mobile (375px)
   - [ ] Works on tablet (768px)
   - [ ] Works on desktop (1280px+)
   - [ ] Dark mode looks correct
   - [ ] Loading states appear
   - [ ] Errors handled gracefully

### Test Commands

```bash
# Frontend (via Docker — 321 tests)
docker-compose exec frontend npm run test:run        # Run all tests
docker-compose exec frontend npm run test:coverage   # With coverage

# Backend (via Docker — 325 tests)
docker-compose exec api uv run pytest                      # All tests
docker-compose exec api uv run pytest tests/unit -v        # Unit tests only
docker-compose exec api uv run pytest tests/integration -v # Integration tests
```
