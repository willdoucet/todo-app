# Product Requirements Document (PRD)
# Family Hub - Task & Meal Management App

**Version:** 1.0 Draft
**Last Updated:** April 2026
**Author:** William Doucet

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Target Users](#3-target-users)
4. [Success Criteria](#4-success-criteria)
5. [Feature Specifications](#5-feature-specifications)
6. [Non-Goals & Out of Scope](#6-non-goals--out-of-scope)
7. [Technical Requirements](#7-technical-requirements)
8. [Data Model](#8-data-model)
9. [User Flows](#9-user-flows)
10. [Edge Cases & Business Rules](#10-edge-cases--business-rules)
11. [Future Roadmap](#11-future-roadmap)

---

## 1. Executive Summary

**Family Hub** is a unified family management application that consolidates task lists, recurring responsibilities, and meal planning into a single, accessible platform. Designed for nuclear families with children ages 3+, it provides parents with comprehensive household management tools while giving kids an age-appropriate interface for viewing and completing their daily responsibilities.

### Core Value Proposition

> One place to see everything: what needs to be done, who's doing it, and what's for dinner.

### Project Status

- **Current state:** Personal project with functional MVP
- **Target state:** Deployed web application accessible to friends and families
- **Tech stack:** FastAPI backend, React 19 frontend, PostgreSQL database

---

## 2. Problem Statement

### The Pain

Managing a household involves juggling multiple disconnected systems:
- Task lists on phones (Apple Reminders, notes apps)
- Separate calendar applications
- No systematic tracking of kids' daily routines/chores
- Meal planning scattered across cookbooks, websites, and memory
- No visibility into "did the kids actually do their morning routine?"

### The Solution

A unified family hub that:
1. Centralizes all household tasks with family member assignments
2. Tracks recurring responsibilities (chores, routines) with daily completion status
3. Plans weekly meals with recipe management
4. Syncs across all family devices
5. Provides age-appropriate views for children

### The "Aha Moment"

Users realize the app's value when they find themselves using it every day and notice reduced stress from not having to mentally track everything across multiple systems.

---

## 3. Target Users

### Primary Persona: Parent/Household Manager

**Demographics:** Adult (25-50), manages household operations
**Goals:**
- See all family tasks and responsibilities in one place
- Assign chores to kids and track completion
- Plan weekly meals efficiently
- Reduce mental load of household management

**Usage Pattern:**
- Daily: Check dashboard, review kids' responsibility completion, manage tasks
- Weekly: Plan meals, review upcoming tasks, adjust schedules

### Secondary Persona: Child (Ages 3+)

**Demographics:** Child in household, varying tech literacy
**Goals:**
- Know what they need to do today
- Mark responsibilities as complete
- Feel accomplished when tasks are done

**Usage Pattern:**
- Morning/Evening: View daily schedule, mark routines complete
- Limited interaction with task creation (view-only for most features)

### Household Composition

Designed primarily for nuclear families (2 parents + children), but flexible enough for:
- Single-parent households
- Multi-generational homes
- Shared living situations

---

## 4. Success Criteria

### Primary Metric

**Family uses the app daily for 3+ consecutive months**

### Secondary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily active users per household | 2+ family members | Login/action tracking |
| Responsibility completion rate | >80% of assigned responsibilities marked complete | Completion records |
| Meal planning adoption | >5 meals planned per week | MealEntry records |
| Task completion rate | >70% of tasks completed within 7 days of creation | Task completion timestamps |

### Qualitative Success

- Users report reduced stress around household management
- Kids engage with their responsibility schedule without constant reminders
- Meal planning becomes a weekly habit rather than daily scramble

---

## 5. Feature Specifications

### Priority Ranking

| Priority | Feature | Status |
|----------|---------|--------|
| P0 | Task Management (Lists & Tasks) | Built |
| P0 | Responsibilities (Recurring Routines) | Built |
| P1 | Meal Planning (Flexible Swimlane Calendar) | Rebuilding |
| P1 | Recipe Management | Built |
| P1 | User Authentication | Planned — [see plan](./plans/features/prod-contract-freeze/prod-contract-freeze-plan-20260421-182714.md) |
| P2 | Shopping Lists (with meal auto-sync) | Rebuilding |
| P2 | Notifications/Reminders | Not Started |
| P2 | iCloud Calendar Sync | Built |
| P3 | Family Member Management | Built |
| P3 | Gamification (Points, Streaks) | Not Started |
| P3 | Add Recipe from URL (AI) | Planned — [see plan](./plans/features/mealboard-ai-recipe-creator/mealboard-ai-recipe-creator-plan-20260416-151059.md) |
| P1 | Calendar (Dashboard Home) | Built |
| P1 | CI/CD & Easy Deployment | Planned — [see plan](./plans/features/prod-contract-freeze/prod-contract-freeze-plan-20260421-182714.md) |

---

### 5.1 Task Management

**Purpose:** Organize household tasks into categorized lists with family member assignments.

#### Features

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| Create List | User creates a named task list with optional color and icon | List appears in sidebar, persists across sessions |
| Create Task | User creates task with title, optional description, due date, importance flag | Task appears in list, shows all fields correctly |
| Assign Task | Task assigned to specific family member or "Everyone" | Assignment visible on task, filterable |
| Complete Task | Toggle task completion status | Visual indication of completion, timestamp recorded |
| Mark Important | Flag task as important | Star icon displayed, can filter by importance |
| Edit Task | Modify any task field after creation | Changes persist, updated_at timestamp updated |
| Inline Task Editing | Click task to edit title in place; expand card for full field editing (desktop). Mobile: inline title + modal for fields | Title editable on click, expand panel shows date/description/assignee/priority, auto-save on blur per field |
| Delete Task | Remove task permanently | Task removed from list and database |
| Filter by List | View tasks belonging to specific list | Only tasks from selected list displayed |
| Overdue Indicator | Visual warning for past-due incomplete tasks | Red/warning styling when due_date < today AND not completed |

#### "Everyone" Assignment Behavior

- Tasks assigned to "Everyone" are shared household tasks
- Any family member can mark the task complete (completes for all)
- Any family member can "grab" the task by reassigning to themselves
- Displayed with group icon to distinguish from individual assignments

#### Data Constraints

- Title: Required, 1-100 characters
- Description: Optional, max 500 characters
- Due Date: Optional, datetime
- List: Required (every task belongs to exactly one list)
- Assigned To: Required (defaults to "Everyone" if not specified)

---

### 5.2 Responsibilities (Recurring Routines)

**Purpose:** Track daily recurring tasks like morning routines, chores, and evening activities.

#### Features

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| Create Responsibility | Define recurring task with title, category, frequency, assignment | Responsibility appears on assigned days |
| Categories | Four time-based categories, selectable as multi-select (a responsibility can belong to multiple categories) | Each category displayed in distinct section |
| Frequency | Select which days responsibility is active | Only visible/completable on selected days |
| Daily View | See all responsibilities for current day, grouped by category | Shows assigned member, completion status; category filter pills narrow to one category |
| Mark Complete | Toggle completion for specific date and category | Completion recorded with date, category, and family member |
| Navigate Days | View previous/next days | Completion history visible for past days |
| Edit Responsibility | Modify responsibility details (including title) | Changes apply to future occurrences; completion history preserved |
| Delete Responsibility | Remove responsibility and all completion history | Cascading delete of completions |
| Icon Support | Optional icon/image for visual identification | Icon displayed in list and daily view |

#### "Everyone" Assignment for Responsibilities

- Responsibility visible for entire family
- Any family member can mark complete (completes once for household)
- Use case: "Send thank you letter" - anyone capable can do it

#### Frequency Logic

- Stored as array of day strings: `["Mon", "Tue", "Wed", "Thu", "Fri"]`
- Responsibility is **visible** only on specified days
- Responsibility is **completable** only on specified days
- Example: "Take out trash" with frequency `["Mon"]` appears only on Mondays

#### Completion Tracking

- One completion record per (responsibility, date, category) tuple
- Unique constraint `UNIQUE(resp_id, date, category)` prevents duplicate completions
- Multi-category responsibilities track completion independently per category (e.g., completing "Brush teeth" in Morning doesn't complete it in Evening)
- Stores which family member marked it complete
- Historical data preserved for reporting

#### Data Constraints

- Title: Required, 1-100 characters
- Description: Optional, max 500 characters
- Categories: Required, non-empty array of enums (MORNING, AFTERNOON, EVENING, CHORE)
- Frequency: Required, non-empty array of day strings
- Assigned To: Required, FK to FamilyMember

---

### 5.3 Meal Planning

**Purpose:** Plan weekly meals for the whole family with flexible per-person assignments, user-defined meal slots, and support for both recipes and simple food items.

#### Core Concept

The system ships with sensible defaults (Breakfast, Lunch, Dinner, Snack) that require zero configuration. Users see a working mealboard on first visit. When they need more flexibility, they customize slot types in settings. Per-person assignment defaults to "everyone" but can be overridden per meal.

#### Features

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| Swimlane Calendar | 7-day horizontal swimlane view (rows = meal slot types, columns = days) | All days visible on desktop, scannable by meal type |
| Flexible Meal Slots | User-defined meal slot types replacing fixed B/L/D. Defaults: Breakfast, Lunch, Dinner, Snack | Configurable in settings; slots have name, color, emoji, sort order, default participants |
| Navigate Weeks | Move to previous/next weeks | Week selector shows date range, data loads for selected week |
| Add Meal (Recipe) | Add a recipe from the catalog to a day and slot | Recipe name, cook time, and favorite badge displayed on card |
| Add Meal (Food Item) | Add a lightweight food item (banana, yogurt) to a day and slot | Emoji + food name displayed on a translucent card |
| Add Meal (Custom) | Enter a free-text meal name for one-off items | Custom name displayed on meal card |
| Per-Person Assignment | Assign meals to specific family members or "everyone" | Participant avatars displayed on card; 3-level fallback: explicit > slot default > everyone |
| Mark Cooked | Toggle "was_cooked" status | Sage-green styling with line-through text and checkmark badge |
| Meal Notes | Add notes to individual meals | Notes displayed in italic below card content |
| Delete Meal | Remove meal from calendar | Meal removed from day; shopping list contributions subtracted |
| Quick Add | Add favorite recipe from right panel | Right panel shows favorites, click adds to selected day + slot |
| Multi-Slot Progress | Track planning completion per active slot type | Progress cards show "X/7" per slot type with colored progress bars |
| Multiple Items Per Slot | Stack multiple meals in one day/slot cell | Cards stack vertically; inline "+" button appears on hover |
| Food Items Management | Browse and manage food items on the Recipes page | "Recipes / Food Items" tab toggle with grid/list view, search, category filters |
| Shopping List Auto-Sync | Recipe ingredients and food items auto-write to linked shopping list | Ingredients aggregated by name + unit group; async via Celery |

#### "Was Cooked" Tracking Purpose

Creates historical log of successfully completed meals:
- First-time recipes create memorable experiences
- Users can distinguish "known" recipes from new experiments
- Enables future analytics (monthly/yearly meal reviews)
- Helps answer "how often do we actually make this?"

#### Swimlane Layout

The planner uses a horizontal swimlane layout where rows represent meal slot types and columns represent days. This enables scanning "all dinners this week" or "all breakfasts" at a glance.

```
              Mon     Tue     Wed     Thu     Fri     Sat     Sun
           +-------+-------+-------+-------+-------+-------+-------+
 Breakfast | card  | card  | card  | card  |   +   | card  |   +   |
           +-------+-------+-------+-------+-------+-------+-------+
 Lunch     |2cards |   +   |2cards |   +   | card  |   +   |   +   |
           +-------+-------+-------+-------+-------+-------+-------+
 Dinner    | card  | card  | card  | card  | card  |   +   | card  |
           +-------+-------+-------+-------+-------+-------+-------+
 Snack     | food  | food  |2foods |   +   | food  |   +   |   +   |
           +-------+-------+-------+-------+-------+-------+-------+
```

Each swimlane band has a gradient background matching its slot type color, with a left rail label showing the slot emoji and name.

#### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| < 768px | Swimlanes stack vertically or switch to day-focused card view |
| 768px - 1199px | Full swimlane grid, no mealboard nav panel (dropdown instead). Sidebar remains |
| >= 1200px | Full swimlane grid + app sidebar (80px) + mealboard nav panel (224px) |

#### Meal Slot Configuration (Settings)

New "Mealboard" card section on the main app Settings page. Two-column layout:
- **Left column:** Slot type list with inline editing (drag to reorder, color picker, emoji, default participants, show/hide toggle)
- **Right column:** Live day preview showing all active slot types as colored bars, updating in real-time
- **Preferences:** Week starts on (Monday/Sunday), Measurement system (Imperial/Metric)

#### Data Constraints

- Date: Required
- Meal Slot Type: Required, FK to MealSlotType
- Item Type: Required, enum (recipe, food_item, custom)
- Recipe ID: Optional, FK to Recipe (when item_type = "recipe")
- Food Item ID: Optional, FK to FoodItem (when item_type = "food_item")
- Custom Meal Name: Optional, max 200 characters (when item_type = "custom")
- Notes: Optional, max 500 characters
- Servings: Optional integer, overrides recipe default (only for recipe items)
- Sort Order: Integer, ordering within a slot on a day
- Must have exactly one of: recipe_id, food_item_id, or custom_meal_name

---

### 5.4 Recipe Management

**Purpose:** Store and organize family recipes for meal planning.

#### Features

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| Create Recipe | Add recipe with name, ingredients, instructions, times | Recipe saved and appears in catalog |
| Ingredients List | Structured ingredient entry (name, qty, unit, category) | Ingredients stored as JSON array |
| Instructions | Multi-line cooking instructions | Full text preserved and displayed |
| Timing | Prep time and cook time in minutes | Displayed on recipe cards |
| Servings | Number of servings recipe makes | Default 4, displayed on recipe |
| Image URL | Link to recipe photo | Image displayed on recipe card |
| Favorite Toggle | Mark/unmark recipe as favorite | Favorites appear in quick-add panel |
| Tags | Categorize with custom tags | Tags displayed, future: filterable |
| Filter Favorites | View only favorite recipes | Filter dropdown in Recipes view |
| Sort Recipes | Sort by name, date added, cook time | Sort options in recipe catalog |
| Edit Recipe | Modify any recipe field | Changes persist |
| Delete Recipe | Remove recipe (meal entries keep reference) | Recipe removed, meal_entry.recipe_id set to NULL, displays "Unnamed meal" |

#### Ingredient Structure

```json
{
  "name": "Chicken breast",
  "quantity": 2,
  "unit": "lb",
  "category": "Protein"
}
```

Categories: Produce, Protein, Dairy, Pantry, Frozen, Bakery, Beverages, Other

#### Data Constraints

- Name: Required, 1-200 characters
- Instructions: Required, min 1 character
- Description: Optional, max 1000 characters
- Prep Time: Optional, >= 0 minutes
- Cook Time: Optional, >= 0 minutes
- Servings: Required, >= 1, default 4
- Ingredients: Optional, JSON array
- Tags: Optional, JSON array of strings

---

### 5.5 Shopping Lists

**Purpose:** Manage grocery shopping with optional recipe integration.

#### Current Implementation (v1.0)

- Links to existing task list (reuses task infrastructure)
- Manual item entry
- Completion toggle per item
- Persistent list selection via localStorage

#### Planned Enhancement (v1.1) — Auto-Sync with Ingredient Aggregation

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| Auto-sync from Meals | When a recipe or food item is added to the mealboard, its ingredients are automatically written to the linked shopping list via Celery background task | Ingredients appear as tasks; `shopping_sync_status` tracks success/failure per meal |
| Ingredient Aggregation | Same ingredient from multiple meals is consolidated by name + unit group | Quantities converted to common base unit, summed, and displayed in user's preferred measurement system (Imperial/Metric) |
| Subtraction on Removal | When a meal is removed from the planner, its ingredient contributions are subtracted from shopping tasks | Tasks at zero quantity are deleted; checked-off (purchased) items are never modified |
| Predefined Unit System | Recipe ingredient units use a predefined dropdown (not freeform text) to enable reliable conversion | Units grouped by Weight (lb, oz, g, kg), Volume (cup, tbsp, tsp, ml, l, fl oz, quart, pint, gallon), Count (piece, clove, slice, bunch, can, package, head, stalk, sprig), and None |
| Concurrency Safety | Aggregation uses a unique constraint on (list_id, aggregation_key_name, aggregation_unit_group) with SELECT FOR UPDATE and constraint-violation retry | No duplicate shopping items even under concurrent Celery workers |
| Shopping Card | Top-bar card on mealboard shows linked list status: no list, item count, or empty | Three states with link modal flow; warning indicator when sync fails |

---

### 5.6 Family Member Management

**Purpose:** Manage household members for task assignment and responsibility tracking.

#### Features

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| System "Everyone" Member | Pre-created, non-deletable member for shared tasks | Always exists, cannot edit/delete |
| Create Member | Add family member with name and optional photo | Member appears in assignment dropdowns |
| Upload Photo | Upload profile photo (JPEG, PNG, GIF, WebP) | Photo displayed as avatar, max 5MB |
| Edit Member | Change name or photo | Changes reflected everywhere member displayed |
| Delete Member | Remove family member | See deletion rules below |

#### Deletion Rules

**Current behavior:** Blocked if member has assigned tasks or responsibilities

**Target behavior (v1.1):**
1. Show confirmation dialog listing assigned items
2. Options:
   - Delete member AND all assigned tasks/responsibilities
   - Keep items but reassign to "Everyone"
   - Cancel

#### Data Constraints

- Name: Required, 1-50 characters, unique
- Color: Optional hex color (auto-assigned from palette on creation)
- Photo URL: Optional, valid image path
- is_system: Boolean, true only for "Everyone"

---

### 5.7 User Authentication (Planned for v1 productionization)

**Purpose:** Secure one shared login per deployment. The app is single-tenant by design — each household runs its own deployment, so there is no cross-household isolation layer or public signup in v1.

> Authoritative source: the 8-milestone productionization plan at
> `.claude/plans/features/prod-contract-freeze/prod-contract-freeze-plan-20260421-182714.md`.
> This section summarizes the product-visible surface; the plan owns the implementation spec.

#### v1 identity model

- Exactly one shared household login per deployment.
- Family members inside the app remain application entities, not auth identities.
- No per-user accounts, no household-join flow, no invite codes, no open public signup.

#### Requirements

| Requirement | Description |
|-------------|-------------|
| Unified Auth Portal | Single `/auth` route showing both Sign in and Create new account. The Create button is hidden after the first account exists, based on `GET /auth/status`. |
| Gated First-Run Registration | `POST /auth/register` creates the one shared login. Gated by `HOUSEHOLD_ACCESS_KEY` (a deployment-specific secret) AND a "no existing account" check. Backend rejects defensively even if the UI still surfaces Create. |
| Login | Email + password. Short-lived JWT access token (15-min TTL, in-memory only) + HttpOnly refresh cookie (`__Host-refresh`, `Secure`, 30-day TTL, rotated on login and refresh). |
| Refresh | `POST /auth/refresh` against the refresh cookie returns a fresh access token and rotates the refresh cookie. 60-second grace window on rotation handles parallel in-flight refreshes. |
| Logout | Revokes the refresh token. Requires the access token in `Authorization: Bearer` (cookie-only logout is rejected as CSRF). |
| Password Recovery | No self-service password reset in v1. Operator rotates the shared password via CLI (`fly ssh console`) — the rotation also invalidates all outstanding refresh tokens AND any still-unexpired access JWTs via a server-side token/session version check. |
| Route Protection | Unauthenticated users on `/`, `/lists`, `/responsibilities`, `/settings`, `/mealboard/*` are redirected to `/auth?return_to=<path>`. Only `/healthz` and `/auth/*` remain public. |

#### What this explicitly does NOT include in v1

- Multi-user accounts within a household (one shared login only).
- Invite codes, household-join flows, public signup.
- Self-service password reset, magic-link login, OAuth/social login.
- Cross-household data isolation (single-tenant-per-deployment replaces this entirely).

#### Deferred beyond v1

- Magic-link login and self-service password reset are v2 candidates.
- Multi-user per household remains intentionally out of roadmap — adding it would require re-architecting the single-tenant assumption, and the current product model (separate deployment per family) is the canonical answer to "how do two households use the app?"

---

### 5.8 Notifications & Reminders (Planned)

**Purpose:** Proactive alerts for tasks, responsibilities, and meals.

#### Notification Types

| Type | Trigger | Content |
|------|---------|---------|
| Task Due | Task due date approaching (1 day before) | "Task X is due tomorrow" |
| Task Overdue | Task past due date | "Task X is overdue" |
| Responsibility Reminder | Morning/time-based | "Time for morning routine!" |
| Meal Reminder | Configurable time before meal | "Dinner tonight: Recipe Name" |
| Incomplete Responsibilities | End of day | "X responsibilities incomplete today" |

#### Delivery Methods

- Push notifications (mobile)
- Browser notifications (desktop)
- Optional email digest

---

### 5.9 iCloud Calendar Integration (Built)

**Purpose:** Two-way sync with iCloud Calendar via CalDAV protocol.

#### Features

| Feature | Description | Status |
|---------|-------------|--------|
| Calendar Sync | Two-way sync: iCloud events appear in app, edits push back to iCloud | Built |
| Connection Flow | 2-step validate/connect with app-specific password, calendar selector | Built |
| Settings UI | Integration cards with status badges, sync button, disconnect | Built |
| Background Sync | Celery workers poll iCloud every 10 minutes for changes | Built |
| Conflict Resolution | Last-write-wins based on timestamps with logging | Built |
| Timezone Config | User-configurable timezone; synced events display in local time, push back as UTC | Built |
| Reminders Sync | Two-way sync with Apple Reminders app | Not Started |
| Meal Calendar | Meal plans appear as calendar events | Not Started |

#### Architecture

- **Authentication**: App-specific passwords (not Apple Sign-In), encrypted at rest with Fernet
- **Protocol**: CalDAV via `caldav` Python library, ICS parsing via `icalendar`
- **Sync**: Celery beat schedule (10-min interval) triggers `sync_all_icloud_integrations` task
- **Push**: Editing/deleting an iCloud event in the app dispatches a Celery push task (30s countdown debounce)
- **Shared Calendar Detection**: During validate, checks if calendar events already exist in DB from another integration

---

### 5.10 Gamification (Planned)

**Purpose:** Motivate kids through points, streaks, and rewards.

#### Features

| Feature | Description |
|---------|-------------|
| Points | Earn points for completing responsibilities |
| Streaks | Track consecutive days of completion |
| Achievements | Unlock badges for milestones |
| Rewards | Parents define redeemable rewards |
| Leaderboard | Family-friendly competition view |

---

### 5.11 Calendar (Dashboard Home)

**Purpose:** Unified calendar view as the primary dashboard, showing household events and tasks in one place. Meal planning remains separate in the Mealboard feature.

#### Overview

The home page (`/` or `/dashboard`) will be a full calendar replacing the current dashboard. This calendar serves as the central hub for family scheduling, pulling in data from:
- Tasks with due dates
- External calendars (iCloud, Google - via sync)
- Future: Responsibility reminders, appointments

**Note:** Meal plans are intentionally excluded from this calendar. Meal planning has its own dedicated weekly calendar in the Mealboard feature (`/mealboard/planner`) and the two should remain distinct.

#### Features

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| Month View | Traditional month grid showing all events | Events grouped by day, color-coded by type |
| Week View | 7-day detailed view with time slots | Tasks and calendar events visible |
| Day View | Single day with full event details | All scheduled items expanded |
| Task Integration | Tasks with due dates appear on calendar | Click task to view/edit in modal |
| Click-to-Edit | Click any item to edit in modal | Tasks open TaskFormModal, events open EventFormModal; checkbox toggles task completion |
| iCloud Sync | Two-way sync with iCloud Calendar | Events from iCloud appear in app and are editable; changes sync back to iCloud |
| Google Calendar Sync | Two-way sync with Google Calendar | Events from Google appear in app and are editable; changes sync back to Google |
| Quick Add | Add event directly from calendar | Click day/time slot to create task or event |
| Event Types | Distinguish between tasks and calendar events | Different colors/icons per type |
| Family Member Filter | Show/hide items by family member | Toggle chips in calendar header |

#### Calendar Event Sources

| Source | Type | Color | Sync Direction |
|--------|------|-------|----------------|
| Tasks (with due date) | Internal | Terracotta | One-way (from Tasks) |
| iCloud Calendar | External | Blue | Two-way |
| Google Calendar | External | Blue | Two-way |
| Manual Events | Internal | Purple | Local only |

#### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| < 640px | Day view default, swipe between days |
| >= 640px | Week view default |
| >= 1024px | Month view default, week/day as options |

#### Data Model Addition

`CalendarEvent` entity for storing manual events and sync metadata (implemented):

```
CalendarEvent
├── id (PK)
├── title (required, 1-200 chars)
├── description (optional, max 500 chars)
├── date (DATE, required, indexed)
├── start_time (VARCHAR, HH:MM format, nullable for all-day)
├── end_time (VARCHAR, HH:MM format, nullable, must be > start_time)
├── all_day (boolean, default false)
├── source (enum: MANUAL, ICLOUD, GOOGLE)
├── external_id (unique, for sync reference)
├── assigned_to (FK → family_members.id, nullable)
├── created_at
├── updated_at
```

**Business rules:**
- MANUAL and ICLOUD events can be edited/deleted; GOOGLE events are read-only (returns 400)
- Editing an ICLOUD event sets sync_status to PENDING_PUSH and dispatches a Celery push task
- Time fields use HH:MM string format with validation
- end_time must be after start_time when both are provided

#### Integration with Existing Features

- **Tasks:** Tasks with due dates automatically appear on calendar
- **Lists:** Tasks synced from specific lists can be filtered
- **Responsibilities:** Future - recurring responsibilities could show on calendar
- **Mealboard:** Intentionally separate - meal planning stays in `/mealboard/planner`

---

### 5.12 CI/CD & Easy Deployment

**Purpose:** Enable continuous integration/deployment and provide a simple way for users to access the app without technical setup.

#### Requirements

| Requirement | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| CI Pipeline | Automated testing on every push/PR | Tests run via GitHub Actions, block merge on failure |
| CD Pipeline | Automated deployment to production | Successful main branch builds deploy automatically |
| Web Hosting | App accessible via public URL | Users visit URL, no setup required |
| Local Option | One-command local deployment | `npx family-hub` or similar starts the app |
| Database | Managed PostgreSQL in production | No manual DB setup for end users |
| File Storage | Cloud storage for uploads | S3-compatible storage for photos/icons |
| SSL | HTTPS for all traffic | TLS certificates auto-provisioned |
| Environment Config | Easy configuration via environment variables | `.env` file or hosting platform config |

#### Hosting Strategy

**Primary: Cloud Hosted (Recommended)**

Users simply visit the web app URL. Options being evaluated:
- **Fly.io** - Container-based, good free tier
- **Railway** - Simple deployment, PostgreSQL included
- **Render** - Similar to Railway
- **Vercel + Supabase** - Frontend on Vercel, backend/DB on Supabase

**Secondary: Self-Hosted**

For users who want to run their own instance:
- Docker Compose (current)
- One-click deploy buttons (Heroku, Railway)
- Future: Homebrew/apt package for local installation

#### CI/CD Pipeline

```
Push/PR → GitHub Actions
    ├── Lint (frontend + backend)
    ├── Test (frontend + backend)
    ├── Build Docker images
    └── (main branch) Deploy to production
```

#### Deployment Checklist for v1

- [ ] CI: Tests run on all PRs
- [ ] CI: Linting enforced
- [ ] CD: Auto-deploy to staging on PR merge
- [ ] CD: Manual promotion to production
- [ ] Hosting: Production environment live
- [ ] Hosting: Managed PostgreSQL
- [ ] Hosting: File storage configured
- [ ] Monitoring: Basic health checks
- [ ] Monitoring: Error tracking (Sentry or equivalent)

---

## 6. Non-Goals & Out of Scope

### Explicitly Out of Scope for v1

| Feature | Reason |
|---------|--------|
| Recipe Finder (AI Discovery) | Deferred to post-v1; AI infrastructure being built as part of URL import feature |
| Social/Sharing Features | Single-household focus for v1 |
| Nutritional Tracking | Adds complexity, not core value prop |
| Budget/Cost Tracking | Out of scope for family task app |
| Inventory Management | Pantry tracking deferred |
| Third-party Recipe Import (Spoonacular, etc.) | v1 uses manual entry or AI URL parsing |
| Native Mobile Apps | Web-first, PWA later |
| Offline Mode | Requires significant architecture changes |
| Multi-language Support | English only for v1 |
| Accessibility Audit | Best-effort for v1, formal audit post-launch |

### What This App Is NOT

- **Not a recipe website** - Stores family recipes, not a discovery platform
- **Not a budgeting tool** - No financial tracking
- **Not a social network** - Private household data only

---

## 7. Technical Requirements

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React 19      │────▶│   FastAPI       │────▶│   PostgreSQL    │
│   Frontend      │     │   Backend       │     │   Database      │
│   (Vite)        │◀────│   (Async)       │◀────│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, React Router v7, Vite, TailwindCSS v4 |
| Backend | FastAPI, SQLAlchemy (async), Pydantic, Celery |
| Database | PostgreSQL, Redis |
| Package Manager | uv (Python), npm (JavaScript) |
| Containerization | Docker, Docker Compose |
| Testing | pytest (backend), vitest (frontend) |

### Performance Requirements

| Metric | Target |
|--------|--------|
| Page Load | < 2 seconds |
| API Response | < 500ms (95th percentile) |
| Database Queries | < 100ms average |
| Concurrent Users | 100+ per household instance |

### Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| Authentication | JWT tokens (planned) |
| Password Storage | bcrypt hashing |
| Data Isolation | Household-scoped queries |
| File Uploads | Type validation, size limits (5MB) |
| CORS | Restricted to known origins |
| SQL Injection | Parameterized queries via SQLAlchemy |
| XSS | React's default escaping |

### Deployment Requirements

| Requirement | Description |
|-------------|-------------|
| Web Accessible | No command-line interaction for end users |
| Multi-tenant | Support multiple households |
| CI/CD | Automated testing and deployment |
| Hosting | Cloud provider (TBD: Fly.io, Railway, etc.) |
| Database | Managed PostgreSQL |
| File Storage | Cloud storage for uploads (S3 or equivalent) |

---

## 8. Data Model

### Entity Relationship Diagram

```
┌──────────────────┐
│  FamilyMember    │
│──────────────────│
│  id              │
│  name (unique)   │
│  is_system       │
│  color           │
│  photo_url       │
│  created_at      │
│  updated_at      │
└────────┬─────────┘
         │
         │ 1:many
         ▼
┌──────────────────┐       ┌──────────────────┐
│      Task        │       │      List        │
│──────────────────│       │──────────────────│
│  id              │       │  id              │
│  title           │◀──────│  name            │
│  description     │ many:1│  color           │
│  due_date        │       │  icon            │
│  completed       │       │  created_at      │
│  important       │       │  updated_at      │
│  assigned_to(FK) │       └──────────────────┘
│  list_id (FK)    │
│  created_at      │
│  updated_at      │
└──────────────────┘

┌──────────────────┐       ┌──────────────────────────┐
│  Responsibility  │       │  ResponsibilityCompletion │
│──────────────────│       │──────────────────────────│
│  id              │1:many │  id                       │
│  title           │──────▶│  responsibility_id (FK)   │
│  description     │       │  family_member_id (FK)    │
│  categories[]    │       │  completion_date          │
│  assigned_to(FK) │       │  category                 │
│  frequency[]     │       │  created_at               │
│  icon_url        │       │  UNIQUE(resp_id, date,    │
│  created_at      │       │        category)           │
│  updated_at      │       └──────────────────────────┘
└──────────────────┘

┌──────────────────────┐       ┌───────────────────────────────┐
│        Item          │       │          MealEntry            │
│──────────────────────│       │───────────────────────────────│
│  id                  │1:many │  id                           │
│  name                │──────▶│  date (indexed)               │
│  item_type (enum)    │       │  meal_slot_type_id (FK)       │──▶ MealSlotType
│  icon_emoji (null)   │       │  item_id (FK, nullable)       │
│  icon_url (null)     │       │  custom_meal_name (nullable)  │
│  tags (JSONB)        │       │  custom_meal_emoji (nullable) │
│  is_favorite         │       │  servings (nullable)          │
│  deleted_at (null)   │       │  was_cooked                   │
│  created_at          │       │  soft_hidden_at (null)        │
│  updated_at          │       │  notes                        │
└──────┬───────────────┘       │  sort_order                   │
       │ 1:1                   │  shopping_sync_status         │
       ├──▶ RecipeDetail       │  created_at                   │
       │     (item_id PK,      │  updated_at                   │
       │      description,     └─────────┬─────────────────────┘
       │      ingredients,               │ many:many
       │      instructions,              ▼
       │      prep_time,       ┌───────────────────────────┐
       │      cook_time,       │  meal_entry_participants  │
       │      servings,        │───────────────────────────│
       │      image_url)       │  meal_entry_id (FK)       │
       │                       │  family_member_id (FK)    │──▶ FamilyMember
       └──▶ FoodItemDetail     │  PK(meal_entry_id,        │
            (item_id PK,       │     family_member_id)     │
             category,         └───────────────────────────┘
             shopping_qty,
             shopping_unit)

CHECK CONSTRAINTS:
  items.(icon_emoji, icon_url)  — XOR: not both set
  meal_entries.(item_id, custom_meal_name) — at least one must be set
  Item.deleted_at cascades to MealEntry.soft_hidden_at via application logic
  ON DELETE CASCADE: items → recipe_details, items → food_item_details, items → meal_entries

SCHEMA HISTORY:
  - Pre-2026-04: separate `recipes` and `food_items` tables, `meal_entries.recipe_id`/`food_item_id` with item_type discriminator
  - 2026-04-13 (mealboard polish batch Chunk 0): unified into `items` + detail subtype tables, `meal_entries.item_id`

┌──────────────────────────────┐
│       MealSlotType           │
│──────────────────────────────│
│  id                          │
│  name                        │
│  sort_order                  │
│  color (hex)                 │
│  icon (emoji, nullable)      │
│  is_default                  │
│  is_active                   │
│  default_participants (JSON) │
│  created_at                  │
│  updated_at                  │
└──────────────────────────────┘

(Recipe + FoodItem entities above are now merged into Item + RecipeDetail + FoodItemDetail
 as shown in the Item/MealEntry diagram — see 2026-04-13 schema history note.)

┌──────────────────┐
│  CalendarEvent   │
│──────────────────│
│  id              │
│  title           │
│  description     │
│  date            │
│  start_time      │
│  end_time        │
│  all_day         │
│  source (enum)   │
│  external_id     │
│  assigned_to(FK) │──────► FamilyMember
│  created_at      │
│  updated_at      │
└──────────────────┘
```

### Enums

```python
class ResponsibilityCategory:
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    CHORE = "CHORE"

class MealItemType:
    RECIPE = "recipe"
    FOOD_ITEM = "food_item"
    CUSTOM = "custom"

class ShoppingSyncStatus:
    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"

class CalendarEventSource:
    MANUAL = "MANUAL"
    ICLOUD = "ICLOUD"
    GOOGLE = "GOOGLE"
```

---

## 9. User Flows

### 9.1 Parent: Morning Check-in

```
1. Open app (lands on Dashboard)
2. View today's date and upcoming tasks
3. Navigate to Responsibilities
4. See daily view with family member columns
5. Check which kids completed morning routine
6. Note any incomplete items to follow up
```

### 9.2 Child: Complete Morning Routine

```
1. Open app (or parent opens for young child)
2. Navigate to Responsibilities
3. See today's responsibilities in categories
4. Tap checkbox for "Brush Teeth"
5. Tap checkbox for "Get Dressed"
6. See visual feedback (checkmarks, green styling)
7. Parent can verify completion
```

### 9.3 Parent: Weekly Meal Planning

```
1. Navigate to Mealboard > Meal Planner
2. See current week's swimlane grid (rows: Breakfast, Lunch, Dinner, Snack; columns: Mon-Sun)
3. Click empty cell in the Dinner row for Monday
4. Quick-entry popover appears with unified search across recipes and food items
5. Type "chicken" — see grouped results (RECIPES: Honey Garlic Chicken, FOOD ITEMS: Chicken Breast)
6. Select "Honey Garlic Chicken" recipe — participant avatars default to "Everyone"
7. Override participants: toggle to assign only to parents (kids having something else)
8. Repeat for other days and slot types
9. Click "+" in Monday Lunch row, type "PB&J" — select "+ Add PB&J as custom meal"
10. Add "banana" to Monday Snack — food item card appears with emoji
11. Review week — progress tracker shows "5/7 Dinners", "3/7 Lunches", etc.
12. Recipe ingredients auto-sync to linked shopping list (aggregated by name + unit)
```

### 9.4 Parent: Add New Recipe

```
1. Navigate to Mealboard > Recipes
2. Click "Add Recipe" button
3. Enter recipe details:
   - Name: "Honey Garlic Chicken"
   - Ingredients: Add each with qty/unit
   - Instructions: Paste or type steps
   - Prep/Cook time
   - Mark as favorite
4. Save recipe
5. Recipe appears in catalog and favorites
```

### 9.5 Family: Shared Task Completion

```
1. Task "Clean garage" assigned to "Everyone"
2. Dad sees task in list
3. Dad completes task, marks complete
4. Task shows as completed for household
5. Alternatively: Dad could "grab" task (reassign to self) first
```

---

## 10. Edge Cases & Business Rules

### Task Rules

| Rule | Behavior |
|------|----------|
| Task without due date | No overdue warning, sorts to bottom |
| Task reassignment | Allowed at any time, history not tracked |
| Deleting list with tasks | All tasks in list deleted (cascade) |
| Empty task title | Rejected (validation error) |

### Responsibility Rules

| Rule | Behavior |
|------|----------|
| Completion on wrong day | Blocked - can only complete on frequency days |
| Multiple completions same day per category | Blocked - unique constraint per (resp, date, category) |
| Edit frequency | Affects future visibility only |
| Delete responsibility | All completion history deleted |

### Recipe & Meal Rules

| Rule | Behavior |
|------|----------|
| Delete recipe with meal entries | Cascade soft-delete: recipe + meal entries are soft-hidden (recipes.deleted_at / meal_entries.soft_hidden_at set). User sees a merged undo toast ("Recipe + N meals deleted. Undo") with a 15-second client window; Celery beat hard-deletes after 24h. Undo before the server window expires restores both. (Changed 2026-04-13 CEO review of mealboard polish batch — replaces prior "set recipe_id to NULL" behavior.) |
| Delete food item with meal entries | Cascade soft-delete: food item + meal entries are soft-hidden (food_items.deleted_at / meal_entries.soft_hidden_at set). Same 15s undo toast + 24h Celery beat hard-delete as recipes. (Changed 2026-04-13 CEO review — replaces prior "set food_item_id to NULL" behavior.) |
| Delete meal card directly (user-initiated) | Soft-delete with `undo_token` sidecar. In-place 5-second undo card replaces the meal card in its grid slot (dashed border, shrinking countdown bar). Click restores and re-syncs ingredients to the shopping list. Timeout = permanent soft-delete; hourly sweeper hard-deletes entries >15s old. 6.5s server-side window accommodates network slack. Distinct from the cascade-delete undo toast (which fires from item/recipe delete). Concurrent deletes from two family members: second DELETE returns 404 Not Found. (Added 2026-04-17 CEO review of `mealboard-meal-card-polish`.) |
| Meal without recipe, food item, or custom name | Rejected - must have exactly one based on item_type |
| Multiple meals same day/slot | Allowed - cards stack vertically within the cell, ordered by sort_order |
| Mark cooked | Can toggle on/off; card styling changes to sage-green with line-through |
| Delete meal slot type with entries | Soft-delete (set is_active = false); hard-delete only if no entries reference it |
| Per-person participant resolution | 3-level fallback: explicit entry participants > slot type defaults > everyone |
| Shopping list sync on meal add | Ingredients auto-written to linked shopping list via Celery; aggregated by name + unit group |
| Shopping list sync on meal remove | Contributions subtracted; checked-off items never modified; zero-quantity tasks deleted |

### Family Member Rules

| Rule | Behavior |
|------|----------|
| Duplicate name | Rejected - unique constraint |
| Delete "Everyone" | Blocked - system member |
| Edit "Everyone" | Blocked - system member |
| Delete member with tasks | Currently blocked (v1.1: dialog with options) |

### Data Validation

| Field | Validation |
|-------|------------|
| All titles/names | Non-empty, max length enforced |
| Dates | Valid date format required |
| Foreign keys | Must reference existing records |
| File uploads | Type (jpg/png/gif/webp), size (5MB max) |
| URLs | Valid URL format |

---

## 11. Future Roadmap

### v1.0 (Productionization — active)

- [ ] First-party email + password auth for one shared household login (see plan at `.claude/plans/features/prod-contract-freeze/prod-contract-freeze-plan-20260421-182714.md`, milestones M3-M5)
- [ ] Production deployment on Vercel + Fly.io + Fly managed Postgres + Upstash Redis + Cloudflare R2 (same plan, milestones M2, M6-M8; M6 is residual cleanup and may be skipped)

### v1.1 (Post-Launch Polish)

- [ ] Family member deletion dialog with task reassignment
- [x] Shopping list auto-sync from meal entries with ingredient aggregation
- [x] Automatic ingredient subtraction when meals removed from planner
- [ ] Basic analytics dashboard (completions over time)

### v1.2 (Integration)

- [x] iCloud Calendar sync (two-way via CalDAV + Celery)
- [ ] iCloud Reminders sync
- [ ] Google Calendar sync
- [ ] Push notifications

> **Not on the roadmap:** multi-household SaaS within a single shared deployment. The app is single-tenant-per-deployment by design. A second household that wants to use the app gets its own independent deployment (separate Fly app, DB, Redis, R2 bucket, Vercel project). Multi-tenant shared hosting would require re-architecting the data model and auth boundary and is explicitly deferred indefinitely.

### v1.3 (Engagement)

- [ ] Gamification system (points, streaks, badges)
- [ ] Kid-friendly view mode (larger buttons, simpler UI)
- [ ] Weekly summary email

### v2.0 (AI Features)

- [ ] Recipe Finder (AI-powered discovery)
- [ ] Add recipe from URL (AI parsing)
- [ ] Meal suggestions based on history
- [ ] Smart shopping list optimization

### Future Considerations

- Native mobile apps (iOS/Android)
- Offline mode with sync
- Voice assistant integration
- Multi-language support
- Accessibility certification

---

## Appendix A: API Endpoints

### Tasks
- `GET /tasks` - List tasks (filter by list_id)
- `GET /tasks/{id}` - Get task
- `POST /tasks` - Create task
- `PATCH /tasks/{id}` - Update task
- `DELETE /tasks/{id}` - Delete task

### Lists
- `GET /lists` - List all lists
- `GET /lists/{id}` - Get list
- `POST /lists` - Create list
- `PATCH /lists/{id}` - Update list
- `DELETE /lists/{id}` - Delete list

### Family Members
- `GET /family-members` - List all members
- `GET /family-members/{id}` - Get member
- `POST /family-members` - Create member
- `PATCH /family-members/{id}` - Update member
- `DELETE /family-members/{id}` - Delete member

### Responsibilities
- `GET /responsibilities` - List responsibilities (filter by assigned_to)
- `GET /responsibilities/completions` - Get completions for date
- `GET /responsibilities/{id}` - Get responsibility
- `POST /responsibilities` - Create responsibility
- `PATCH /responsibilities/{id}` - Update responsibility
- `DELETE /responsibilities/{id}` - Delete responsibility
- `POST /responsibilities/{id}/complete` - Toggle completion

### Recipes
- `GET /recipes` - List recipes (filter by favorites_only)
- `GET /recipes/{id}` - Get recipe
- `POST /recipes` - Create recipe
- `PATCH /recipes/{id}` - Update recipe
- `DELETE /recipes/{id}` - Delete recipe

### Meal Slot Types
- `GET /meal-slot-types` - List all slot types (active + inactive)
- `POST /meal-slot-types` - Create custom slot type
- `PATCH /meal-slot-types/{id}` - Update slot type (rename, recolor, reorder, toggle active)
- `DELETE /meal-slot-types/{id}` - Soft-delete if entries exist, hard-delete if none
- `POST /meal-slot-types/reset` - Restore default slot types (B/L/D/Snack)

### Food Items
- `GET /food-items` - List food items (supports ?search=, ?category= filters)
- `POST /food-items` - Create food item
- `PATCH /food-items/{id}` - Update food item
- `DELETE /food-items/{id}` - Delete food item (ON DELETE SET NULL on meal entries)

### Meal Entries
- `GET /meal-entries` - List meal entries (requires start_date, end_date; optional family_member_id filter)
- `POST /meal-entries` - Create meal entry (triggers shopping list sync via Celery)
- `PATCH /meal-entries/{id}` - Update meal entry
- `DELETE /meal-entries/{id}` - Delete meal entry (subtracts shopping list contributions)

### Calendar Events
- `GET /calendar-events` - List events (requires start_date, end_date; optional assigned_to)
- `GET /calendar-events/{id}` - Get single event
- `POST /calendar-events` - Create event (MANUAL source default)
- `PATCH /calendar-events/{id}` - Update event (MANUAL + ICLOUD; dispatches push for ICLOUD)
- `DELETE /calendar-events/{id}` - Delete event (MANUAL + ICLOUD; dispatches delete-push for ICLOUD)

### Calendar Integrations
- `POST /integrations/icloud/validate` - Validate credentials, return calendar list
- `POST /integrations/icloud/connect` - Connect iCloud (encrypt, store, initial sync)
- `GET /integrations/` - List all integrations (optional family_member_id filter)
- `GET /integrations/{id}` - Get single integration
- `POST /integrations/{id}/sync` - Force sync (dispatches Celery task)
- `DELETE /integrations/{id}` - Disconnect and cascade-delete synced events

### App Settings
- `GET /app-settings/` - Get current settings (timezone, week_start_day, measurement_system)
- `PATCH /app-settings/` - Update settings (timezone validated as IANA name; week_start_day: "monday"/"sunday"; measurement_system: "imperial"/"metric")
- `GET /app-settings/timezones` - List all valid IANA timezone names

### Uploads
- `POST /upload/family-photo` - Upload family member photo
- `POST /upload/responsibility-icon` - Upload responsibility icon
- `GET /upload/stock-icons` - List stock icons

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| Household | A single family unit using the app together |
| Family Member | A person in the household (includes "Everyone") |
| Task | A one-time to-do item assigned to a family member |
| List | A category/folder for organizing tasks |
| Responsibility | A recurring task with a schedule (frequency) |
| Completion | A record that a responsibility was done on a specific date |
| Recipe | A stored meal recipe with ingredients and instructions |
| Meal Entry | A scheduled meal for a specific date and meal slot type, linked to a recipe, food item, or custom name |
| Meal Slot Type | A user-configurable meal category (e.g., Breakfast, Lunch, Dinner, Snack) with color, emoji, and default participants |
| Food Item | A lightweight non-recipe food (e.g., banana, yogurt) with optional emoji and category |
| Calendar Event | A scheduled event on the calendar (manual or synced from external calendar) |
| "Everyone" | System family member representing the whole household |

---

*Document Version History*

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 Draft | Feb 2026 | William Doucet | Initial PRD |
| 1.1 | Apr 2026 | William Doucet | Mealboard overhaul: flexible meal slot types, per-person assignments, food items, swimlane UI, shopping list auto-sync with ingredient aggregation |
