---
plan_kind: "feature"
registry_key: "plan:mealboard"
updated_at: "2026-09-09T22:03:40Z"
---
# Mealboard Backend Implementation Plan

## Overview

Implement backend API support for the Mealboard feature, enabling recipe management and weekly meal planning. The frontend is complete and awaiting these endpoints.

## Current State

- Frontend components complete (see `mealboard-plan-frontend-summary.md`)
- Existing `Recipe` model in `models.py` is a stub (missing fields)
- No `MealPlan` model exists
- No CRUD operations or routes for recipes/meal-plans

## Target State

Full CRUD API for:
- `/recipes` - Recipe management
- `/meal-plans` - Meal planning by date/category

---

## Phase 1: Database Models

### 1.1 Update `app/models.py`

**Add MealCategory enum:**
```python
class MealCategory(PyEnum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
```

**Replace existing Recipe model with:**
```python
class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    ingredients = Column(JSON, nullable=True)  # Array of {name, quantity, unit, category}
    instructions = Column(Text, nullable=False)
    prep_time_minutes = Column(Integer, nullable=True)
    cook_time_minutes = Column(Integer, nullable=True)
    servings = Column(Integer, default=4)
    image_url = Column(String, nullable=True)
    is_favorite = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)  # Array of strings
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    meal_plans = relationship("MealPlan", back_populates="recipe")
```

**Add MealPlan model:**
```python
class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    category = Column(SQLEnum(MealCategory), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    custom_meal_name = Column(String, nullable=True)
    was_cooked = Column(Boolean, default=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    recipe = relationship("Recipe", back_populates="meal_plans")
```

**Imports to add:**
- `JSON` from sqlalchemy
- `Text` from sqlalchemy (for instructions field)

---

## Phase 2: Pydantic Schemas

### 2.1 Add to `app/schemas.py`

**MealCategory enum:**
```python
class MealCategory(str, Enum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
```

**Ingredient schema (nested in Recipe):**
```python
class Ingredient(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    category: str = "Other"
```

**Recipe schemas:**
```python
class RecipeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    ingredients: Optional[List[Ingredient]] = None
    instructions: str = Field(..., min_length=1)
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    servings: int = Field(default=4, ge=1)
    image_url: Optional[str] = None
    is_favorite: bool = False
    tags: Optional[List[str]] = None

class RecipeCreate(RecipeBase):
    pass

class RecipeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    ingredients: Optional[List[Ingredient]] = None
    instructions: Optional[str] = Field(None, min_length=1)
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    cook_time_minutes: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1)
    image_url: Optional[str] = None
    is_favorite: Optional[bool] = None
    tags: Optional[List[str]] = None

class Recipe(RecipeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
```

**MealPlan schemas:**
```python
class MealPlanBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    category: MealCategory
    recipe_id: Optional[int] = Field(None, ge=1)
    custom_meal_name: Optional[str] = Field(None, max_length=200)
    was_cooked: bool = False
    notes: Optional[str] = Field(None, max_length=500)

class MealPlanCreate(MealPlanBase):
    pass

class MealPlanUpdate(BaseModel):
    date: Optional[date] = None
    category: Optional[MealCategory] = None
    recipe_id: Optional[int] = Field(None, ge=1)
    custom_meal_name: Optional[str] = Field(None, max_length=200)
    was_cooked: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)

class MealPlan(MealPlanBase):
    id: int
    recipe: Optional[Recipe] = None  # Nested recipe when available
    created_at: datetime
    updated_at: Optional[datetime] = None
```

---

## Phase 3: CRUD Operations

### 3.1 Create `app/crud_recipes.py`

```python
async def get_recipes(db: AsyncSession, skip: int = 0, limit: int = 100, favorites_only: bool = False):
    """Get all recipes, optionally filtered by favorites."""
    stmt = select(models.Recipe)
    if favorites_only:
        stmt = stmt.where(models.Recipe.is_favorite == True)
    stmt = stmt.offset(skip).limit(limit).order_by(models.Recipe.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_recipe(db: AsyncSession, recipe_id: int):
    """Get a single recipe by ID."""
    stmt = select(models.Recipe).where(models.Recipe.id == recipe_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_recipe(db: AsyncSession, recipe: schemas.RecipeCreate):
    """Create a new recipe."""
    db_recipe = models.Recipe(**recipe.model_dump())
    db.add(db_recipe)
    await db.commit()
    await db.refresh(db_recipe)
    return db_recipe

async def update_recipe(db: AsyncSession, recipe_id: int, recipe: schemas.RecipeUpdate):
    """Update an existing recipe."""
    stmt = (
        update(models.Recipe)
        .where(models.Recipe.id == recipe_id)
        .values(**recipe.model_dump(exclude_unset=True))
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    await db.commit()
    return await get_recipe(db, recipe_id)

async def delete_recipe(db: AsyncSession, recipe_id: int):
    """Delete a recipe."""
    recipe = await get_recipe(db, recipe_id)
    if recipe:
        await db.delete(recipe)
        await db.commit()
    return recipe
```

### 3.2 Create `app/crud_meal_plans.py`

```python
async def get_meal_plans(db: AsyncSession, start_date: date, end_date: date):
    """Get meal plans for a date range."""
    stmt = (
        select(models.MealPlan)
        .options(selectinload(models.MealPlan.recipe))
        .where(models.MealPlan.date >= start_date)
        .where(models.MealPlan.date <= end_date)
        .order_by(models.MealPlan.date, models.MealPlan.category)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_meal_plan(db: AsyncSession, meal_plan_id: int):
    """Get a single meal plan by ID."""
    stmt = (
        select(models.MealPlan)
        .options(selectinload(models.MealPlan.recipe))
        .where(models.MealPlan.id == meal_plan_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_meal_plan(db: AsyncSession, meal_plan: schemas.MealPlanCreate):
    """Create a new meal plan entry."""
    db_meal_plan = models.MealPlan(**meal_plan.model_dump())
    db.add(db_meal_plan)
    await db.commit()
    return await get_meal_plan(db, db_meal_plan.id)

async def update_meal_plan(db: AsyncSession, meal_plan_id: int, meal_plan: schemas.MealPlanUpdate):
    """Update an existing meal plan."""
    stmt = (
        update(models.MealPlan)
        .where(models.MealPlan.id == meal_plan_id)
        .values(**meal_plan.model_dump(exclude_unset=True))
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    await db.commit()
    return await get_meal_plan(db, meal_plan_id)

async def delete_meal_plan(db: AsyncSession, meal_plan_id: int):
    """Delete a meal plan entry."""
    meal_plan = await get_meal_plan(db, meal_plan_id)
    if meal_plan:
        await db.delete(meal_plan)
        await db.commit()
    return meal_plan
```

---

## Phase 4: API Routes

### 4.1 Create `app/routes/recipes.py`

```python
router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[schemas.Recipe])
async def get_recipes(
    skip: int = 0,
    limit: int = 100,
    favorites_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all recipes, optionally filtered to favorites."""

@router.get("/{recipe_id}", response_model=schemas.Recipe)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single recipe by ID."""

@router.post("/", response_model=schemas.Recipe, status_code=201)
async def create_recipe(recipe: schemas.RecipeCreate, db: AsyncSession = Depends(get_db)):
    """Create a new recipe."""

@router.patch("/{recipe_id}", response_model=schemas.Recipe)
async def update_recipe(
    recipe_id: int,
    recipe_update: schemas.RecipeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing recipe."""

@router.delete("/{recipe_id}", response_model=schemas.Recipe)
async def delete_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a recipe."""
```

### 4.2 Create `app/routes/meal_plans.py`

```python
router = APIRouter(
    prefix="/meal-plans",
    tags=["meal-plans"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[schemas.MealPlan])
async def get_meal_plans(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
):
    """Get meal plans for a date range. Required: start_date, end_date."""

@router.get("/{meal_plan_id}", response_model=schemas.MealPlan)
async def get_meal_plan(meal_plan_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single meal plan by ID."""

@router.post("/", response_model=schemas.MealPlan, status_code=201)
async def create_meal_plan(
    meal_plan: schemas.MealPlanCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new meal plan entry."""

@router.patch("/{meal_plan_id}", response_model=schemas.MealPlan)
async def update_meal_plan(
    meal_plan_id: int,
    meal_plan_update: schemas.MealPlanUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a meal plan (e.g., mark as cooked, add notes)."""

@router.delete("/{meal_plan_id}", response_model=schemas.MealPlan)
async def delete_meal_plan(meal_plan_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a meal plan entry."""
```

### 4.3 Register routers in `app/main.py`

```python
from .routes import recipes, meal_plans

app.include_router(recipes.router)
app.include_router(meal_plans.router)
```

---

## Phase 5: Database Migration

### 5.1 Create Alembic migration

```bash
cd backend
alembic revision --autogenerate -m "add_recipe_and_meal_plan_tables"
alembic upgrade head
```

**Expected changes:**
- Drop/recreate `recipes` table with new schema
- Create `meal_plans` table
- Add foreign key constraint from `meal_plans.recipe_id` to `recipes.id`

---

## Phase 6: Testing

### 6.1 Unit Tests

**Create `tests/unit/test_crud_recipes.py`:**
- `test_create_recipe`
- `test_get_recipe_found`
- `test_get_recipe_not_found`
- `test_update_recipe`
- `test_delete_recipe`

**Create `tests/unit/test_crud_meal_plans.py`:**
- `test_create_meal_plan_with_recipe`
- `test_create_meal_plan_custom_meal`
- `test_get_meal_plans_by_date_range`
- `test_update_meal_plan_was_cooked`
- `test_delete_meal_plan`

### 6.2 Integration Tests

**Create `tests/integration/test_recipes_api.py`:**
- `TestGetRecipes`: empty list, returns all, filters by favorites
- `TestGetRecipe`: found, 404
- `TestCreateRecipe`: with required fields, with all fields, validation errors
- `TestUpdateRecipe`: partial update, 404
- `TestDeleteRecipe`: success, 404

**Create `tests/integration/test_meal_plans_api.py`:**
- `TestGetMealPlans`: requires date params, returns filtered by range
- `TestGetMealPlan`: found with recipe nested, 404
- `TestCreateMealPlan`: with recipe_id, with custom_meal_name
- `TestUpdateMealPlan`: toggle was_cooked, update notes
- `TestDeleteMealPlan`: success, 404

### 6.3 Test Fixtures

**Add to `tests/conftest.py`:**
```python
@pytest.fixture
def sample_recipe_data():
    return {
        "name": "Honey Garlic Chicken",
        "description": "Quick and easy dinner",
        "ingredients": [
            {"name": "Chicken breast", "quantity": 2, "unit": "lb", "category": "Protein"},
            {"name": "Honey", "quantity": 0.25, "unit": "cups", "category": "Pantry"},
        ],
        "instructions": "1. Season chicken. 2. Cook in pan. 3. Add sauce.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 25,
        "servings": 4,
        "is_favorite": True,
        "tags": ["chicken", "quick", "dinner"],
    }

@pytest.fixture
def sample_meal_plan_data():
    return {
        "date": date.today().isoformat(),
        "category": "DINNER",
        "recipe_id": None,
        "custom_meal_name": None,
        "was_cooked": False,
        "notes": None,
    }
```

**Add to `tests/integration/conftest.py`:**
```python
@pytest_asyncio.fixture
async def test_recipe(db_session):
    """Create a test recipe in the database."""
    from app.models import Recipe
    recipe = Recipe(
        name="Test Recipe",
        description="A test recipe",
        ingredients=[{"name": "Test ingredient", "quantity": 1, "unit": "cups", "category": "Pantry"}],
        instructions="Test instructions",
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=4,
        is_favorite=False,
        tags=["test"],
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)
    return recipe

@pytest_asyncio.fixture
async def test_meal_plan(db_session, test_recipe):
    """Create a test meal plan in the database."""
    from app.models import MealPlan
    meal_plan = MealPlan(
        date=date.today(),
        category="DINNER",
        recipe_id=test_recipe.id,
        was_cooked=False,
    )
    db_session.add(meal_plan)
    await db_session.commit()
    await db_session.refresh(meal_plan)
    return meal_plan
```

---

## Implementation Checklist

### Phase 1: Models
- [x] Add `MealCategory` enum to `models.py`
- [x] Update `Recipe` model with all fields
- [x] Add `MealPlan` model
- [x] Add required imports (JSON, Text)

### Phase 2: Schemas
- [x] Add `MealCategory` enum to `schemas.py`
- [x] Add `Ingredient` schema
- [x] Add `RecipeBase`, `RecipeCreate`, `RecipeUpdate`, `Recipe` schemas
- [x] Add `MealPlanBase`, `MealPlanCreate`, `MealPlanUpdate`, `MealPlan` schemas

### Phase 3: CRUD
- [x] Create `crud_recipes.py` with all operations
- [x] Create `crud_meal_plans.py` with all operations

### Phase 4: Routes
- [x] Create `routes/recipes.py` with all endpoints
- [x] Create `routes/meal_plans.py` with all endpoints
- [x] Register routers in `main.py`

### Phase 5: Migration
- [x] Tables already existed with correct schema
- [x] Updated FK constraint to add ON DELETE SET NULL
- [x] Added default values for is_favorite, servings, was_cooked

### Phase 6: Testing
- [x] Integration tests for `/recipes` API (15 tests)
- [x] Integration tests for `/meal-plans` API (18 tests)
- [x] Add test fixtures to conftest.py and integration/conftest.py
- [x] All 204 tests pass (33 new tests added)

### Phase 7: Verification
- [x] Run full test suite (`uv run pytest`) - 204 passed
- [x] Manual API testing - all endpoints work
- [ ] Verify all frontend operations work:
  - [ ] Create/edit/delete recipes
  - [ ] Add meals to calendar (recipe + custom)
  - [ ] Toggle was_cooked status
  - [ ] Filter recipes by favorites

---

## API Contract Reference

### Recipes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/recipes` | List all recipes |
| GET | `/recipes?favorites_only=true` | List favorite recipes |
| GET | `/recipes/{id}` | Get single recipe |
| POST | `/recipes` | Create recipe |
| PATCH | `/recipes/{id}` | Update recipe |
| DELETE | `/recipes/{id}` | Delete recipe |

### Meal Plans

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/meal-plans?start_date=&end_date=` | Get plans in date range |
| GET | `/meal-plans/{id}` | Get single plan |
| POST | `/meal-plans` | Create plan entry |
| PATCH | `/meal-plans/{id}` | Update plan (cooked, notes) |
| DELETE | `/meal-plans/{id}` | Delete plan entry |

---

## Notes

1. **JSON fields**: SQLAlchemy `JSON` type maps to PostgreSQL `JSONB` for efficient querying
2. **Cascade delete**: Using `ondelete="SET NULL"` for recipe FK so deleting a recipe doesn't delete meal plans
3. **Date filtering**: MealPlan queries require date range to avoid loading entire history
4. **Nested recipe**: MealPlan response includes nested Recipe object when available
5. **Existing Recipe table**: Will need to be dropped/recreated (data migration not needed as it's currently a stub)
