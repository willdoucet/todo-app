# Mealboard Backend Implementation Summary

## Scope

Implement full CRUD API for the Mealboard feature to support the completed frontend.

## Deliverables

### New Files
- `app/crud_recipes.py` - Recipe CRUD operations
- `app/crud_meal_plans.py` - MealPlan CRUD operations
- `app/routes/recipes.py` - `/recipes` API endpoints
- `app/routes/meal_plans.py` - `/meal-plans` API endpoints
- `tests/unit/test_crud_recipes.py`
- `tests/unit/test_crud_meal_plans.py`
- `tests/integration/test_recipes_api.py`
- `tests/integration/test_meal_plans_api.py`

### Modified Files
- `app/models.py` - Add MealCategory enum, update Recipe model, add MealPlan model
- `app/schemas.py` - Add MealCategory, Ingredient, Recipe*, MealPlan* schemas
- `app/main.py` - Register new routers
- `tests/conftest.py` - Add sample data fixtures
- `tests/integration/conftest.py` - Add test_recipe, test_meal_plan fixtures

### Database Migration
- Drop/recreate `recipes` table with full schema
- Create `meal_plans` table with recipe FK

## API Endpoints

```
GET    /recipes                         List recipes (optional: ?favorites_only=true)
GET    /recipes/{id}                    Get recipe
POST   /recipes                         Create recipe
PATCH  /recipes/{id}                    Update recipe
DELETE /recipes/{id}                    Delete recipe

GET    /meal-plans?start_date=&end_date=  Get plans for date range
GET    /meal-plans/{id}                   Get plan (includes nested recipe)
POST   /meal-plans                        Create plan entry
PATCH  /meal-plans/{id}                   Update plan (was_cooked, notes)
DELETE /meal-plans/{id}                   Delete plan entry
```

## Data Models

### Recipe
- name, description, ingredients (JSON), instructions
- prep_time_minutes, cook_time_minutes, servings
- image_url, is_favorite, tags (JSON)
- created_at, updated_at

### MealPlan
- date, category (BREAKFAST/LUNCH/DINNER)
- recipe_id (optional FK) OR custom_meal_name
- was_cooked, notes
- created_at, updated_at

## Implementation Phases

1. **Models** - Add enums and update/create models
2. **Schemas** - Add Pydantic validation schemas
3. **CRUD** - Create crud_recipes.py and crud_meal_plans.py
4. **Routes** - Create API endpoints and register routers
5. **Migration** - Generate and apply Alembic migration
6. **Testing** - Unit + integration tests (~30-40 new tests)
7. **Verification** - Test with frontend, verify all operations work

## Key Decisions

- Use `JSON` type for ingredients and tags (PostgreSQL JSONB)
- `ondelete="SET NULL"` for recipe FK (preserve meal plans if recipe deleted)
- MealPlan queries require date range (performance guard)
- Nested Recipe object in MealPlan responses

## Estimated Test Count

- Unit tests: ~10 (5 recipes + 5 meal plans)
- Integration tests: ~20 (10 recipes + 10 meal plans)
- Total new tests: ~30

## Dependencies

- Frontend is complete and waiting
- No new Python packages required
- Follows existing codebase patterns exactly
