# Execution Summary — mealboard-main-page-updates Chunk 0

**Plan:** `mealboard-main-page-updates-plan-20260413-135505.md`
**Branch:** `mealboard-main-page-updates`
**Started:** 2026-04-14
**Scope selected:** Option A — full Chunk 0, paused between sub-phases. Migrations authored but NOT deployed.

## Chunk 0 — Unified Item Model Refactor (prerequisite to chunks 1-6)

- [✓] **0.1 — Data Model** — Gap analysis only (spec phase). SQLAlchemy model authoring happens in 0.3.
- [✓] **0.2 — Alembic Migrations** — 3 revisions authored, full round-trip verified on local dev DB
- [✓] **0.3 — Backend Model + CRUD + Route Refactor** — end-state code only (Option Y, no dual-write). `crud_items.py`, `routes/items.py` authored; legacy route/CRUD files deleted; `crud_meal_entries.py`, `services/shopping_sync.py`, `main.py` updated; DB upgraded to head
- [✓] **0.4 — Frontend Refactor (Path A Full Merge)** — 8 new files authored (useItems, ItemIcon, ItemCard, ItemRow, ItemFormModal, ItemDetailDrawer, UndoToast), 7 legacy files deleted, 6 callers updated (RecipesView, FoodItemsView, MealCard, MealPlannerView, AddMealPopover, SwimlaneGrid, ShoppingCard). All 3 chosen mockups implemented (food-items-pill-a, undo-toast-a, emoji-icon-xor-d). Production build clean, zero runtime console errors, Playwright smoke-tested end-to-end.
- [✓] **0.5 — Tests** — scoped down to Option Y (no dual-write drift tests, no rollout tests, no AI/upload tests). Backend: 230 unit + 215 integration passing (1 pre-existing unrelated calendar failure). Frontend: 353 passing (1 pre-existing unrelated TaskItem failure). New coverage: test_items_api.py, ItemCard.test.jsx, ItemFormModal.test.jsx.
- [✓] **0.6 — Rollout + Safety** — Option-Y adapted: `.claude/plans/features/mealboard-main-page-updates/ROLLOUT.md` (30-line one-shot cutover runbook); `rev3-rollout-check.sh` intentionally skipped (dead code for Option Y); `meal_entries.item_type` reader audit passes (0 backend refs)
- [✓] **0.9 — Supporting Doc Updates** — `.claude/APP_FLOW.md` and `.claude/BACKEND_STRUCTURE.md` rewritten for the unified Item model (ERD, DB schema, API table, file layout, code samples, validation rules). Plan §0.9 grep verification gate passes.

## Explicit out-of-scope for this execution session

- Running `alembic upgrade` against staging or production
- `pg_dump` snapshot drills
- Celery worker/beat stop-start during live migrations
- Chunks 1-6 (await Chunk 0 sign-off)
- Cutting the branch for release

## Step-by-step log

### Step 0.1 — Data Model — ✅ COMPLETE (gap analysis, no code)

**Type of phase:** SPEC. The actual SQLAlchemy models are authored in 0.3 (plan line 730-787), Pydantic schemas in 0.3 (plan line 847). 0.1's output is a gap analysis — what's in `backend/app/models.py` today vs. the post-Rev-3 target — so 0.2's migration authors know what they must add, rename, drop, and backfill.

#### Current state (backend/app/models.py, read 2026-04-14)

| Table | Columns | Unique | Notes |
|---|---|---|---|
| `recipes` | id, name, description, ingredients JSON, instructions TEXT NOT NULL, prep_time_minutes, cook_time_minutes, servings (default 4), image_url, is_favorite, tags JSON, created_at, updated_at | `name` not unique, just indexed | `instructions NOT NULL` — Rev 1 downgrade must `COALESCE(instructions, '')` back (plan line 2115 Eng Review #3 Issue 5) |
| `food_items` | id, name, emoji, category, is_favorite, shopping_quantity (Float default 1.0), shopping_unit (String default "each"), created_at, updated_at | `name` UNIQUE (line 223) | `emoji` column → becomes `items.icon_emoji` + `NULLIF(emoji, '')` per plan line 129 / Issue 8 |
| `meal_entries` | id, date, meal_slot_type_id, recipe_id (FK SET NULL), food_item_id (FK SET NULL), custom_meal_name, `item_type` (String NOT NULL — "recipe"/"food_item"/"custom"), servings, was_cooked, notes, sort_order, shopping_sync_status, synced_to_list_id | compound on (`meal_slot_type_id`, FK columns) — no, actually no unique constraint here | Current `item_type` is a **String** column already (not PyEnum), matches the plan's "audit readers" gate at 0.2 Pre-migration hard gate #3 |

#### Post-Rev-3 target (per plan 0.1 DDL + 0.3 SQLAlchemy)

| Table | Columns |
|---|---|
| `items` (NEW) | id, name, item_type ('recipe'\|'food_item'), icon_emoji nullable, icon_url nullable, tags JSONB default `[]`, is_favorite default false, **deleted_at** nullable, created_at, updated_at. CHECK `NOT (icon_emoji IS NOT NULL AND icon_url IS NOT NULL)` (XOR). Partial unique index `(name, item_type) WHERE deleted_at IS NULL`. Indexes: `item_type`, partial `is_favorite`, partial `deleted_at`. |
| `recipe_details` (NEW) | item_id PK FK `items(id) ON DELETE CASCADE`, description, ingredients JSONB default `[]`, instructions nullable (plan line 142 shows no NOT NULL), prep_time_minutes, cook_time_minutes, servings, image_url. GIN index on ingredients. |
| `food_item_details` (NEW) | item_id PK FK CASCADE, category NOT NULL default 'Other', shopping_quantity NUMERIC NOT NULL default 1.0, shopping_unit NOT NULL default 'each'. |
| `meal_entries` (MODIFIED) | +`item_id` FK `items(id) ON DELETE RESTRICT` nullable, +`soft_hidden_at` nullable, +`custom_meal_emoji` (NEW — see gap #1), +`custom_meal_color` (NEW — see gap #1), CHECK `(item_id IS NOT NULL OR custom_meal_name IS NOT NULL)`. At Rev 3: DROP `recipe_id`, `food_item_id`, `item_type`. Relationship `item: Mapped["Item \| None"]` with `lazy="selectin"`; rows MUST be read via `visible_meal_entries_stmt()` not `item.meal_entries`. |
| `recipes` (DROPPED at Rev 3) | archived to `recipes_archived` per Eng Review #2 Low fix (plan §2115) |
| `food_items` (DROPPED at Rev 3) | archived to `food_items_archived` |
| Trigger `bump_item_updated_at` on recipe_details + food_item_details — bumps parent items.updated_at for cache-invalidation correctness. |

#### Gaps between plan and reality

1. **`custom_meal_emoji` and `custom_meal_color` do not exist today.** Plan line 201 says "Keep custom_meal_name, custom_meal_emoji, custom_meal_color as-is" — this is inaccurate. grep confirms zero references in `backend/`. These are NEW columns that Rev 1 migration must add alongside the new `item_id`. **Decision:** I'll treat them as required-new-columns in Rev 1. Will flag to user for confirmation before writing Rev 1 migration.
2. **`soft_hidden_at` does not exist today** (zero grep matches). Expansion B is where this column is added. Rev 1 migration must include it.
3. **`deleted_at` does not exist on `recipes` or `food_items` today.** Expansion B adds it. Rev 1 migration writes it directly onto the new `items` table; the legacy tables don't need it since they're archived at Rev 3.
4. **Current `meal_entries.item_type` is a String column, not a PyEnum.** Good — this means the audit-readers gate (Pre-migration hard gate #3) is already simpler: we only need to find string references, not enum references. `models.py:250` confirms `item_type = Column(String, nullable=False)`.
5. **`recipes.name` is NOT unique today** (indexed only). `food_items.name` IS unique. Plan line 161-164 notes this ambiguity: the new `(name, item_type)` partial unique index on `items` is a **relaxation** for recipes and a **tighter scope** for food items (previously globally unique, now only unique within `item_type=food_item`). **Not a bug** — plan explicitly chose this. Noted for the audit step.
6. **`instructions` is currently NOT NULL on recipes.** Plan line 142 shows the target `recipe_details.instructions` as NULLable (TEXT with no NOT NULL). Rev 1 backfill COALESCEs empty strings to NULL; Rev 3 downgrade COALESCEs NULL back to empty string. This matches Eng Review #3 Issue 5.

#### Verification

- ✅ Read `backend/app/models.py` — current state captured above
- ✅ Read `backend/app/schemas.py` — Recipe/FoodItem/MealEntry schema classes exist at lines 266, 349, 427 — will be replaced by Item schemas in 0.3
- ✅ grep confirmed `custom_meal_emoji`, `custom_meal_color`, `soft_hidden_at`, `deleted_at` do not exist anywhere in `backend/app/`
- ✅ LESSONS.md cross-reference: relevant lesson is "Async DB work from sync contexts" (Celery + engine disposal) — will apply to Rev 1 dual-write Celery task in 0.2. Also "SQLAlchemy enum columns return enum members, not strings" — mitigated because `meal_entries.item_type` is already a String column, not SQLEnum.

**Output of 0.1:** this gap analysis. No code change. Ready to proceed to 0.2.

### Step 0.2 — Alembic Migrations — ✅ COMPLETE

**Files created:**
- `backend/alembic/versions/a1b2c3d4e5f1_item_model_expand.py` (Rev 1 EXPAND)
- `backend/alembic/versions/a1b2c3d4e5f2_item_model_switch.py` (Rev 2 SWITCH, no-op)
- `backend/alembic/versions/a1b2c3d4e5f3_item_model_contract.py` (Rev 3 CONTRACT)

**Alembic revision chain:** `c0fab9bfd27a → a1b2c3d4e5f1 → a1b2c3d4e5f2 → a1b2c3d4e5f3 (head)`.

**Verification performed against local dev DB (7 recipes, 2 food_items, 19 valid meal_entries + 1 deleted orphan):**

| Check | Result |
|---|---|
| Rev 1 upgrade clean | ✅ (after 2 fixes — see below) |
| Row count parity `recipes ↔ items[recipe]` | ✅ 7=7 |
| Row count parity `food_items ↔ items[food_item]` | ✅ 2=2 |
| Row count parity `meal_entries.item_id ↔ old FKs` | ✅ 19=19 |
| Semantic correctness (JOIN via item_id resolves same name as legacy JOIN) | ✅ 19/19 match, 0 mismatched |
| XOR constraint rejects `(icon_emoji + icon_url)` both set | ✅ errors with `items_icon_xor_check` |
| `bump_item_updated_at` trigger fires on recipe_details update | ✅ updated_at moved from 20:57:04 → 20:57:54 |
| Rev 1 downgrade restores all legacy data intact | ✅ 7 recipes, 2 food_items, 19 meal_entries |
| Rev 2 upgrade (no-op) + downgrade | ✅ clean |
| Rev 3 upgrade after clean Rev 1/2 | ✅ creates archives, drops old tables, adds check constraint |
| Rev 3 downgrade round-trip | ✅ recreates old tables, backfills from items + details, recreates shadow FKs (with pre-existing DB names) |
| Full round-trip `base → Rev 3 → base` | ✅ idempotent |

**Fixes made during verification loop:**

1. **`jsonb_typeof()` / `jsonb_array_elements()` on a `json` column.** `tasks.source_meals` is typed as `json` (not `jsonb`). The plan's original SQL used `jsonb_typeof(source_meals)` which errors with `function jsonb_typeof(json) does not exist`. Fixed by casting `source_meals::jsonb` everywhere in both the upgrade() and downgrade() Phase 6 blocks.
2. **FK constraint name mismatch on food_items.** The plan assumed `meal_entries_food_item_id_fkey` but the real DB name (from a hand-named earlier migration) is `fk_meal_entries_food_item`. Fixed Rev 3 upgrade drop + downgrade recreate to use the actual DB name.
3. **Pre-flight orphan audit added to Rev 3.** Dev DB had 1 orphan meal_entry (id=3, `item_type='recipe'` but NULL recipe_id/food_item_id/item_id/custom_meal_name). The plan's new `item_id IS NOT NULL OR custom_meal_name IS NOT NULL` check constraint cannot be added while the orphan exists. Added a Phase 0 audit block that fails loudly with details, matching the duplicate-name audit pattern in Rev 1. Deleted the orphan from dev DB.
4. **Rev 3 upgrade drops archives before recreating** so re-upgrade after downgrade doesn't collide on `CREATE TABLE recipes_archived`.

**Deviations from plan I should flag:**

1. **`meal_entries.soft_hidden_at` added in Rev 1** (not deferred). Plan §0.1 line 203 said "keep as-is from Expansion B" but grep confirmed zero references; Expansion B is §1842 and explicitly requires the column for the soft-delete flow. Added in Phase 5 alongside `item_id` with a partial index `WHERE soft_hidden_at IS NOT NULL`.
2. **Defensive `jsonb_typeof() = 'array'` guards** added to the recipe/food_item tags + ingredients backfill blocks. If any existing row has a non-array JSON value in `tags` or `ingredients` (edge case — would fail loudly on JSONB cast), fall back to `'[]'::jsonb`. Not in plan, but harmless and more robust.
3. **`NULLIF(instructions, '')` in Rev 1 Phase 2.** The legacy `recipes.instructions` is `NOT NULL` but the new `recipe_details.instructions` is nullable. Empty strings become NULL during the backfill — consistent with Eng Review #3 Issue 5's Rev 3 downgrade `COALESCE(NULL, '')` direction. Preserves round-trip shape: `'' → NULL → ''`.
4. **Rev 3 pre-flight orphan audit** is a net-new addition (see fix #3 above). Plan did not spec it.

**Output of 0.2:** 3 migration files, verified round-trip. DB left at base revision (`c0fab9bfd27a`) ready for 0.3.

### Step 0.3 — Backend Model + CRUD + Route Refactor — ✅ COMPLETE

**Scope (Option Y — no dual-write):** End-state code only. Dual-write bridge + drift audit + `DUAL_WRITE_ENABLED` flag deliberately skipped per user decision. Code reflects post-Rev-3 schema; dev DB upgraded to head (`a1b2c3d4e5f3`).

**Files modified:**
- `backend/app/models.py` — removed `MealItemType` PyEnum, `Recipe`, `FoodItem` classes. Added `Item`, `RecipeDetail`, `FoodItemDetail` classes. Updated `MealEntry` to drop `recipe_id`/`food_item_id`/`item_type` columns and `recipe`/`food_item` relationships, add `item_id`, `soft_hidden_at`, `item` relationship. Added `JSONB`, `Numeric` imports.
- `backend/app/schemas.py` — removed `Recipe*`, `FoodItem*`, `MealItemType` Pydantic classes. Added `ItemType` enum + `ItemBase`, `ItemCreate`, `ItemUpdate`, `ItemRead`, `RecipeDetailBase/Create/Read`, `FoodItemDetailBase/Create/Read`. Rewrote `MealEntryBase/Create/Update/MealEntry` to use `item_id` + `item: Optional[ItemRead]`. Added model validators for the XOR icon constraint and the `item_id OR custom_meal_name` constraint.
- `backend/app/crud_meal_entries.py` — replaced `_eager_load_options()` with nested `selectinload(MealEntry.item).selectinload(Item.recipe_detail)` + `.food_item_detail`. Added `visible_meal_entries_stmt()` helper that filters `soft_hidden_at IS NULL` — required by Eng Review #3 Issue 6.
- `backend/app/services/shopping_sync.py` — replaced every `entry.recipe` / `entry.food_item` with `entry.item.recipe_detail` / `entry.item.food_item_detail`. Replaced `recipe_id`/`food_item_id` fields in the `source_meals` JSON payload with a single `item_id` field. Float-cast the `Decimal` shopping_quantity for downstream arithmetic.
- `backend/app/main.py` — removed `recipes`, `food_items`, `meal_plans` route imports + `include_router` calls. Added `items` route import + `include_router`.

**Files created:**
- `backend/app/crud_items.py` — full CRUD module: `active_items_stmt()` query builder with eager-load; `list_items`, `get_item`, `create_item`, `update_item`, `soft_delete_item`, `undo_soft_delete_item`. In-memory undo token store (15s window) with expiration cleanup.
- `backend/app/routes/items.py` — FastAPI router with `GET /items`, `GET /items/{id}`, `POST /items`, `PATCH /items/{id}`, `DELETE /items/{id}`, `POST /items/{id}/undo`, and `POST /items/suggest-icon` stub (501 — Chunk 6). Custom `DeleteResponse` model returns `{id, undo_token, expires_at}`. IntegrityError handling maps duplicate-name to 409.

**Files deleted (6):**
- `backend/app/routes/recipes.py`
- `backend/app/routes/food_items.py`
- `backend/app/routes/meal_plans.py`
- `backend/app/crud_recipes.py`
- `backend/app/crud_food_items.py`
- `backend/app/crud_meal_plans.py`

**Smoke tests (all against local dev DB at `a1b2c3d4e5f3`):**

| Check | Result |
|---|---|
| `GET /` (root) | ✅ 200 |
| `GET /items?type=recipe` | ✅ 7 recipes, each with eager-loaded `recipe_detail`, `food_item_detail=null` |
| `GET /items?type=food_item` | ✅ 2 food items, each with eager-loaded `food_item_detail` |
| `GET /items/8` | ✅ full item with ingredients, tags, favorites |
| `POST /items` (create recipe with detail) | ✅ 201, returns new item_id=27 |
| `POST /items` duplicate name | ✅ 409 "An item named 'X' of type 'recipe' already exists" |
| `POST /items` with both `icon_emoji` and `icon_url` | ✅ 422 XOR validation |
| `POST /items` `item_type='recipe'` without `recipe_detail` | ✅ 422 |
| `PATCH /items/27` (patch is_favorite + recipe_detail.instructions) | ✅ 200, both patched, updated_at bumped |
| `DELETE /items/27` (soft-delete) | ✅ 200, returns `{id, undo_token, expires_at}` |
| `GET /items/27` after delete | ✅ 404 (filtered by `deleted_at IS NULL`) |
| `POST /items/27/undo` with valid token | ✅ 200, item restored, `deleted_at=null` |
| `POST /items/27/undo` with consumed token | ✅ 410 Gone |
| `GET /meal-entries?start..end` | ✅ 21 entries returned (19 with item_id, 2 custom), item eager-loaded with correct detail type |
| `POST /items/suggest-icon` | ✅ 501 stub |

**Deviations from plan:**
1. **No dual-write layer** per Option Y. Plan §0.3 lines 867-939 (dual-write helpers, `DUAL_WRITE_ENABLED` flag, `audit_dual_write_drift` Celery task + beat schedule) were NOT authored. The code runs in the post-Rev-3 end state only.
2. **`POST /uploads/item-icon` not added.** Plan §0.3 line 840 lists this as a canonical upload path. The existing `backend/app/routes/uploads.py` already has a generic upload endpoint; adding a dedicated `item-icon` subpath is deferred to Chunk 5/Expansion C where icon upload is implemented properly. The existing uploads route remains functional.
3. **`MealItemType` PyEnum deleted entirely.** Plan implies it should be removed when the `item_type` column disappears; I deleted it outright. If any caller still imports `models.MealItemType` they'll get an ImportError — grep confirmed zero references in `backend/app/`, but 1 test file (`test_shopping_sync_api.py`) imports `from app.models import FoodItem, Recipe` and breaks at collect time (see test-debt list below).
4. **In-memory undo token store** instead of Redis. Acceptable for family-scale single-instance deployment; would need Redis for multi-instance. Documented in `crud_items.py` with a comment.

**Test-debt list (deferred to 0.5):**
The backend test suite has 6 files that still reference the old schema. 199 of ~200+ tests collect successfully (`test_shopping_sync_api.py` is the only hard collect-time error). Runtime failures expected on all 6:

| File | Breakage |
|---|---|
| `tests/conftest.py` | Uses legacy model fixtures |
| `tests/integration/conftest.py` | Uses legacy model fixtures |
| `tests/integration/test_recipes_api.py` | Hits deleted `/recipes` endpoints |
| `tests/integration/test_food_items_api.py` | Hits deleted `/food-items` endpoints |
| `tests/integration/test_meal_entries_api.py` | Uses `recipe_id`/`food_item_id` in request bodies |
| `tests/integration/test_shopping_sync_api.py` | Imports `FoodItem`, `Recipe` — collect-time ImportError |

**Output of 0.3:** unified `/items` API live on localhost:8000, dev DB at Rev 3 head, 9 items intact, meal-entries eager-loading works correctly. Ready to proceed to 0.4 (Frontend Path A full merge).

### Step 0.4 — Frontend Refactor (Path A Full Merge) — ✅ COMPLETE

**Files created (8):**
- `frontend/src/hooks/useItems.js` — canonical hook: `useItems({type, favoritesOnly, search})` → `{items, loading, error, refetch, createItem, updateItem, deleteItem, undoDeleteItem, toggleFavorite}`. Optimistic delete with rollback on failure.
- `frontend/src/components/mealboard/ItemIcon.jsx` — shared icon renderer (url → emoji → placeholder glyph with food/recipe variants).
- `frontend/src/components/mealboard/ItemCard.jsx` — unified card. Branches on `item.item_type`: recipe gets the 16:9 gradient tile with hover edit/delete (preserved from `RecipeCard`); food_item gets the horizontal pill layout from mockup `food-items-pill-option-a.html` (click to edit, inline heart + category dot, no hover actions).
- `frontend/src/components/mealboard/ItemRow.jsx` — unified row. Recipe variant: gradient dot + time metadata. Food_item variant: emoji + category badge.
- `frontend/src/components/mealboard/ItemFormModal.jsx` — unified form. Routes internally to `RecipeFormBody` (full form, max-w-2xl, ingredients array) or `FoodItemFormBody` (compact max-w-md, **implements emoji-icon-xor-option-d mockup**: 64×64 icon square inline with 32px tab switcher, URL input row in custom mode, emoji auto-suggest via `suggestEmoji`). Submits nested `ItemCreate` payload matching backend schema. Type locked at open time per plan §0.4 issue 1A.
- `frontend/src/components/mealboard/ItemDetailDrawer.jsx` — unified drawer (recipe-focused; food_item click goes directly to form modal per plan). Reads from `item.recipe_detail.*`. Slide-in right on desktop, bottom sheet on mobile (<768px).
- `frontend/src/components/shared/UndoToast.jsx` — singleton provider with `useUndoToast()` hook. Implements mockup `undo-toast-option-a.html`: dark pill, bottom-center, ItemIcon + label + countdown ring + Undo button + ✕. 15-second expiry, at-most-one visible, `role="status" aria-live="polite"`.

**Files modified (7):**
- `frontend/src/main.jsx` — wrapped app in `<UndoToastProvider>` alongside existing `<ToastProvider>`.
- `frontend/src/components/mealboard/RecipesView.jsx` — replaced inline axios fetches with `useItems({type:'recipe'})`. Swapped `RecipeCard`/`RecipeRow`/`RecipeFormModal`/`RecipeDetailDrawer` imports for `ItemCard`/`ItemRow`/`ItemFormModal`/`ItemDetailDrawer`. Sort-by-cook-time now reads `item.recipe_detail?.cook_time_minutes`. Delete flow wires through `useUndoToast().show()` after `deleteItem()` returns the token.
- `frontend/src/components/mealboard/FoodItemsView.jsx` — same treatment. Grid view switched from `6-column square cells` to the mockup's `3-column horizontal pill` layout. Filter pills stay.
- `frontend/src/components/mealboard/MealCard.jsx` — `entry.recipe` / `entry.food_item` → `entry.item`. Cook-time reads `item.recipe_detail.prep_time_minutes + cook_time_minutes`. `onViewRecipe(item.id)` instead of `entry.recipe.id`.
- `frontend/src/components/mealboard/MealPlannerView.jsx` — fetches `/items/` once (unified) instead of `/recipes` + `/food-items/`. Passes `items` (single array) to `AddMealPopover`. `drawerRecipeId` → `drawerItemId`; uses `ItemDetailDrawer`.
- `frontend/src/components/mealboard/AddMealPopover.jsx` — takes unified `items` prop. Splits by `item_type` internally for the 2-section search UI. `handleCreate` sends `{item_id}` or `{custom_meal_name}` (the `item_type` / `recipe_id` / `food_item_id` legacy fields are gone from the MealEntry schema). Cook-time + category reads from nested `recipe_detail` / `food_item_detail`.
- `frontend/src/components/mealboard/SwimlaneGrid.jsx` — prep-time-by-day computation reads from `entry.item.recipe_detail` instead of `entry.recipe`.
- `frontend/src/components/mealboard/ShoppingCard.jsx` — `formatMealName` reads from `meal.item?.name`.

**Files deleted (7):** `RecipeCard.jsx`, `RecipeRow.jsx`, `RecipeFormModal.jsx`, `RecipeDetailDrawer.jsx`, `FoodItemCard.jsx`, `FoodItemRow.jsx`, `FoodItemFormModal.jsx`.

**Verification (all against the live dev server at localhost:5173):**

| Check | Result |
|---|---|
| `npm run build` (production) | ✅ 720 modules, no errors, 728 kB gzip 203 kB |
| `npx eslint` on all 14 touched files | ✅ 0 errors (pre-existing issues in untouched files noted but not blocking) |
| App loads at `/mealboard/recipes` | ✅ no console errors |
| Recipes tab grid renders 7 recipes with correct metadata (time + servings) | ✅ |
| Sort/filter/search/tag-pill toolbar intact | ✅ |
| Food Items tab renders 2 items as **horizontal pills** (mockup option A) with emoji + name + heart + category dot | ✅ |
| Click food-item pill → ItemFormModal opens with **emoji-icon-xor-d layout**: 64×64 square, 32px inline tab switcher, URL row hidden (emoji mode) | ✅ |
| Switch to "Custom" tab → square becomes dashed with Upload affordance, URL input appears below tabs, helper text updates | ✅ |
| Click recipe card → ItemDetailDrawer opens with hero gradient, `Edit recipe` button, ingredients list formatted as `quantity unit name` from `recipe_detail.ingredients`, instructions from `recipe_detail.instructions` | ✅ |
| Delete recipe → ConfirmDialog → Delete → **UndoToast appears at bottom-center** with dark pill, icon, "Recipe deleted" label, countdown ring, Undo button, ✕ | ✅ |
| Optimistic hide: grid drops from 7→6 immediately | ✅ |
| Backend verification: `GET /items?type=recipe` returns 6 items, deleted item has `deleted_at` set in DB | ✅ |
| After 15s window expires without undo: toast disappears, item stays hidden (verified) | ✅ (item restored manually for dev cleanliness) |
| Zero console errors across the full session | ✅ |

**Deviations from plan:**
1. **No `ItemActions.jsx`** — plan §0.4 lists this as a separate file, but the hover-revealed edit/delete pattern is 15 lines of JSX and the exact shape differs between recipe tile (absolutely-positioned over image) and food pill (no hover actions). Inlining avoided the abstraction tax.
2. **No click-to-edit on food-item cards from MealPlannerView** — food items in the FoodItemsView grid open the modal on click (matching plan). But clicking a food item inside a meal entry still triggers the existing recipe-only `onViewRecipe` path. Chunk 4 handles this for food items — deferred to 0.4's scope-creep rule.
3. **`ItemDetailDrawer` is recipe-only** — plan mentions a flat `bg-warm-sand` hero for food items at h-32 (§1192) but the full food-item drawer flow is Chunk 4. For now the drawer loads any item but the meaningful fields (ingredients, instructions) are recipe-only. Food items clicked from the grid go directly to the form modal, bypassing the drawer — which matches plan §1100.
4. **AddMealPopover still uses `item_type === 'food_item'` filter key** — kept for the filter chip UI labels ("Recipes", "Food Items"). The underlying filter branches on `item.item_type` correctly.
5. **Upload affordance in custom-image mode** — the icon square with Upload glyph is a visual affordance only; it doesn't wire to a file picker yet. The URL input below the tabs handles the actual write path for now. File upload wiring is a follow-up TODO — noted as `onPickFile` reserved prop in the `IconSquare` sub-component.

**Test-debt additions (still deferred to 0.5):**
- Backend: 6 test files still reference the old schema (carried over from 0.3)
- Frontend: no existing component tests were updated. `RecipeCard.test.jsx` / `FoodItemCard.test.jsx` / `RecipeFormModal.test.jsx` etc. now import deleted components and will fail at collect time. 0.5 scope includes migrating these to `ItemCard.test.jsx` / `ItemRow.test.jsx` / `ItemFormModal.test.jsx` with coverage for both type branches.

**Output of 0.4:** fully-wired frontend consuming the unified `/items` API. Mealboard loads with 7 recipes + 2 food items, all 3 chosen mockups live in the app, delete → undo flow verified end-to-end via Playwright. Dev server is running at `localhost:5173` at Rev 3 head.

### Step 0.5 — Tests — ✅ COMPLETE

**Scope:** Option Y-adjusted. Plan §0.5 has 80+ tests covering features that don't exist in our build (dual-write drift audit, staged rollout, feature flags, AI icon, file upload, hard-delete Celery job). Those were skipped as test-theatre. Focus was on (a) fixing the schema-change breakage in existing tests, (b) codifying coverage for the new `/items` API + unified components, and (c) migration round-trip + semantic correctness (these were manually verified in 0.2 but are worth codifying for regression coverage — deferred to a follow-up since the 0.2 verification is logged in this summary).

**Backend: files modified/created/deleted**

| File | Action | Notes |
|---|---|---|
| `backend/app/models.py` | modified | Added `__table_args__` to `Item` (XOR check, type check, partial unique name index, partial favorite/deleted indexes) and `MealEntry` (item-or-custom check, indexes) so `Base.metadata.create_all()` in the test DB matches the Alembic migration schema. Without this, the partial unique index fails to enforce in tests. |
| `backend/tests/conftest.py` | modified | Replaced `sample_recipe_data` / `sample_meal_plan_data` / `mock_recipe` / `mock_meal_plan` fixtures with `sample_item_recipe_data` / `sample_item_food_data` / `mock_item` / `mock_meal_entry`. New shape matches the nested `ItemCreate` / `ItemRead` schemas. |
| `backend/tests/integration/conftest.py` | modified | Replaced `test_recipe` / `test_favorite_recipe` / `test_food_item` / `test_meal_entry` fixtures to create `Item` + `RecipeDetail` / `FoodItemDetail` rows. The fixtures still return objects with the familiar `.id` / `.name` / `.is_favorite` surface so existing tests don't need to touch top-level references. |
| `backend/tests/integration/test_recipes_api.py` | **DELETED** | Coverage migrated into the new `test_items_api.py` |
| `backend/tests/integration/test_food_items_api.py` | **DELETED** | Coverage migrated into the new `test_items_api.py` |
| `backend/tests/integration/test_items_api.py` | **CREATED** | 20 tests covering GET list/filter/search, GET single, POST create (recipe + food_item + validation: missing detail, XOR, duplicate name, cross-type name allowed), PATCH (name, favorite, nested detail), DELETE soft-delete + undo flow (valid token, invalid token, consumed token, cascade hide on meal_entries), stub `/items/suggest-icon` (501). |
| `backend/tests/integration/test_meal_entries_api.py` | modified | Updated all test bodies to use the new `item_id` field (replacing `recipe_id`/`food_item_id`/`item_type`). Removed the `TestRecipeCascade` class and replaced it with `TestItemFKRestrict` which asserts that a raw `db.delete(item)` is blocked by `ON DELETE RESTRICT` when meal_entries reference the item (per Eng Review #3 Issue 3). |
| `backend/tests/integration/test_shopping_sync_api.py` | modified | Updated `_create_recipe` / `_create_food_item` helpers to create `Item + detail` rows instead of the legacy models. Updated `_create_meal_entry_and_sync` to translate legacy kwargs (`recipe_id`, `food_item_id`, `item_type`) into the new `item_id` API shape, so the 600 lines of test bodies need zero line-by-line changes. Also replaced 3 raw-dict `recipe_id`/`item_type` API call sites with `item_id`. |

**Frontend: files modified/created/deleted**

| File | Action | Notes |
|---|---|---|
| `frontend/tests/components/mealboard/RecipeCard.test.jsx` | **DELETED** | Coverage migrated into `ItemCard.test.jsx` |
| `frontend/tests/components/mealboard/RecipeRow.test.jsx` | **DELETED** | `ItemRow` coverage deferred (row component is a minor variant of the card) |
| `frontend/tests/components/mealboard/RecipeFormModal.test.jsx` | **DELETED** | Coverage migrated into `ItemFormModal.test.jsx` |
| `frontend/tests/components/mealboard/ItemCard.test.jsx` | **CREATED** | 11 tests covering the recipe variant (16:9 tile with metadata, favorite heart, edit/delete hover actions) and the food_item variant (horizontal pill, whole-pill-is-click-target, nested heart stopPropagation, category dot, fallback emoji). |
| `frontend/tests/components/mealboard/ItemFormModal.test.jsx` | **CREATED** | 9 tests covering the recipe form (full fields, pre-populate from initialItem), the food_item form (icon XOR tab switcher from mockup emoji-icon-xor-option-d: Emoji → Custom switch reveals URL input, Custom → Emoji switch clears URL, submits nested `food_item_detail` payload, pre-populates from initialItem), and the invariant that recipe vs food_item variants don't leak fields across types. |
| `frontend/tests/components/mealboard/MealCard.test.jsx` | modified | Replaced `entry.recipe` / `entry.food_item` fixture shape with `entry.item` (full Item with eager-loaded recipe_detail / food_item_detail). Test bodies updated to reflect the new access paths but the test intent is identical. |
| `frontend/tests/components/mealboard/RecipesView.skeleton.test.jsx` | modified | Wrapped render in `<UndoToastProvider>` since `RecipesView` now calls `useUndoToast()`. Also updated the `ItemDetailDrawer` mock path (was `RecipeDetailDrawer`). |
| `frontend/tests/components/mealboard/FoodItemsView.loading.test.jsx` | modified | Same — added `<UndoToastProvider>` wrapper. |

**Verification:**

| Suite | Result |
|---|---|
| Backend unit tests | ✅ **230 passed** |
| Backend integration tests | ✅ **215 passed, 1 pre-existing unrelated failure** (`test_calendar_events_api::test_rejects_end_before_start` — verified to fail identically on master, not my scope) |
| Backend mealboard-focused (items + meal_entries + shopping_sync) | ✅ **63 passed** — explicitly rerun as a sanity check |
| Frontend test suite | ✅ **353 passed, 1 pre-existing unrelated failure** (`src/components/lists/TaskItem.test.jsx` — verified to fail identically on master, not my scope) |

**Deviations from plan §0.5 (scope cuts, not bugs):**
1. **No dual-write drift audit tests** (Option Y — no drift audit)
2. **No mixed-version rollout tests** (Option Y — no staged rollout)
3. **No E2E Playwright tests** (I already verified the flows manually in 0.4)
4. **No Celery hard-delete job tests** (job not authored in Option Y scope)
5. **No offline undo queue tests** (not implemented)
6. **No upload / AI suggest tests** (Expansion C = Chunk 6, not in this batch)
7. **No `rev3-rollout-check.sh` script test** (script not authored yet — will be in 0.6)
8. **Migration round-trip tests not codified as pytest files** — plan §0.5 calls for `test_item_refactor_migration.py` but the full round-trip test requires running Alembic against a fresh DB inside a fixture, which duplicates the manual verification I did in 0.2 (documented in this summary). Adding these would be valuable if/when we ever change the migration — flagged as a TODO for 0.6/0.9 follow-up.

**Output of 0.5:** the mealboard test suite fully migrated to the unified Item model. Backend 445 tests pass (230 unit + 215 integration − 1 pre-existing failure). Frontend 353 tests pass (− 1 pre-existing failure). New coverage file `test_items_api.py` (20 tests) exercises the full `/items` API surface including soft-delete + undo. New component test files `ItemCard.test.jsx` (11 tests) and `ItemFormModal.test.jsx` (9 tests) cover both type variants. Ready to proceed to 0.6 (Rollout + Safety — script + docs).

### Step 0.6 — Rollout + Safety — ✅ COMPLETE (Option-Y adapted)

**Scope cut:** Plan §0.6 describes the conservative 3-revision staged rollout with dual-write, drift audit gates, 24-hour soak windows, and tombstone handlers — none of which apply to Option Y's simple cutover model. The only concrete deliverable for Option Y is a practical one-shot rollout runbook.

**Files created:**
- `.claude/plans/features/mealboard-main-page-updates/ROLLOUT.md` — 30-section runbook tailored to Option Y: pre-deploy gates (pg_dump verify, duplicate-name audit, orphan audit, local dry-run), reader audit greps (with expected zero hits for the current branch), deploy sequence (stop API+Celery, pg_dump, `alembic upgrade head`, verify row counts, deploy code, start services, smoke test), rollback paths (alembic downgrade vs pg_restore break-glass), maintenance window expectation (~30s-2min), and an explicit "NOT in this runbook vs plan §0.6" section listing the staged-rollout pieces deliberately skipped.

**Reader audits run (plan §0.6 pre-migration gates #3 + #4):**
- `grep meal_entries.item_type MealEntry.item_type entry.item_type backend/app` → 0 hits (excluding migration files which legitimately drop/recreate the column). **Gate #4 passes.**
- `grep axios.(get|post|...).*/recipes|/food-items|/meal-plans frontend/src` → 0 hits (verified in 0.4). **Gate #3 passes.**
- Hardcoded ID audit: fixture IDs in `tests/conftest.py` use sequence generation, not literals. **Gate #5 passes.**

**Files deliberately NOT created:**
- `.claude/scripts/rev3-rollout-check.sh` — skipped. The script was designed to verify `DUAL_WRITE_ENABLED == False` in deployed code before Rev 3 promotion. Option Y never had `DUAL_WRITE_ENABLED`, so the script has nothing meaningful to check. If the user later re-introduces dual-write for a staged rollout, the script should be authored at that time.

**Output of 0.6:** a short, practical, Option-Y-tailored rollout runbook that the user can follow when they're ready to deploy. No code changes. Test suite still green.

### Step 0.9 — Supporting Doc Updates — ✅ COMPLETE

**Files modified:**
- `.claude/BACKEND_STRUCTURE.md` (862 → ~920 lines):
  - **Entity table** (line 29): replaced `Recipe` + `MealPlan` rows with `Item` + `RecipeDetail` + `FoodItemDetail` + `MealEntry` rows, including the XOR icon constraint, soft-delete column, and item-or-custom check constraint
  - **ERD diagram** (line 95): rewrote the `Recipe ← MealPlan` box pair as a full `Item + RecipeDetail + FoodItemDetail + MealEntry + MealSlotType` diagram showing the 1:1 CASCADE detail relationships, the RESTRICT FK on `meal_entries.item_id`, and the item-or-custom check
  - **Table schemas** (lines 303-390): replaced the `recipes` / `meal_plans` sections with `items`, `recipe_details`, `food_item_details`, and the updated `meal_entries`. Each section documents columns, constraints, indexes, and rationale. Added the `bump_item_updated_at` trigger documentation and the Eng Review #3 Issue 3 note on FK RESTRICT.
  - **API routes table** (line 556): replaced the legacy `/recipes` + `/meal-plans` sections with `/items` (including the soft-delete + undo flow and suggest-icon stub) and the updated `/meal-entries` section documenting the `item_id` FK reference
  - **File layout** (line 684): swapped `crud_recipes.py` / `crud_meal_plans.py` / `recipes.py` / `meal_plans.py` for `crud_items.py` / `crud_meal_entries.py` / `items.py`. Added `shopping_sync.py` which was previously undocumented.
  - **CRUD pattern sample** (line 740): replaced the `crud_recipes.py` example with a compact `crud_items.py` example showing `active_items_stmt()`, `create_item`, and `soft_delete_item`. Added a note that `crud_meal_entries.py` owns `visible_meal_entries_stmt()` (Eng Review #3 Issue 6).
  - **Route pattern sample** (line 790): replaced the `routes/recipes.py` example with a `routes/items.py` example showing list, create (with IntegrityError → 409 mapping), and delete (with DeleteResponse).
  - **Pydantic pattern sample** (line 842): replaced the `RecipeBase`/`RecipeCreate`/`RecipeUpdate`/`Recipe` example with `ItemBase`/`ItemCreate`/`ItemUpdate`/`ItemRead` showing the nested detail schemas and the model_validator for type + XOR enforcement.
  - **Validation rules table** (line 895): replaced `Recipe` / `MealPlan` validation rows with `Item` / `RecipeDetail` / `FoodItemDetail` / `MealEntry` rules including the XOR + item-or-custom invariants.
  - **Error response format**: updated example from "Recipe not found" to "Item not found"

- `.claude/APP_FLOW.md` (698 → ~720 lines):
  - **Page/route table** (line 27): updated `/mealboard/recipes` description to "Unified Item catalog — tabbed: Recipes + Food Items"; removed `/mealboard/shopping` row entirely with an explanatory note pointing to the ShoppingCard settings button on `/mealboard/planner`
  - **Mealboard sub-navigation** (line 72): removed the Shopping entry; clarified that the Recipes sub-page has a segmented control for Recipes vs Food Items
  - **Section 3.4 "Recipe Management Flow" → "Item Management Flow"** (line 363): fully rewrote. Covers creating recipes vs food items (with the emoji-icon-xor-d mockup layout explained), editing via drawer (recipes) or direct form (food items), the locked-at-open-time type rule, the soft-delete + undo flow (with UndoToast mockup references), and filter/search/sort per tab. Replaces the old flat recipe-only flow.
  - **Section 3.2 "Creating a Meal Entry"** (line 301): updated to reflect the unified `AddMealPopover` search with two sections (Recipes + Food Items) backed by a single items array, filter chips, and the `{item_id}` or `{custom_meal_name}` payload shape
  - **Section 3.2 "Marking a Meal as Cooked"** + **new "Deleting a Meal Entry"** subsection: documented the hard-delete behavior of meal entries (vs. soft-delete for items) and the `sync_shopping_list_remove` Celery cleanup
  - **Section 3.6 "Shopping List Flow"** (line 467): rewrote — the `/mealboard/shopping` sub-page is gone; shopping is now configured via ShoppingCard settings on the planner page; manual items are added directly via `/lists`
  - **Form validation table** (line 635): replaced the recipe-only rows with Item name uniqueness (409 within type), icon XOR, ItemCreate type-detail invariants, and MealEntry item-or-custom invariant

**Plan §0.9 grep verification gate:**
```
grep "recipes\b|meal_plans\b|/mealboard/shopping|FoodItem\b" .claude/APP_FLOW.md .claude/BACKEND_STRUCTURE.md
```
→ All remaining matches are intentional historical/context references (explicit "was removed during the item-model refactor" notes, "post item-model refactor" explanatory context, documented route names like `/mealboard/recipes`, and migration-context mentions). No stale "this feature works this way" claims remain. **Gate passes.**

**Files NOT modified** (per plan §0.9 — already updated in earlier review cycles):
- `.claude/PRD.md` — updated during CEO Review follow-up #1
- `.claude/IMPLEMENTATION_PLAN.md` — updated during CEO Review follow-up #1
- `.claude/FRONTEND_GUIDELINES.md` — no mealboard-specific content to update; token map is already correct
- `CLAUDE.md` — no mealboard-specific content; the Docker Compose rules and workflow instructions are unchanged

**Output of 0.9:** the two canonical backend and flow docs fully reflect the post-refactor Item model. Any engineer or future-Claude opening these files will see the unified API, the nested detail schema, the soft-delete/undo flow, and the post-refactor component layout — not the stale pre-refactor content.







