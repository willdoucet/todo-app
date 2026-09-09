# Application Flow Documentation

> Every page, navigation path, and user flow documented in plain English.

---

## Table of Contents

1. [Screen Inventory](#1-screen-inventory)
2. [Navigation Structure](#2-navigation-structure)
3. [User Flows](#3-user-flows)
4. [Error Handling](#4-error-handling)

---

## 1. Screen Inventory

### Routes & Pages

| Route | Page Component | Purpose |
|-------|----------------|---------|
| `/` | `CalendarDashboard` | Home screen with unified calendar view |
| `/lists` | `ListsPage` | Task management with list sidebar |
| `/responsibilities` | `ResponsibilitiesPage` | Daily routines and recurring tasks |
| `/settings` | `FamilyMembersPage` | Manage household members, timezone, and calendar integrations |
| `/mealboard/planner` | `MealPlannerView` | Weekly meal calendar |
| `/mealboard/recipes` | `RecipesView` | Unified Item catalog — tabbed: Recipes + Food Items |
| `/mealboard/finder` | `RecipeFinderView` | Coming soon placeholder |

> **Note:** `/mealboard/shopping` was removed during the item-model refactor. The shopping list integration now lives at `/lists` (the target list is configured via the ShoppingCard settings button on the Mealboard planner page).

### Page Hierarchy

```
App (Layout)
├── Sidebar (persistent, left side)
│   ├── Calendar link (/) - Home/Dashboard
│   ├── Lists link (/lists)
│   ├── Responsibilities link (/responsibilities)
│   ├── Mealboard link (/mealboard/planner)
│   └── Settings link (/settings)
│
└── Main Content Area
    └── [Current Page Component]
```

---

## 2. Navigation Structure

### Global Navigation (Sidebar)

**Trigger:** Always visible on screens >= 640px (sm:), icon-only on mobile

**Elements:**
1. **Calendar** - Calendar icon → `/` (Home/Dashboard)
2. **Lists** - List icon → `/lists`
3. **Responsibilities** - Clipboard icon → `/responsibilities`
4. **Mealboard** - Utensils/plate icon → `/mealboard/planner`
5. **Settings** - Cog icon → `/settings`
6. **Dark Mode Toggle** - Moon/Sun icon (bottom of sidebar)

**Behavior:**
- Active route highlighted with background color
- Icons always visible, labels visible on hover/expanded
- Mobile: Bottom navigation bar or hamburger menu

### Mealboard Sub-Navigation

**Location:** Inside MealboardPage, left panel (>=1200px) or dropdown (<1200px)

**Elements:**
1. **Meal Planner** → `/mealboard/planner` (default)
2. **Recipes** → `/mealboard/recipes` (segmented control inside: Recipes tab + Food Items tab — both backed by the unified `/items` API)
3. **Recipe Finder** → `/mealboard/finder` (disabled/coming soon)

---

## 3. User Flows

### 3.1 Task Management Flow

#### Creating a Task

**Trigger:** Click "Add a task" row at bottom of section (or unsectioned area)

**Steps (Desktop — Inline):**
1. User is on `/lists` page
2. User selects a list from the sidebar
3. User clicks "Add a task" row at the bottom of the desired section
4. Row transforms into inline text input with + icon
5. User types task title
6. User optionally clicks expand button to set fields (date, description, assignee, priority)
7. User presses Enter or clicks Save

**Steps (Mobile):**
1. Same as desktop steps 1-5
2. For additional fields: user taps expand button which opens modal form
3. User fills fields in modal and saves

**On Success:**
- Task appears in list immediately
- Inline input clears, reverts to "Add a task" row
- Task saved to database

**On Error:**
- Inline input stays active with error toast
- Input retains text for retry

#### Completing a Task

**Trigger:** Click checkbox next to task

**Steps:**
1. User sees task in list
2. User clicks circular checkbox
3. Checkbox animates to filled state
4. Task text gets strikethrough styling

**On Success:**
- Task marked complete in database
- Task moves to "Completed" section (if grouped)
- Completion timestamp recorded

**On Error:**
- Checkbox reverts to previous state
- Error toast displayed

#### Editing a Task

**Trigger (Desktop):** Click anywhere on task text (not checkbox, not action area)

**Steps (Desktop — Inline):**
1. Task title becomes editable input with terracotta underline
2. Save/Cancel buttons appear in action area
3. User edits title, presses Enter or clicks Save (or blur auto-saves)
4. For other fields: click expand button → inset panel slides down with date, description, assignee (pills), priority (pills)
5. Each expanded field auto-saves on blur (debounced 500ms)

**Steps (Mobile):**
1. Click task text → inline title edit (same as desktop)
2. For other fields: tap expand button → existing modal opens with all fields

**On Success:**
- Changes persist immediately (auto-save per field)
- No modal on desktop

**On Error:**
- Input stays active, inline error toast, retry or cancel

#### Deleting a Task

**Trigger:** Click always-visible delete button on task card, OR clear task title and press Enter

**Steps:**
1. User clicks delete button (always visible on task card)
2. Task removed from list
*OR:*
1. User is editing task title inline
2. User clears all text — Save button changes to red "Delete"
3. User presses Enter → task deleted

**On Success:**
- Task deleted from database
- Task fades out of list

**On Error:**
- Task reappears in list
- Error message displayed

---

### 3.2 Responsibilities Flow

#### Viewing Daily Schedule

**Trigger:** Navigate to `/responsibilities`

**Steps:**
1. User clicks Responsibilities in sidebar
2. Page loads with "Daily View" tab active
3. Current date displayed at top
4. Responsibilities grouped by category:
   - Morning (sunrise emoji)
   - Afternoon (sun emoji)
   - Evening (moon emoji)
   - Chores (broom emoji)
5. Each responsibility shows:
   - Title
   - Assigned member avatar
   - Completion checkbox
6. Category filter pills above the list:
   - "All" (default — shows all categories)
   - Morning, Afternoon, Evening, Chores
   - Click a pill to show only that category; click again to return to All
   - Multi-category responsibilities appear only under the selected category when filtered

**Navigation:**
- Left arrow: Previous day
- Right arrow: Next day
- Date picker: Jump to specific date

#### Marking Responsibility Complete

**Trigger:** Click checkbox for responsibility

**Steps:**
1. User sees responsibility in daily view
2. User clicks checkbox
3. Checkbox fills with checkmark
4. Card styling changes (green tint)

**Note:** Completion is tracked per-category. If a responsibility belongs to multiple categories (e.g., Morning and Evening), completing it in one category does not affect the other.

**On Success:**
- Completion record created in database for specific category
- Visual feedback immediate

**On Error:**
- Checkbox reverts
- Error displayed

**Decision Point:** If responsibility already completed for the day in that category
- Clicking again removes completion (toggle behavior)
- Confirmation not required

#### Creating a Responsibility

**Trigger:** Click "Add Responsibility" button in Edit view

**Steps:**
1. User switches to "Edit Responsibilities" tab
2. User clicks "Add Responsibility" button
3. Modal opens with form:
   - Title (required)
   - Description (optional)
   - Categories multi-select buttons (Morning/Afternoon/Evening/Chore) — select one or more
   - Assigned member dropdown
   - Frequency checkboxes (Mon-Sun)
   - Icon selector (optional)
4. User fills form
5. User clicks Save

**On Success:**
- Modal closes
- Responsibility appears in list under category
- Available for completion on selected days

**On Error:**
- Modal stays open
- Error message shown in modal
- Form data preserved

#### Editing a Responsibility

**Trigger:** Click edit button on a responsibility card in "Edit Responsibilities" tab

**Steps:**
1. User switches to "Edit Responsibilities" tab
2. User clicks edit icon on a responsibility card
3. Modal opens with form pre-filled with existing values
4. All fields are editable, including title
5. User modifies desired fields
6. User clicks "Save Changes"

**On Success:**
- Modal closes
- Updated responsibility reflected in list
- Existing completion history is preserved

**On Error:**
- Modal stays open
- Error message shown
- Form data preserved

---

### 3.3 Meal Planning Flow

#### Viewing Week Calendar

**Trigger:** Navigate to `/mealboard/planner`

**Steps:**
1. User clicks Mealboard in sidebar
2. Meal Planner view loads (default)
3. Current week displayed (Mon-Sun)
4. Each day shows:
   - Day name and date
   - Three meal slots (Breakfast, Lunch, Dinner)
   - Existing meals as cards
   - "+" button for empty slots

**Navigation:**
- Left arrow: Previous week
- Right arrow: Next week
- Week range displayed in header

#### Adding a Meal

**Trigger:** Click "+" button on any swimlane cell (day × meal slot) in the SwimlaneGrid (desktop) or MobileDayView (<768px)

**Steps:**
1. User clicks "+" on the target day / meal slot
2. `AddMealPopover` opens pre-populated with the date and meal slot
3. Popover header shows the slot icon/name and formatted date
4. **Unified search input** — types any string, the popover shows two sections:
   - **Recipes** — filtered items where `item_type === 'recipe'`
   - **Food Items** — filtered items where `item_type === 'food_item'`
   - Each section caps at 8 results
5. Filter chips above the results: All / Recipes / Food Items
6. User either:
   - Clicks an item from the list → POST `/meal-entries` with `{item_id}`
   - Types a name with no matches and clicks "Add '{typed}' as custom meal" → POST with `{custom_meal_name}`
7. Participants default to the slot's `default_participants` (or all family members if empty); user can toggle individual participants
8. Optional notes field (collapsible `<details>`)
9. Meal entry is created, `AddMealPopover` closes, the new `MealCard` appears in the swimlane

**On Success:** Modal closes, meal card renders with `entry.item.name` (or `custom_meal_name`) + participants + cook time metadata from `item.recipe_detail`. **On Error:** Modal stays open, inline error shown, form preserved.

#### Marking a Meal as Cooked

**Trigger:** Hover the `MealCard`; click the green ✓ button in the revealed action row.

**Steps:**
1. `PATCH /meal-entries/{id}` with `{was_cooked: true}`
2. Card re-renders with strikethrough name + sage-green "✓ Cooked" badge

**Toggle:** Clicking again flips `was_cooked` back to `false`.

#### Deleting a Meal Entry

Meal entries are **hard-deleted** (not soft-deleted — only Items have the soft-delete/undo flow). Clicking the red ✕ button on a MealCard fires `DELETE /meal-entries/{id}` and the card disappears immediately. A separate Celery task (`sync_shopping_list_remove`) cleans up the aggregated shopping task contribution for that meal entry.

---

### 3.4 Item Management Flow (recipes + food items, unified)

The `/mealboard/recipes` page is a single `RecipesView` with a segmented-control tab switch between **Recipes** and **Food Items**. Both tabs share the same underlying `useItems({type})` hook, `ItemCard`, `ItemRow`, `ItemFormModal`, and `ItemDetailDrawer` components — the only difference is the `type` parameter.

#### Creating a Recipe or Food Item

**Trigger:** Click the Add button on the active tab (labeled "Add Recipe" or "Add Item")

**Steps (recipe):**
1. User is on the Recipes tab
2. User clicks "Add Recipe"
3. `ItemFormModal` opens in the full recipe form (max-w-2xl):
   - Name (required)
   - Description
   - Ingredients (dynamic list): name, quantity, unit, category
   - Instructions (textarea)
   - Prep time / cook time / servings
   - Image upload (recipe hero)
   - Tags (comma-separated)
   - Favorite toggle
4. User fills form, clicks "Add Recipe"
5. `POST /items` fires with nested `recipe_detail` payload

**Steps (food item):**
1. User is on the Food Items tab
2. User clicks "Add Item"
3. `ItemFormModal` opens in compact food-item form (max-w-md):
   - Name (required)
   - **Icon section (mockup emoji-icon-xor-option-d):** 64×64 icon square + 32px-tall tab switcher `[Emoji | Custom]`. In Emoji mode, clicking the square opens the emoji picker and typing the name auto-suggests an emoji. In Custom mode, the square shows an upload affordance and a URL input appears below the tabs.
   - Category dropdown (Fruit / Vegetable / Protein / Dairy / Grain / No category)
   - Favorite toggle
4. User fills form, clicks "Create"
5. `POST /items` fires with nested `food_item_detail` payload

**On Success:** Modal closes, new item appears in the grid. **On Error:** Modal stays open with inline error; duplicate-name conflict returns 409 with an explicit message.

#### Editing an Item

**Trigger (recipe):** Click a recipe card → `ItemDetailDrawer` slides in from the right → click "Edit recipe" button.
**Trigger (food item):** Click a food item pill — opens `ItemFormModal` directly (no drawer step; plan §1099-1100).

Both flows reuse the same `ItemFormModal` component; the form pre-populates from `initialItem`. The `type` prop is locked at open time — there is no user-facing way to convert a recipe into a food item (plan §0.4F / Design Review IA issue 1A).

#### Deleting an Item (soft-delete + undo)

**Trigger:** Click the trash icon on a recipe card (hover-reveal) or an item row.

**Steps:**
1. `ConfirmDialog` asks "Are you sure you want to delete 'X'? You'll have 15 seconds to undo."
2. User confirms
3. Frontend optimistically removes the item from the grid
4. `DELETE /items/{id}` fires → backend sets `items.deleted_at = now()` and cascades `meal_entries.soft_hidden_at`
5. Backend response `{id, undo_token, expires_at}` triggers the `UndoToast` singleton at bottom-center (mockup undo-toast-option-a): dark pill, item icon, "Recipe deleted" / "Food item deleted" label, 15s countdown ring, Undo button, dismiss ✕
6. **Undo path:** user clicks Undo within the window → `POST /items/{id}/undo` with the stored token → item is restored, toast hides. Toast shows 410 errors (expired/invalid/consumed token) as an "Undo window expired" state.
7. **Expiry path:** countdown reaches zero → toast auto-hides → item stays soft-deleted server-side; it will be hard-deleted by the `hard_delete_expired_soft_deletes` Celery beat task (Chunk 6 / Expansion B).

#### Filtering & Searching Items

**Trigger:** Toolbar on each tab — search input, favorites filter pills, tag pills (recipes only), category pills (food items only), sort dropdown, grid/list view toggle.

- **Recipes tab sort options:** Name A-Z / Name Z-A / Recently Added / Cook Time (reads from `item.recipe_detail.cook_time_minutes`)
- **Food items tab filter options:** All / Fruit / Vegetable / Protein / Dairy / Grain (reads from `item.food_item_detail.category`)
- **Favorites filter:** All / Favorites / Non-Favorites — works on both tabs via `item.is_favorite`
- **Tag filter:** recipes only, pulls distinct `item.tags` across the current tab's items

State is local to the view (no context, no persistence beyond `localStorage` for the grid/list view preference on the recipes tab).

---

### 3.5 Family Member Management Flow

#### Adding a Family Member

**Trigger:** Click "Add Member" on Settings page

**Steps:**
1. User navigates to `/settings`
2. User clicks "Add Member" button
3. Form appears:
   - Name (required)
   - Photo upload (optional)
4. User enters name
5. User optionally uploads photo
6. User clicks "Save"

**On Success:**
- Member appears in list
- Available in all assignment dropdowns

**On Error:**
- If duplicate name: "Name already exists" error
- Form preserved for correction

#### Uploading Member Photo

**Trigger:** Click photo area or "Upload Photo" button

**Steps:**
1. User clicks upload area
2. File picker opens
3. User selects image file
4. Preview shown in form
5. On form save, photo uploaded to server

**Validation:**
- File types: .jpg, .jpeg, .png, .gif, .webp
- Max size: 5MB
- Checked client-side before upload

**On Error:**
- "File too large" or "Invalid file type" message
- File not uploaded

#### Deleting a Family Member

**Trigger:** Click delete button on member card

**Current Behavior:**
1. User clicks delete
2. If member has tasks/responsibilities:
   - Error: "Cannot delete member with assigned items"
3. If no assignments:
   - Member deleted
   - Removed from list

**Note:** "Everyone" member cannot be deleted (button hidden/disabled)

---

### 3.6 Shopping List Flow (post-refactor)

The dedicated `/mealboard/shopping` sub-page was removed during the item-model refactor. Shopping is now expressed as a **target task list** that meal entries sync ingredients into.

#### Linking a Shopping List

**Trigger:** Click the ShoppingCard settings gear on the Mealboard planner page (`/mealboard/planner`).

**Steps:**
1. User opens the ShoppingLinkModal
2. User picks a task list from the dropdown of all non-synced `lists`
3. The selection writes `AppSettings.mealboard_shopping_list_id` via `PATCH /app-settings`
4. On save, existing meal entries trigger a backfill sync into the newly-linked list

**Behavior:**
- The linked list persists in `AppSettings` (server-side, single-source-of-truth across devices)
- Can be changed at any time via the same ShoppingCard settings button

#### Adding Shopping Items

Shopping items are no longer added directly from the Mealboard UI — they appear automatically when meal entries get their ingredients aggregated and synced to the linked task list by `app.services.shopping_sync.sync_meal_to_shopping_list`. Users add manual shopping items directly via the Lists page (`/lists`).

**On Success:**
- Task created in backend
- Item shows in list

#### Completing Shopping Items

**Trigger:** Click checkbox

**Same as task completion flow**

---

### 3.7 Calendar Dashboard Flow

#### Viewing Calendar (Home)

**Trigger:** Navigate to `/` (home page)

**Steps:**
1. User opens app or clicks Calendar in sidebar
2. Calendar loads in month view (desktop) or day view (mobile)
3. Events displayed color-coded by type:
   - Terracotta: Tasks with due dates
   - Blue: External calendar events (iCloud/Google)
   - Purple: Manual events
4. User can see at-a-glance what's happening each day
5. Meal plans are NOT shown here (see Mealboard for meal planning)

**View Options:**
- Month view: Full month grid with event dots/previews
- Week view: 7-day detailed view
- Day view: Single day with full details

#### Navigating Calendar

**Trigger:** Click arrows or swipe

**Steps:**
1. Click left/right arrows to move month/week/day
2. On mobile: swipe left/right between days
3. Click "Today" button to return to current date
4. Click specific date to jump to day view

#### Adding Event from Calendar

**Trigger:** Click empty day or time slot

**Steps:**
1. User clicks on a day (month view) or time slot (week/day view)
2. Quick-add popover appears with options:
   - Add Task (creates task with due date set)
   - Add Event (creates calendar event)
3. User selects type and fills minimal form
4. Event appears on calendar immediately

**On Success:**
- Event saved to appropriate backend (tasks or calendar-events)
- Calendar updates to show new event

#### Editing Tasks/Events from Calendar

**Trigger:** Click on existing task or event in any view

**Steps (Month view - desktop):**
1. User clicks day cell → popover shows items
2. User clicks an item → popover closes, edit modal opens
3. User modifies fields and clicks "Save Changes"
4. Calendar refreshes with updated data

**Steps (Week/Day view - desktop):**
1. User clicks event block in TimeGrid → EventFormModal opens in edit mode
2. User clicks task bar in AllDaySection → TaskFormModal opens in edit mode
3. Event click uses `stopPropagation` to prevent quick-add popup

**Steps (Mobile - any view):**
1. User taps day → day list shows tasks and events
2. User taps item → edit modal opens
3. User modifies and saves

**Task completion toggle:**
- Checkbox icon on tasks is a separate click target
- Clicking checkbox toggles `completed` via `PATCH /tasks/{id}`
- Does NOT open edit modal (`stopPropagation`)
- Available in: CalendarItem (MobileDayList, MonthDayPopover) and AllDaySection bars

#### Configuring Timezone

**Trigger:** Navigate to Settings page

**Steps:**
1. User navigates to Settings (`/settings`)
2. Scrolls to "Timezone" card (between Family Members and Calendar Integrations)
3. Searches for timezone in searchable input field
4. Selects timezone from filtered list (e.g. "America/Los_Angeles")
5. Clicks "Save Timezone"
6. Success message: "Timezone saved. Re-sync calendars to update event times."

**Effect:** After saving, the next iCloud sync converts event times from UTC to the selected timezone. Manual events are unaffected.

#### Syncing with iCloud (Built)

**Trigger:** First-time setup from Settings page

**Connection flow:**
1. User navigates to Settings (`/settings`)
2. Scrolls to "Calendar Integrations" section
3. Clicks "Connect iCloud Calendar"
4. Form appears: select Family Member, enter iCloud email, enter app-specific password
5. Clicks "Validate" — backend connects via CalDAV, returns available calendars with event counts and shared-calendar warnings
6. User selects which calendars to sync via CalendarSelector checkboxes
7. Clicks "Connect" — backend encrypts password, creates integration, dispatches initial sync task
8. Card shows "Syncing..." status with polling (3s interval)
9. When sync completes, card shows "Active" with last synced time

**Ongoing sync:**
- Celery beat runs `sync_all_icloud_integrations` every 10 minutes
- Manual "Sync Now" button dispatches immediate sync via `POST /integrations/{id}/sync`
- iCloud events appear on calendar, color-coded by family member

**Editing iCloud events:**
- Click iCloud event → EventFormModal opens with "Synced from iCloud" badge
- Edit fields → click Save → confirmation banner: "This will also update the event in iCloud"
- On confirm: PATCH saves locally with sync_status=PENDING_PUSH, Celery pushes to iCloud (30s countdown)
- Delete flow similar: confirmation banner warns about iCloud deletion

**Disconnect:**
- Click "Disconnect" on integration card
- Integration and all its synced events are cascade-deleted

#### Syncing with Google Calendar (Planned)

**Status:** Not yet implemented. Will use OAuth 2.0 flow instead of app-specific passwords.

---

## 4. Error Handling

### API Error States

| Error Type | User Message | Recovery Action |
|------------|--------------|-----------------|
| Network Error | "Unable to connect. Check your internet." | Retry button |
| 400 Bad Request | "Invalid data. Please check your input." | Highlight fields |
| 401 Unauthorized | "Session expired. Please log in again." | Redirect to login |
| 404 Not Found | "Item not found. It may have been deleted." | Refresh list |
| 500 Server Error | "Something went wrong. Please try again." | Retry button |

### Form Validation

| Field | Validation | Error Message |
|-------|------------|---------------|
| Task Title | Required, 1-100 chars | "Title is required" / "Title too long" |
| Due Date | Valid date or empty | "Invalid date format" |
| Family Member Name | Required, unique, 1-50 chars | "Name required" / "Name already exists" |
| Item Name | Required, 1-200 chars, unique within item_type | "An item named 'X' of type 'recipe' already exists" (409) |
| Item icon XOR | Cannot set both `icon_emoji` and `icon_url` | 422 "icon_emoji and icon_url cannot both be set (XOR)" |
| ItemCreate recipe | `recipe_detail` required when `item_type='recipe'` | 422 "recipe_detail is required when item_type='recipe'" |
| ItemCreate food_item | `food_item_detail` required when `item_type='food_item'` | 422 "food_item_detail is required when item_type='food_item'" |
| MealEntry | Must have either `item_id` or `custom_meal_name` | 422 "Either item_id or custom_meal_name must be provided" |
| File Upload | Type + size validation | "Invalid file type" / "File too large (max 5MB)" |

### Optimistic Updates

**Pattern Used:**
1. Update UI immediately
2. Send API request
3. On success: Keep UI state
4. On error: Revert UI, show error

**Applied To:**
- Task completion toggle
- Responsibility completion toggle
- Meal "cooked" toggle
- Task deletion

---

## 5. Decision Points Summary

| Scenario | Decision | Outcome A | Outcome B |
|----------|----------|-----------|-----------|
| Delete member with tasks | Block or reassign? | Currently: Block | Future: Dialog with options |
| Complete responsibility twice | Allow toggle? | Yes - removes completion | |
| Add meal without recipe | Allow custom name? | Yes - custom_meal_name field | |
| Delete recipe with meal plans | Cascade or preserve? | Preserve meal, null recipe_id | |
| Upload invalid file | Reject silently or message? | Show error message | |
