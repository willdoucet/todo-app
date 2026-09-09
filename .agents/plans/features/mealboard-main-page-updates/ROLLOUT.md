# Mealboard Item-Model Refactor — Rollout Runbook (Option Y — one-shot cutover)

This runbook is tailored to **Option Y** (single-instance, family-scale app, no staged Rev 1 → Rev 2 → Rev 3 dual-write window). It replaces plan §0.6 which describes the more conservative 3-revision staged rollout.

> **Why the simpler cutover is safe here:** one user, ~9 items, ~21 meal entries, single-instance deployment. A ~30-second outage during `alembic upgrade head` is acceptable. The three migration files (`a1b2c3d4e5f1` → `a1b2c3d4e5f2` → `a1b2c3d4e5f3`) are still authored and committed so you retain the option to stage later if you ever scale up.

---

## Pre-deploy gates

All four must pass before running `alembic upgrade head` in production:

1. **`pg_dump` of production taken and verified.** Store to a path outside the repo (gitignored). Verify by restoring to a throwaway clone DB and `SELECT COUNT(*)` on `recipes`, `food_items`, `meal_entries`, `tasks`. Never drop the live DB as part of the restore drill.
   ```bash
   TS=$(date -u +%Y%m%dT%H%M%SZ)
   pg_dump -h HOST -U USER -d todo_app -Fc > ~/backups/pre-item-refactor-${TS}.dump
   # Verify restore on a throwaway clone
   createdb todo_app_restore_probe
   pg_restore -d todo_app_restore_probe ~/backups/pre-item-refactor-${TS}.dump
   psql todo_app_restore_probe -c "SELECT (SELECT COUNT(*) FROM recipes) AS r, (SELECT COUNT(*) FROM food_items) AS f, (SELECT COUNT(*) FROM meal_entries) AS m"
   dropdb todo_app_restore_probe
   ```

2. **Pre-flight duplicate-name audit** (Rev 1 migration will fail loudly if this isn't clean):
   ```bash
   psql todo_app -c "
     SELECT 'recipe' AS type, name, COUNT(*) FROM recipes GROUP BY name HAVING COUNT(*) > 1
     UNION ALL
     SELECT 'food_item', name, COUNT(*) FROM food_items GROUP BY name HAVING COUNT(*) > 1"
   ```
   Expected: zero rows. If any duplicates, rename them before proceeding.

3. **Pre-flight orphan audit** (Rev 3 migration will fail loudly if this isn't clean):
   ```bash
   psql todo_app -c "
     SELECT id, date, item_type FROM meal_entries
     WHERE recipe_id IS NULL AND food_item_id IS NULL
       AND (custom_meal_name IS NULL OR custom_meal_name = '')"
   ```
   Expected: zero rows. If any orphans, delete them or set a `custom_meal_name`.

4. **Local dry-run.** Run the Rev 1 → 2 → 3 sequence against a local Postgres loaded from the production pg_dump. Verify row count parity (`items[recipe]` == `recipes`, `items[food_item]` == `food_items`, `meal_entries WHERE item_id IS NOT NULL` == `meal_entries WHERE recipe_id OR food_item_id`). Record the pre/post counts in the deploy PR description.

## Reader audits (run these greps; expect zero hits in live code)

Plan §0.6 Pre-migration gate #3 + #4. These are already verified for the current branch as of 2026-04-14:

```bash
# No backend readers of meal_entries.item_type
grep -rIn "meal_entries\.item_type\|MealEntry\.item_type\|entry\.item_type" \
  backend/app  # should return 0

# No frontend references to meal-plans / legacy routes
grep -rIn "axios\.\(get\|post\|patch\|delete\).*['\"]\(/recipes\|/food-items\|/meal-plans\)" \
  frontend/src  # should return 0

# No hardcoded recipe/food_item IDs in tests or seed data
grep -rIn "recipe_id *= *[0-9]\|food_item_id *= *[0-9]" \
  backend/tests  # noise is OK if it's inside a fixture that uses sequence IDs
```

## Deploy sequence

> **Target state:** DB at head (`a1b2c3d4e5f3`), backend running the Option-Y end-state code, frontend running the unified `/items` API client.

```
1. Announce maintenance window (1-2 min expected)

2. Stop the API and Celery
   docker-compose stop api celery_worker celery_beat

3. Take a fresh pg_dump (already verified in gate 1)
   pg_dump -h HOST -U USER -d todo_app -Fc > ~/backups/deploy-${TS}.dump

4. Run all three migrations in one shot
   docker-compose run --rm api .venv/bin/alembic upgrade head

5. Verify post-migration state
   docker-compose run --rm api .venv/bin/alembic current
   # Expected: a1b2c3d4e5f3 (head)

   psql todo_app -c "SELECT
     (SELECT COUNT(*) FROM items WHERE item_type='recipe') AS items_recipe,
     (SELECT COUNT(*) FROM items WHERE item_type='food_item') AS items_food,
     (SELECT COUNT(*) FROM recipe_details) AS rd,
     (SELECT COUNT(*) FROM food_item_details) AS fid,
     (SELECT COUNT(*) FROM meal_entries WHERE item_id IS NOT NULL) AS me_linked"

   # Old tables should be gone
   psql todo_app -c "\dt recipes food_items" # expected: "Did not find any relation"

   # Archives should exist (read-only snapshots, 30-day soak)
   psql todo_app -c "SELECT
     (SELECT COUNT(*) FROM recipes_archived) AS archived_recipes,
     (SELECT COUNT(*) FROM food_items_archived) AS archived_food_items"

6. Deploy the new backend + frontend code (both pre-built)

7. Start services
   docker-compose up -d api celery_worker celery_beat

8. Smoke test (5 min)
   - GET /items → returns items, correct count
   - GET /items/{id} → returns item with detail eager-loaded
   - POST /items → creates successfully
   - PATCH /items/{id} → updates successfully
   - DELETE /items/{id} → soft-deletes + returns undo_token
   - POST /items/{id}/undo → restores
   - Open Mealboard in the browser, verify the Recipes + Food Items tabs load
   - Add a meal entry, verify it shows in the planner
   - Shopping list sync fires after meal entry create (check Celery logs)
```

## Rollback

**Within 5 minutes of upgrade:** the archives (`recipes_archived`, `food_items_archived`) are still fresh. You have two paths:

1. **Alembic downgrade (lossy for post-Rev-3 items without instructions)**:
   ```bash
   docker-compose run --rm api .venv/bin/alembic downgrade c0fab9bfd27a
   ```
   This recreates the `recipes` / `food_items` tables, backfills from `items`, drops the new `items` / `recipe_details` / `food_item_details` tables. Note: the `item_model_contract` downgrade re-creates the old tables; it does NOT restore the archived rows that were fresher than the point of upgrade.

2. **pg_restore break-glass** (prefer for >5 minutes post-deploy):
   ```bash
   # Spin up a new DB, restore, then rename
   createdb todo_app_restored
   pg_restore -d todo_app_restored ~/backups/deploy-${TS}.dump
   # Verify, then cut over (swap DB URL env var + restart)
   ```
   This is the safer path for any rollback >5 minutes post-deploy since the archives may be stale by then.

**Beyond 30 days:** Rev 4 cleanup drops `recipes_archived` and `food_items_archived`. If you haven't authored Rev 4 yet, the archives will sit there indefinitely (low storage cost; harmless). Once Rev 4 ships, full restoration requires the pg_dump.

## Maintenance window

- **Expected downtime:** ~30s-2min total for the `alembic upgrade head` + API container restart. Family-scale data (9 items, 21 meal entries) completes the migration in well under a second; the rest is container restart time.
- **Schedule during low-traffic:** late evening is fine. Nobody is planning next week's dinner at 11pm.

## What's explicitly NOT in this runbook (vs. plan §0.6)

- **No dual-write drift audit gate** — we don't have dual-write, so there's no drift to audit.
- **No ≥24 consecutive clean runs promotion gate** — one-shot cutover, no promotion steps.
- **No `410` tombstone handlers for legacy routes** — the legacy routes are deleted in the same deploy, not kept around as tombstones.
- **No `rev3-rollout-check.sh`** — designed to verify `DUAL_WRITE_ENABLED == False` in deployed code; we never had `DUAL_WRITE_ENABLED`.
- **No feature-flag fallback for `MEALBOARD_SOFT_DELETE_ENABLED`** — not implemented in Option Y.
- **No staging environment soak** — household-scale app, single-instance. If you add staging later, run the same sequence there first.

## If you ever scale up and need the staged rollout

Plan §0.6 / §0.6A / §0.6B describe the full 3-revision staged rollout with dual-write code, drift audit, and tombstone handlers. You'd need to:
1. Re-introduce the `DUAL_WRITE_ENABLED` flag + helpers in `crud_items.py` (~1 CC hour)
2. Author `audit_dual_write_drift` Celery task + beat schedule (~30 min)
3. Author `rev3-rollout-check.sh` script (~15 min)
4. Add `410` tombstone handlers for `/recipes` and `/food-items` in `main.py` (~15 min)

The three Alembic migration files are unchanged in that scenario — they were authored for the staged-rollout case and are already production-safe.
