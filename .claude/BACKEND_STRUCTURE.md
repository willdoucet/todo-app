# Backend Structure

> Database schema, API contracts, and code organization for the FastAPI backend.

---

## Table of Contents

1. [Database Schema](#1-database-schema)
2. [API Endpoints](#2-api-endpoints)
3. [Code Organization](#3-code-organization)
4. [Data Validation](#4-data-validation)
5. [Error Handling](#5-error-handling)

---

## 1. Database Schema

### Entity Overview

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| **FamilyMember** | Household members | `name`, `is_system` (for "Everyone"), `color` (calendar display) |
| **List** | Task categories | `name`, `color`, `icon`, `external_id` (CalDAV URL), FK→CalendarIntegration (SET NULL) |
| **Task** | Todo items assigned to members | `title`, `due_date`, `completed`, `priority` (0-9), `parent_id` (self-ref), `sort_order`, `completed_at`, sync metadata, FK→Section, FK→List, FK→FamilyMember, FK→CalendarIntegration |
| **Section** | Grouping within lists | `name`, `sort_order`, `external_id`, FK→List (CASCADE) |
| **Responsibility** | Recurring tasks | `title`, `categories[]` (MORNING/AFTERNOON/EVENING/CHORE), `frequency[]`, FK→FamilyMember |
| **ResponsibilityCompletion** | Daily completion tracking | `completion_date`, `category`, FK→Responsibility, FK→FamilyMember |
| **Item** | Unified parent for recipes and food items (post item-model refactor) | `name`, `item_type` ('recipe'\|'food_item'), `icon_emoji` (XOR), `icon_url` (XOR), `tags` JSONB, `is_favorite`, `deleted_at` (soft-delete) |
| **RecipeDetail** | Recipe-only fields keyed to Item | `item_id` PK FK CASCADE, `description`, `ingredients` JSONB, `instructions`, `prep_time_minutes`, `cook_time_minutes`, `servings`, `image_url` |
| **FoodItemDetail** | Food-item-only fields keyed to Item | `item_id` PK FK CASCADE, `category`, `shopping_quantity` (Numeric), `shopping_unit` |
| **MealEntry** | Scheduled meals — references Item via `item_id` or stands alone via `custom_meal_name` | `date`, FK→MealSlotType, `item_id` FK→Item RESTRICT (nullable), `custom_meal_name` (nullable), `was_cooked`, `soft_hidden_at` (cascade from Item soft-delete), participants (M:N via `meal_entry_participants`). CHECK: `item_id IS NOT NULL OR custom_meal_name IS NOT NULL` |
| **CalendarEvent** | Manual + synced calendar events | `date`, `start_time`/`end_time` (HH:MM), `source` (MANUAL/ICLOUD/GOOGLE), `sync_status`, FK→Calendar |
| **Calendar** | Individual iCloud calendars/reminder lists | `calendar_url`, `name`, `color`, `is_todo`, FK→CalendarIntegration (cascade) |
| **CalendarIntegration** | External calendar connections | `provider`, `email`, `encrypted_password`, `status`, `reminders_status`, `sync_range_*_days` |
| **AppSettings** | Singleton app config | `timezone` (IANA name, default UTC) |

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
│  FamilyMember   │       │         Task            │       │         List            │
├─────────────────┤       ├─────────────────────────┤       ├─────────────────────────┤
│ id (PK)         │◄──────│ assigned_to (FK)        │       │ id (PK)                 │
│ name            │       │ list_id (FK)            │──────►│ name                    │
│ is_system       │       │ id (PK)                 │       │ color                   │
│ color           │       │ title                   │       │ icon                    │
│ photo_url       │       │ description             │       │ external_id             │
│ created_at      │       │ due_date                │       │ calendar_integration_id │───► CalendarIntegration
│ updated_at      │       │ completed               │       │ created_at              │
        │                 │ priority (0-9)          │       │ updated_at              │
        │                 │ parent_id (FK→Task)     │─┐     └───────────┬─────────────┘
        │                 │ section_id (FK)         │ │                 │ 1:many (cascade)
        │                 │ sort_order              │ │                 ▼
        │                 │ completed_at            │ │     ┌─────────────────────────┐
        │                 │ external_id             │ │     │       Section           │
        │                 │ etag                    │ │     ├─────────────────────────┤
        │                 │ last_modified_remote    │ │     │ id (PK)                 │
        │                 │ sync_status             │ │     │ name                    │
        │                 │ calendar_integration_id │ │     │ list_id (FK)            │───► List (CASCADE)
        │                 │ created_at              │ │     │ sort_order              │
        │                 │ updated_at              │ │     │ external_id             │
        │                 └─────────────────────────┘ │     │ created_at              │
        │                   │ self-ref (subtasks)      │     │ updated_at              │
        │                   └─────────────────────────┘     └─────────────────────────┘
        │                 UNIQUE(external_id, calendar_integration_id)
        │
        │                 ┌─────────────────────────┐
        │                 │    Responsibility       │
        ├────────────────►├─────────────────────────┤
        │                 │ id (PK)                 │
        │                 │ title                   │
        │                 │ categories (ARRAY)      │
        │                 │ assigned_to (FK)        │
        │                 │ frequency (ARRAY)       │
        │                 │ icon_url                │
        │                 │ description             │
        │                 │ created_at              │
        │                 │ updated_at              │
        │                 └───────────┬─────────────┘
        │                             │
        │                             ▼
        │                 ┌─────────────────────────┐
        └────────────────►│ ResponsibilityCompletion│
                          ├─────────────────────────┤
                          │ id (PK)                 │
                          │ responsibility_id (FK)  │
                          │ family_member_id (FK)   │
                          │ completion_date         │
                          │ category                │
                          │ created_at              │
                          └─────────────────────────┘
                          UNIQUE(responsibility_id, completion_date, category)

┌─────────────────────┐       ┌──────────────────────┐       ┌─────────────────────┐
│        Item         │       │    MealEntry         │       │   MealSlotType      │
├─────────────────────┤       ├──────────────────────┤       ├─────────────────────┤
│ id (PK)             │◄──────│ item_id (FK)         │       │ id (PK)             │
│ name                │       │ id (PK)              │──────►│ name                │◄─ RESTRICT
│ item_type (CHECK)   │       │ date                 │       │ color, icon         │
│ icon_emoji (XOR)    │       │ meal_slot_type_id    │       │ default_participants│
│ icon_url (XOR)      │       │ custom_meal_name     │       └─────────────────────┘
│ tags (JSONB)        │       │ was_cooked           │
│ is_favorite         │       │ soft_hidden_at       │
│ deleted_at          │       │ notes                │
│ created_at          │       │ shopping_sync_status │
│ updated_at          │       │ synced_to_list_id    │
└──┬──────────────┬───┘       └──────────────────────┘
   │1:1 CASCADE   │1:1 CASCADE   CHECK(item_id OR custom_meal_name)
   ▼              ▼              FK item_id = RESTRICT (soft-delete is the supported path)
┌─────────────────┐   ┌──────────────────────┐
│  RecipeDetail   │   │   FoodItemDetail     │
├─────────────────┤   ├──────────────────────┤
│ item_id (PK+FK) │   │ item_id (PK+FK)      │
│ description     │   │ category             │
│ ingredients GIN │   │ shopping_quantity    │
│ instructions    │   │ shopping_unit        │
│ prep/cook time  │   └──────────────────────┘
│ servings        │
│ image_url       │
└─────────────────┘

┌─────────────────────────┐
│  CalendarIntegration    │
├─────────────────────────┤
│ id (PK)                 │
│ family_member_id (FK)   │───► FamilyMember
│ provider (VARCHAR)      │
│ email (VARCHAR)         │
│ encrypted_password      │
│ status (ENUM)           │
│ reminders_status (ENUM) │  ◄── nullable, ACTIVE/SYNCING/ERROR
│ reminders_last_error    │
│ reminders_last_sync_at  │
│ selected_calendars (JSON│  ◄── legacy, migrating to Calendar table
│ sync_range_past_days    │
│ sync_range_future_days  │
│ last_sync_at            │
│ last_error              │
│ created_at              │
│ updated_at              │
└───────────┬─────────────┘
            │ 1:many (cascade)
            ▼
┌─────────────────────────┐
│       Calendar          │
├─────────────────────────┤
│ id (PK)                 │
│ calendar_integration_id │───► CalendarIntegration (CASCADE)
│ calendar_url (VARCHAR)  │
│ name (VARCHAR)          │
│ color (VARCHAR, nullable│
│ is_todo (BOOLEAN)       │  ◄── True=reminder list, False=event calendar
│ created_at              │
│ updated_at              │
└───────────┬─────────────┘
UNIQUE(calendar_integration_id, calendar_url)
            │ 1:many
            ▼
┌─────────────────────────┐
│     CalendarEvent       │
├─────────────────────────┤
│ id (PK)                 │
│ title                   │
│ description             │
│ date (DATE, indexed)    │
│ start_time (HH:MM)     │
│ end_time (HH:MM)       │
│ all_day                 │
│ source (ENUM)           │
│ external_id             │
│ etag                    │
│ last_modified_remote    │
│ sync_status (VARCHAR)   │
│ calendar_integration_id │───► CalendarIntegration (SET NULL)
│ calendar_id (FK)        │───► Calendar (SET NULL)
│ assigned_to (FK)        │───► FamilyMember
│ timezone (VARCHAR)      │
│ created_at              │
│ updated_at              │
└─────────────────────────┘
UNIQUE(external_id, calendar_integration_id)

┌─────────────────────────┐
│      AppSettings        │
├─────────────────────────┤
│ id (PK)                 │
│ timezone (VARCHAR)      │  default "UTC", IANA timezone name
│ created_at              │
│ updated_at              │
└─────────────────────────┘
Singleton — only one row exists (seeded by migration)
```

### Table Definitions

#### family_members

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `name` | VARCHAR | UNIQUE, NOT NULL, INDEX | Display name |
| `is_system` | BOOLEAN | NOT NULL, DEFAULT false | True for "Everyone" member |
| `color` | VARCHAR(7) | NULLABLE | Hex color for calendar display (auto-assigned from palette) |
| `photo_url` | VARCHAR | NULLABLE | Path to uploaded photo |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

#### lists

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `name` | VARCHAR | NOT NULL, INDEX | List name |
| `color` | VARCHAR(7) | NULLABLE | Hex color code |
| `icon` | VARCHAR | NULLABLE | Icon identifier |
| `external_id` | VARCHAR | NULLABLE | CalDAV calendar URL for synced reminder lists |
| `calendar_integration_id` | INTEGER | FK → calendar_integrations.id (SET NULL), NULLABLE | Owning integration for synced lists |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Relationships:** `tasks` (1:many), `sections` (1:many, cascade delete), `integration` (many:1 → CalendarIntegration)

**Business rules:**
- Synced lists (`calendar_integration_id IS NOT NULL`) cannot be deleted from the Lists UI — user must disconnect Reminders in Settings first
- `is_synced` is derived in the Pydantic response schema from `calendar_integration_id IS NOT NULL`

#### tasks

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `title` | VARCHAR | NOT NULL, INDEX | Task title |
| `description` | VARCHAR | NULLABLE | Optional details |
| `due_date` | TIMESTAMP | NULLABLE | Due date/time |
| `completed` | BOOLEAN | DEFAULT false | Completion status |
| `priority` | INTEGER | NOT NULL, DEFAULT 0 | 0=none, 1=high, 5=medium, 9=low (matches Apple Reminders) |
| `assigned_to` | INTEGER | FK → family_members.id, NOT NULL | Assigned member |
| `list_id` | INTEGER | FK → lists.id, NOT NULL | Parent list |
| `parent_id` | INTEGER | FK → tasks.id (SET NULL), NULLABLE | Self-referential subtask parent |
| `section_id` | INTEGER | FK → sections.id (SET NULL), NULLABLE, INDEX | Section within the list |
| `sort_order` | INTEGER | NOT NULL, DEFAULT 0 | Sort position within section/list |
| `completed_at` | TIMESTAMP | NULLABLE | When task was completed (auto-set) |
| `external_id` | VARCHAR | NULLABLE | UID from iCloud Reminders (for sync) |
| `etag` | VARCHAR | NULLABLE | CalDAV ETag for change detection |
| `last_modified_remote` | TIMESTAMP | NULLABLE | Remote last-modified timestamp |
| `sync_status` | VARCHAR | NULLABLE | SYNCED, PENDING_PUSH |
| `calendar_integration_id` | INTEGER | FK → calendar_integrations.id (SET NULL), NULLABLE | Owning integration for synced tasks |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Unique constraint:** `(external_id, calendar_integration_id)` — same external task can exist across different integrations

**Relationships:** `family_member`, `list`, `parent` (self-ref), `children` (1:many → Task), `section`, `integration` (many:1 → CalendarIntegration)

**Business rules:**
- `parent_id` must reference a task in the same `list_id` (cross-list rejected with 400)
- Cycle detection: ancestor chain walked before save (max 50 iterations), 400 on cycle
- `section_id` must reference a section in the same `list_id` (400 if mismatched)
- Setting `completed=True` auto-sets `completed_at`; setting `completed=False` clears it
- Creating a task in a synced list (`list.calendar_integration_id IS NOT NULL`) inherits sync metadata and dispatches push to iCloud
- Editing/deleting a synced task (`external_id IS NOT NULL`) sets `sync_status=PENDING_PUSH` and dispatches Celery push task
- `is_synced` is derived in the Pydantic response from `calendar_integration_id IS NOT NULL`
- When fetching by `list_id`, only root-level tasks (`parent_id IS NULL`) are returned; children are nested via eager-load (2 levels deep)

#### sections

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `name` | VARCHAR | NOT NULL | Section name |
| `list_id` | INTEGER | FK → lists.id (CASCADE), NOT NULL | Parent list |
| `sort_order` | INTEGER | DEFAULT 0 | Sort position within list |
| `external_id` | VARCHAR | NULLABLE | External ID (reserved for future iCloud section mapping) |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Relationships:** `list` (many:1 → List), `tasks` (1:many → Task)

**Business rules:**
- Deleting a section sets `section_id=NULL` on its tasks (tasks become unsectioned, not deleted)
- Deleting a list cascade-deletes all its sections

#### responsibilities

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `title` | VARCHAR | NOT NULL, INDEX | Responsibility name |
| `description` | VARCHAR | NULLABLE | Optional details |
| `categories` | VARCHAR[] | NOT NULL | Array of category strings (MORNING, AFTERNOON, EVENING, CHORE) |
| `assigned_to` | INTEGER | FK → family_members.id, NOT NULL | Assigned member |
| `frequency` | VARCHAR[] | NOT NULL | Array of weekday codes |
| `icon_url` | VARCHAR | NULLABLE | Custom icon path |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Frequency values:** `["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]`

#### responsibility_completions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `responsibility_id` | INTEGER | FK → responsibilities.id, NOT NULL | Parent responsibility |
| `family_member_id` | INTEGER | FK → family_members.id, NOT NULL | Completing member |
| `completion_date` | DATE | NOT NULL | Date completed |
| `category` | VARCHAR | NOT NULL | Which category was completed (MORNING, AFTERNOON, EVENING, CHORE) |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |

**Unique constraint:** `(responsibility_id, completion_date, category)` - one completion per day per category

#### items

Unified parent table replacing the separate `recipes` and `food_items` tables (item-model refactor, Alembic rev `a1b2c3d4e5f1` → `a1b2c3d4e5f3`).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `name` | TEXT | NOT NULL | Item name |
| `item_type` | TEXT | NOT NULL, CHECK IN ('recipe', 'food_item') | Discriminator |
| `icon_emoji` | TEXT | NULLABLE | Emoji (XOR with icon_url) |
| `icon_url` | TEXT | NULLABLE | Image URL (XOR with icon_emoji) |
| `tags` | JSONB | NOT NULL, DEFAULT '[]' | Array of tag strings |
| `is_favorite` | BOOLEAN | NOT NULL, DEFAULT false | Favorite flag |
| `deleted_at` | TIMESTAMP | NULLABLE | Soft-delete timestamp (Expansion B) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT now() + ON UPDATE now() | Last update timestamp |

**Check constraints:**
- `items_item_type_check`: `item_type IN ('recipe', 'food_item')`
- `items_icon_xor_check`: `NOT (icon_emoji IS NOT NULL AND icon_url IS NOT NULL)`

**Indexes:**
- `items_item_type_idx` on `item_type`
- `items_is_favorite_idx` partial on `is_favorite` WHERE `is_favorite = true`
- `items_deleted_at_idx` partial on `deleted_at` WHERE `deleted_at IS NOT NULL`
- `items_name_type_uniq` partial UNIQUE on `(name, item_type)` WHERE `deleted_at IS NULL` — allows a recipe and a food item to share a name (e.g., "Chicken") but not two recipes

**Trigger:** `bump_item_updated_at` fires on `recipe_details` / `food_item_details` INSERT/UPDATE/DELETE and bumps the parent `items.updated_at` so cache invalidation keyed on parent timestamps stays correct.

#### recipe_details

Recipe-only fields keyed by `item_id`. Joined from `items` only when recipe-specific data is needed.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `item_id` | INTEGER | PRIMARY KEY, FK → items.id ON DELETE CASCADE | Parent item |
| `description` | TEXT | NULLABLE | Short description |
| `ingredients` | JSONB | NOT NULL, DEFAULT '[]' | Array of ingredient objects |
| `instructions` | TEXT | NULLABLE | Cooking instructions |
| `prep_time_minutes` | INTEGER | NULLABLE | Prep time in minutes |
| `cook_time_minutes` | INTEGER | NULLABLE | Cook time in minutes |
| `servings` | INTEGER | NULLABLE | Number of servings |
| `image_url` | TEXT | NULLABLE | Recipe hero image URL |
| `source_url` | TEXT | NULLABLE | Origin URL for recipes imported via `POST /items/import-from-url`. NULL for manually-created recipes. Drives the "View Original" link in the recipe detail view and enables future duplicate detection. Added by Alembic revision `e5a6b7c8d9e0` (2026-04-16). |

**Index:** `recipe_details_ingredients_gin` GIN index on `ingredients` for ingredient-substring queries.

**Ingredients JSON structure:**
```json
[
  {"name": "Chicken breast", "quantity": 2, "unit": "lb", "category": "Meat"},
  {"name": "Olive oil", "quantity": 2, "unit": "tbsp", "category": "Pantry"}
]
```

#### food_item_details

Food-item-only fields keyed by `item_id`.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `item_id` | INTEGER | PRIMARY KEY, FK → items.id ON DELETE CASCADE | Parent item |
| `category` | TEXT | NOT NULL, DEFAULT 'Other' | fruit, vegetable, protein, dairy, grain, Other |
| `shopping_quantity` | NUMERIC | NOT NULL, DEFAULT 1.0 | Default quantity for shopping sync |
| `shopping_unit` | TEXT | NOT NULL, DEFAULT 'each' | Default unit for shopping sync |

#### meal_entries

The mealboard uses `meal_entries`, not a separate `meal_plans` table (that name was renamed during an earlier overhaul and fully removed during the item-model refactor).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `date` | DATE | NOT NULL, INDEX | Meal date |
| `meal_slot_type_id` | INTEGER | FK → meal_slot_types.id ON DELETE RESTRICT, NOT NULL | Breakfast/Lunch/Dinner/etc. |
| `item_id` | INTEGER | FK → items.id ON DELETE RESTRICT, NULLABLE | Linked Item (recipe or food item) |
| `custom_meal_name` | VARCHAR | NULLABLE | Ad-hoc meal name when no Item is chosen |
| `servings` | INTEGER | NULLABLE | Per-entry servings override |
| `was_cooked` | BOOLEAN | DEFAULT false | Cooked status |
| `notes` | VARCHAR | NULLABLE | Additional notes |
| `sort_order` | INTEGER | NOT NULL, DEFAULT 0 | Sort order within a slot |
| `shopping_sync_status` | VARCHAR | NULLABLE | synced / pending / failed / skipped |
| `synced_to_list_id` | INTEGER | FK → lists.id ON DELETE SET NULL, NULLABLE | Target shopping list |
| `soft_hidden_at` | TIMESTAMP | NULLABLE | Soft-hide marker — TWO writers: parent-item cascade (undo_token IS NULL) or user-initiated 5s undo window (undo_token IS NOT NULL). See `crud_meal_entries.py` module docstring for the state-machine diagram. |
| `undo_token` | VARCHAR(64) | NULLABLE, partial index WHERE NOT NULL | Per-entry undo token issued by `DELETE /meal-entries/{id}`. Non-NULL only during the 5-second undo window; the `POST /meal-entries/{id}/undo` endpoint performs an atomic CAS on `(id, undo_token, soft_hidden_at > now()-6.5s)` to flip the row back to live. |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Check constraint:** `meal_entries_item_or_custom_check`: `item_id IS NOT NULL OR custom_meal_name IS NOT NULL` — every meal entry must either reference an Item or carry an ad-hoc `custom_meal_name`.

**FK RESTRICT rationale (Eng Review #3 Issue 3):** The `meal_entries.item_id` FK is `ON DELETE RESTRICT` so a raw `DELETE FROM items` fails loudly instead of silently wiping meal history. The supported deletion path is the soft-delete flow: `items.deleted_at` is set and the matching `meal_entries.soft_hidden_at` are set in the same transaction. The hourly `hard_delete_expired_soft_deletes` Celery task (Chunk 6) runs a cascade-in-code transaction with an assertion gate that fails if any active meal_entry still references an expired item.

#### calendar_integrations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `family_member_id` | INTEGER | FK → family_members.id, NOT NULL | Owning family member |
| `provider` | VARCHAR | NOT NULL | Integration provider (`icloud`, `google`) |
| `email` | VARCHAR | NOT NULL | Account email |
| `encrypted_password` | VARCHAR | NOT NULL | Fernet-encrypted app-specific password |
| `status` | ENUM | NOT NULL, DEFAULT ACTIVE | ACTIVE, SYNCING, ERROR (calendar sync status) |
| `last_sync_at` | TIMESTAMP | NULLABLE | Last successful calendar sync time |
| `last_error` | VARCHAR | NULLABLE | Last calendar sync error message |
| `reminders_status` | ENUM | NULLABLE | ACTIVE, SYNCING, ERROR (null = reminders not connected) |
| `reminders_last_sync_at` | TIMESTAMP | NULLABLE | Last successful reminders sync time |
| `reminders_last_error` | VARCHAR | NULLABLE | Last reminders sync error message |
| `selected_calendars` | JSON | NULLABLE | Legacy — array of calendar URLs (migrating to Calendar table) |
| `sync_range_past_days` | INTEGER | DEFAULT 30 | How many days back to sync |
| `sync_range_future_days` | INTEGER | DEFAULT 90 | How many days forward to sync |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Status enum values:**
- `ACTIVE` - Integration connected and working
- `SYNCING` - Sync currently in progress
- `ERROR` - Last sync failed (see `last_error` / `reminders_last_error`)
- `DISCONNECTED` - Integration disconnected

**Composite status:** Calendar and Reminders have separate status fields. `reminders_status` is null when reminders are not connected. The Settings UI shows separate badges per feature.

**Relationships:** `calendars` (1:many, cascade delete), `calendar_events` (1:many), `synced_tasks` (1:many → Task), `synced_lists` (1:many → List), `family_member`

#### calendars

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `calendar_integration_id` | INTEGER | FK → calendar_integrations.id (CASCADE), NOT NULL | Parent integration |
| `calendar_url` | VARCHAR | NOT NULL | CalDAV calendar URL |
| `name` | VARCHAR | NOT NULL | Display name (populated from iCloud on sync) |
| `color` | VARCHAR | NULLABLE | Hex color from iCloud |
| `is_todo` | BOOLEAN | DEFAULT false | True for reminder lists, False for event calendars |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Unique constraint:** `(calendar_integration_id, calendar_url)` — one entry per calendar per integration

**Relationships:** `integration` (many:1 → CalendarIntegration), `events` (1:many → CalendarEvent)

**Purpose:** Replaces the `selected_calendars` JSON column on CalendarIntegration with a proper relational table. Each row represents one iCloud calendar or reminder list that the user selected for syncing. `is_todo=True` rows are reminder lists (VTODOs), `is_todo=False` are event calendars (VEVENTs). Names and colors are updated from iCloud metadata on each sync pull.

#### calendar_events

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO, INDEX | Unique identifier |
| `title` | VARCHAR | NOT NULL | Event title (1-200 chars) |
| `description` | VARCHAR | NULLABLE | Event details (max 500 chars) |
| `date` | DATE | NOT NULL, INDEX | Event date |
| `start_time` | VARCHAR | NULLABLE | Start time in HH:MM format (null for all-day) |
| `end_time` | VARCHAR | NULLABLE | End time in HH:MM format (must be > start_time) |
| `all_day` | BOOLEAN | DEFAULT false | All-day event flag |
| `source` | ENUM | NOT NULL, DEFAULT MANUAL | MANUAL, ICLOUD, GOOGLE |
| `external_id` | VARCHAR | NULLABLE | ID from external calendar (for sync) |
| `etag` | VARCHAR | NULLABLE | CalDAV ETag for change detection |
| `last_modified_remote` | TIMESTAMP | NULLABLE | Remote last-modified timestamp |
| `sync_status` | VARCHAR | NULLABLE | SYNCED, PENDING_PUSH |
| `timezone` | VARCHAR | NULLABLE | IANA timezone name (null for all-day events) |
| `calendar_integration_id` | INTEGER | FK → calendar_integrations.id (SET NULL), NULLABLE | Owning integration |
| `calendar_id` | INTEGER | FK → calendars.id (SET NULL), NULLABLE | Specific iCloud calendar |
| `assigned_to` | INTEGER | FK → family_members.id, NULLABLE | Assigned family member |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Unique constraint:** `(external_id, calendar_integration_id)` — same external event can exist across different integrations

**Source enum values:**
- `MANUAL` - Created directly in Family Hub (editable/deletable)
- `ICLOUD` - Synced from iCloud Calendar (editable, changes push back to iCloud)
- `GOOGLE` - Synced from Google Calendar (read-only in app, planned)

**Business rules:**
- MANUAL and ICLOUD events can be edited/deleted; GOOGLE events return 400
- Editing an ICLOUD event sets `sync_status` to PENDING_PUSH and dispatches a Celery push task
- Deleting an ICLOUD event dispatches a Celery delete-push task before removing from DB
- Setting `calendar_id` on create/edit triggers source transitions:
  - `calendar_id` null → set: MANUAL → ICLOUD (push to iCloud)
  - `calendar_id` set → null: ICLOUD → MANUAL (delete from iCloud, keep locally)
  - `calendar_id` changed (same integration): move event between iCloud calendars
  - `calendar_id` changed (different integration): returns 400
- Time fields validated as HH:MM format; end_time must be after start_time
- Response includes nested `family_member` and `calendar` objects

#### app_settings

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO | Unique identifier |
| `timezone` | VARCHAR | NOT NULL, DEFAULT "UTC" | IANA timezone name (e.g. "America/Los_Angeles") |
| `created_at` | TIMESTAMP | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NULLABLE | Last update timestamp |

**Singleton pattern:** Only one row exists, seeded by migration. CRUD module auto-creates with defaults if missing.

**Purpose:** Stores the user-configured timezone for converting synced calendar event times. Pull direction: iCloud UTC → local time for display. Push direction: local time → UTC for iCloud. Manual events are unaffected (already entered as local time).

---

## 2. API Endpoints

### Base URL

```
Development: http://localhost:8000
```

### Family Members

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/family-members` | List all members |
| GET | `/family-members/{id}` | Get single member |
| POST | `/family-members` | Create member |
| PATCH | `/family-members/{id}` | Update member |
| DELETE | `/family-members/{id}` | Delete member (fails if has tasks) |

### Lists

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lists` | List all lists |
| GET | `/lists/{id}` | Get single list |
| POST | `/lists` | Create list |
| PATCH | `/lists/{id}` | Update list |
| DELETE | `/lists/{id}` | Delete list (400 if synced — must disconnect Reminders first) |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks` | List all tasks (with `list_id`, returns root-level only; children nested via eager-load) |
| GET | `/tasks?list_id={id}` | Filter by list (root-level tasks with 2-level nested children) |
| GET | `/tasks/{id}` | Get single task (with nested children) |
| POST | `/tasks` | Create task (auto-inherits sync metadata if list is synced; pushes to iCloud) |
| PATCH | `/tasks/{id}` | Update task (synced tasks dispatch push to iCloud) |
| DELETE | `/tasks/{id}` | Delete task (synced tasks dispatch delete-push to iCloud) |

### Responsibilities

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/responsibilities` | List all responsibilities |
| GET | `/responsibilities/{id}` | Get single responsibility |
| POST | `/responsibilities` | Create responsibility |
| PATCH | `/responsibilities/{id}` | Update responsibility |
| DELETE | `/responsibilities/{id}` | Delete responsibility |
| POST | `/responsibilities/{id}/complete` | Toggle completion for date and category |

**Complete request body:**
```json
{"completion_date": "2024-01-15"}
```
**Query parameter:** `?category=MORNING` (required — specifies which category to toggle)

### Items (recipes + food items, unified)

Canonical API surface for the mealboard catalog. Replaces the legacy `/recipes` and `/food-items` routes (deleted during the item-model refactor).

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/items` | List items (query params: `type=recipe\|food_item`, `favorites_only=true`, `search=...`) |
| GET | `/items/{id}` | Get single item with detail eager-loaded |
| POST | `/items` | Create item (body: nested `ItemCreate` with either `recipe_detail` or `food_item_detail`) |
| PATCH | `/items/{id}` | Partial update of item + its detail row (body: `ItemUpdate`) |
| DELETE | `/items/{id}` | Soft-delete item (sets `deleted_at`, cascade-hides meal_entries). Returns `{id, undo_token, expires_at}`. |
| POST | `/items/{id}/undo` | Restore a soft-deleted item within the 15-second window. Body: `{undo_token}`. Returns 410 on invalid/expired/consumed tokens. |
| POST | `/items/suggest-icon` | AI-backed emoji suggestion. Body: `{name}`. Returns `{emoji, fallback_used}`. Falls back gracefully (`fallback_used=true`, `emoji=null`) if Anthropic is unavailable so the client uses its local `suggestEmoji()` helper. |
| POST | `/items/import-from-url` | Queue an async recipe extraction from a URL. SSRF pre-gate rejects private/reserved/loopback IPs. Body: `{url}`. Returns `{task_id}` (202-ish semantics, 200 in practice). |
| GET | `/items/import-status/{task_id}` | Poll extraction status. Returns `{status: 'pending'\|'progress'\|'complete'\|'failed'\|'not_found', step?, recipe?, error_code?}`. `error_code` values live in `app/constants/import_errors.py`. |

**Payload shape:**
```json
POST /items
{
  "name": "Honey Garlic Chicken",
  "item_type": "recipe",
  "icon_emoji": null,
  "icon_url": null,
  "tags": ["dinner"],
  "is_favorite": false,
  "recipe_detail": {
    "description": "...",
    "ingredients": [{"name": "chicken", "quantity": 2, "unit": "lb", "category": "Protein"}],
    "instructions": "...",
    "prep_time_minutes": 10,
    "cook_time_minutes": 25,
    "servings": 4,
    "image_url": null
  }
}
```

Food item payloads swap `recipe_detail` for `food_item_detail: {category, shopping_quantity, shopping_unit}`. Pydantic enforces:
- `item_type='recipe'` requires `recipe_detail` present and `food_item_detail` absent (and vice versa)
- `icon_emoji` and `icon_url` cannot both be set (XOR, mirrors the DB CHECK constraint)

### Meal Entries

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/meal-entries?start_date=X&end_date=Y&family_member_id=N` | List meal entries in date range with optional per-person filter |
| GET | `/meal-entries/{id}` | Get single meal entry with item + slot + participants eager-loaded |
| POST | `/meal-entries` | Create meal entry (body: `{date, meal_slot_type_id, item_id \| custom_meal_name, participant_ids?, notes?}`) |
| PATCH | `/meal-entries/{id}` | Update meal entry (cook-toggle, participants, notes, slot change) |
| DELETE | `/meal-entries/{id}` | Soft-delete meal entry; hides the row and returns `{entry, undo_token, expires_at}` for a 5-second in-place undo window. Shopping-list groceries are dispatched for removal immediately; undo re-adds them. |
| POST | `/meal-entries/{id}/undo` | Restore a soft-hidden user-undo meal entry. Body: `{undo_token}`. Returns restored entry (200), 404 (never a user-undo row), or 410 (expired / token mismatch / parent item deleted / race loser). |

Post-refactor, meal entries reference items via a single `item_id` field (the old `recipe_id` / `food_item_id` / `item_type` tuple is gone). The response embeds the full `Item` at `entry.item` with its detail eager-loaded.

### Calendar Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/calendar-events?start_date=X&end_date=Y` | List events in date range (required params; optional: assigned_to) |
| GET | `/calendar-events/{id}` | Get single event |
| POST | `/calendar-events` | Create event (MANUAL by default; set `calendar_id` to create as ICLOUD and push) |
| PATCH | `/calendar-events/{id}` | Update event (MANUAL/ICLOUD editable; `calendar_id` changes trigger source transitions) |
| DELETE | `/calendar-events/{id}` | Delete event (MANUAL/ICLOUD; ICLOUD deletion also pushes delete to remote) |

### Sections

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lists/{list_id}/sections` | List sections for a list (ordered by sort_order) |
| POST | `/lists/{list_id}/sections` | Create section in a list |
| PATCH | `/sections/{section_id}` | Update section (name, sort_order) |
| DELETE | `/sections/{section_id}` | Delete section (tasks in section become unsectioned) |
| POST | `/lists/{list_id}/sections/reorder` | Reorder sections (body: ordered array of section IDs) |

### Calendars

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/calendars/` | List all synced calendars with family member name and integration email (for dropdown) |

### Calendar Integrations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/integrations/icloud/validate` | Validate iCloud credentials, return available calendars with event counts and shared-calendar detection |
| POST | `/integrations/icloud/connect` | Connect iCloud Calendar (encrypt password, create integration, dispatch initial sync) |
| GET | `/integrations/` | List all connected integrations (optional: `?family_member_id=N`) |
| GET | `/integrations/{id}` | Get single integration |
| POST | `/integrations/{id}/sync` | Force sync for specific integration (dispatches Celery task) |
| DELETE | `/integrations/{id}` | Disconnect integration and cascade-delete all synced events |
| POST | `/integrations/icloud/validate-reminders` | Reuse existing credentials, list available reminder lists with task counts |
| POST | `/integrations/icloud/connect-reminders` | Add Calendar rows (is_todo=True) to existing integration, dispatch initial sync |
| POST | `/integrations/{id}/sync-reminders` | Manual sync for reminders only |
| DELETE | `/integrations/{id}/reminders` | Disconnect reminders only (clear sync metadata, keep tasks/lists local) |

### App Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/app-settings/` | Get current settings (timezone) |
| PATCH | `/app-settings/` | Update settings (timezone validated as IANA name) |
| GET | `/app-settings/timezones` | List all valid IANA timezone names |

### File Upload

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload file (multipart/form-data) |

**Response:**
```json
{"filename": "photo_123456.jpg", "url": "/uploads/photo_123456.jpg"}
```

---

## 3. Code Organization

### Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, router registration
│   ├── database.py          # Async session factory
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic validation schemas
│   │
│   ├── crud_tasks.py        # Task CRUD operations
│   ├── crud_lists.py        # List CRUD operations
│   ├── crud_family_members.py
│   ├── crud_responsibilities.py
│   ├── crud_items.py        # Unified Item CRUD (recipes + food items) + soft-delete/undo
│   ├── crud_meal_entries.py # Meal entry CRUD + visible_meal_entries_stmt helper
│   ├── crud_meal_slot_types.py
│   ├── crud_calendar_events.py
│   ├── crud_calendar_integrations.py
│   ├── crud_calendars.py     # Calendar CRUD (get_all, get_or_create for sync)
│   ├── crud_sections.py      # Section CRUD (get, create, update, delete, reorder)
│   ├── crud_app_settings.py  # Singleton settings CRUD (timezone)
│   │
│   ├── celery_app.py        # Celery app with Redis broker + beat schedule
│   ├── tasks.py             # Celery tasks (sync, push, delete)
│   │
│   ├── services/
│   │   ├── caldav_client.py  # CalDAV protocol (VEVENT + VTODO operations)
│   │   ├── sync_base.py      # Shared sync helpers (credential loading, status tracking)
│   │   ├── sync_engine.py    # Two-way calendar sync (pull, push, move, conflict resolution)
│   │   ├── reminders_sync_engine.py  # Two-way reminders sync (VTODO pull/push)
│   │   └── shopping_sync.py  # Mealboard meal-entry → shopping-task aggregation
│   │
│   ├── utils/
│   │   └── encryption.py     # Fernet encrypt/decrypt for stored passwords
│   │
│   └── routes/
│       ├── __init__.py
│       ├── tasks.py         # /tasks endpoints
│       ├── lists.py         # /lists endpoints
│       ├── family_members.py
│       ├── responsibilities.py
│       ├── items.py         # /items endpoints (unified recipes + food items, soft-delete + undo)
│       ├── meal_entries.py  # /meal-entries endpoints
│       ├── meal_slot_types.py
│       ├── calendar_events.py # /calendar-events endpoints (+ iCloud push/move dispatch)
│       ├── calendars.py     # /calendars endpoint (list for dropdown)
│       ├── integrations.py  # /integrations endpoints (validate, connect, sync, disconnect)
│       ├── sections.py     # /lists/{id}/sections + /sections/{id} endpoints
│       ├── app_settings.py  # /app-settings endpoints (timezone config)
│       └── uploads.py       # /uploads endpoints (family photos, responsibility icons; item icons → Chunk 5)
│
├── alembic/                 # Database migrations
│   ├── versions/            # Migration scripts
│   └── env.py
│
├── tests/
│   ├── unit/                # Unit tests (no DB)
│   └── integration/         # Integration tests (testcontainers)
│
├── pyproject.toml           # Dependencies (uv)
├── uv.lock                  # Lock file
├── Dockerfile
└── alembic.ini
```

### CRUD Pattern

Each entity has a dedicated CRUD file with standard operations:

```python
# crud_items.py — canonical query builder + CRUD for the unified Item model

def active_items_stmt(item_type: str | None = None, favorites_only: bool = False, search: str | None = None):
    """All list/detail/search reads build off this. Filters `deleted_at IS NULL`
    and eager-loads both detail relationships to avoid N+1."""
    stmt = (
        select(models.Item)
        .where(models.Item.deleted_at.is_(None))
        .options(
            selectinload(models.Item.recipe_detail),
            selectinload(models.Item.food_item_detail),
        )
    )
    if item_type is not None:
        stmt = stmt.where(models.Item.item_type == item_type)
    if favorites_only:
        stmt = stmt.where(models.Item.is_favorite.is_(True))
    if search:
        stmt = stmt.where(models.Item.name.ilike(f"%{search}%"))
    return stmt


async def create_item(db: AsyncSession, payload: schemas.ItemCreate) -> models.Item:
    """Create Item + type-appropriate detail row in one transaction."""
    item = models.Item(
        name=payload.name,
        item_type=payload.item_type.value,
        icon_emoji=payload.icon_emoji,
        icon_url=payload.icon_url,
        tags=payload.tags or [],
        is_favorite=payload.is_favorite,
    )
    db.add(item)
    await db.flush()  # populates item.id
    if payload.item_type == schemas.ItemType.RECIPE:
        db.add(models.RecipeDetail(item_id=item.id, **payload.recipe_detail.model_dump()))
    else:
        db.add(models.FoodItemDetail(item_id=item.id, **payload.food_item_detail.model_dump()))
    await db.commit()
    return await get_item(db, item.id)


async def soft_delete_item(db: AsyncSession, item_id: int):
    """Set items.deleted_at and cascade-hide meal_entries.soft_hidden_at in one transaction.
    Returns (item, undo_token, expires_at) — the token is opaque and expires in 15 seconds.
    The Celery beat task `hard_delete_expired_soft_deletes` (Chunk 6) purges expired items
    via a cascade-in-code transaction with an assertion gate (Eng Review #3 Issue 3)."""
    ...
```

`crud_meal_entries.py` owns `visible_meal_entries_stmt()` which filters `soft_hidden_at IS NULL` — every UI read path must go through this helper, NOT through `item.meal_entries` directly (that relationship back-populates all rows including hidden ones; see Eng Review #3 Issue 6).

All DB operations use `AsyncSession` with `selectinload()` for eager-loading relationships.

### Route Pattern

```python
# routes/items.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=list[schemas.ItemRead])
async def list_items(
    type: Literal["recipe", "food_item"] | None = Query(None),
    favorites_only: bool = False,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await crud_items.list_items(db, item_type=type, favorites_only=favorites_only, search=search)

@router.post("/", response_model=schemas.ItemRead, status_code=201)
async def create_item(payload: schemas.ItemCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await crud_items.create_item(db, payload)
    except IntegrityError:
        # Partial unique index on (name, item_type) raises on duplicate name
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"An item named '{payload.name}' of type '{payload.item_type.value}' already exists")

@router.delete("/{item_id}", response_model=DeleteResponse)
async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-delete. Returns {id, undo_token, expires_at}. Use POST /items/{id}/undo to restore."""
    result = await crud_items.soft_delete_item(db, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item, token, expires_at = result
    return DeleteResponse(id=item.id, undo_token=token, expires_at=expires_at)
```

---

## 4. Data Validation

### Pydantic Schema Pattern

```python
# Base: shared fields for create/read
class ItemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=200)
    item_type: ItemType  # 'recipe' | 'food_item'
    icon_emoji: Optional[str] = Field(None, max_length=10)
    icon_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False

# Create: includes nested type-specific detail
class ItemCreate(ItemBase):
    recipe_detail: Optional[RecipeDetailCreate] = None
    food_item_detail: Optional[FoodItemDetailCreate] = None

    @model_validator(mode="after")
    def check_type_and_detail(self):
        """item_type='recipe' requires recipe_detail, item_type='food_item' requires
        food_item_detail. icon_emoji and icon_url cannot both be set (XOR)."""
        ...

# Update: all fields optional, item_type is NOT patchable (delete + recreate instead)
class ItemUpdate(BaseModel):
    name: Optional[str] = None
    icon_emoji: Optional[str] = None
    icon_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    recipe_detail: Optional[RecipeDetailCreate] = None
    food_item_detail: Optional[FoodItemDetailCreate] = None

# Response: adds id, deleted_at, timestamps, nested detail
class ItemRead(ItemBase):
    id: int
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    recipe_detail: Optional[RecipeDetailRead] = None
    food_item_detail: Optional[FoodItemDetailRead] = None
```

### Validation Rules

| Entity | Field | Validation |
|--------|-------|------------|
| FamilyMember | name | 1-50 chars, unique |
| Task | title | 1-100 chars |
| Task | description | max 500 chars |
| Task | priority | Integer 0-9 (0=none, 1=high, 5=medium, 9=low) |
| Task | parent_id | Must reference task in same list_id; cycle detection (400 on cycle) |
| Task | section_id | Must reference section in same list_id (400 if mismatched) |
| Section | name | 1-100 chars |
| List | name | 1-100 chars |
| List | color | max 7 chars (hex) |
| Item | name | 1-200 chars, unique within item_type (partial index WHERE deleted_at IS NULL) |
| Item | item_type | must be `recipe` or `food_item` (Pydantic enum + DB CHECK) |
| Item | icon_emoji/icon_url | XOR — cannot both be set (Pydantic validator + DB CHECK) |
| ItemCreate (recipe) | recipe_detail | required when item_type='recipe' |
| ItemCreate (food_item) | food_item_detail | required when item_type='food_item' |
| RecipeDetail | description | max 1000 chars |
| RecipeDetail | servings | >= 1 |
| RecipeDetail | prep/cook time | >= 0 |
| FoodItemDetail | shopping_quantity | > 0 |
| FoodItemDetail | shopping_unit | must be in VALID_UNITS |
| MealEntry | item_id OR custom_meal_name | one of the two must be present (Pydantic validator + DB CHECK) |
| MealEntry | custom_meal_name | max 200 chars |
| MealEntry | notes | max 500 chars |
| CalendarEvent | title | 1-200 chars |
| CalendarEvent | description | max 500 chars |
| CalendarEvent | start_time/end_time | HH:MM format (regex validated) |
| CalendarEvent | end_time | Must be after start_time (model validator) |

---

## 5. Error Handling

### HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Successful GET, PATCH |
| 201 | Successful POST (create) |
| 204 | Successful DELETE (no content) |
| 400 | Validation error |
| 404 | Resource not found |
| 409 | Conflict (duplicate unique field) |
| 422 | Unprocessable entity (Pydantic validation) |
| 500 | Server error |

### Error Response Format

```json
{
  "detail": "Item not found"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Custom Exception Example

```python
@router.delete("/{member_id}", status_code=204)
async def delete_family_member(member_id: int, db: AsyncSession = Depends(get_db)):
    member = await crud_family_members.get_family_member(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    if member.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system member")
    if member.tasks:
        raise HTTPException(status_code=400, detail="Cannot delete member with assigned tasks")
    await crud_family_members.delete_family_member(db, member_id)
```
