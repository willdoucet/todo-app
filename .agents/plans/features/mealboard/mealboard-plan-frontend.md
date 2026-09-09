---
plan_kind: "feature"
registry_key: "plan:mealboard"
updated_at: "2026-09-09T22:03:40Z"
---
# Mealboard Frontend Implementation Plan

## Overview

Create a comprehensive meal planning feature at `/mealboard` that replaces the existing Recipes icon in the sidebar. The Mealboard will include a Recipe Catalog, Weekly Meal Planner, Shopping List integration, and a placeholder for AI-powered Recipe Finder.

**Design Reference:** The UI follows the template provided (Image #1) with a left navigation panel, central calendar view, and right sidebar for shopping list and quick add.

---

## Architecture

### Route Structure
```
/mealboard                    → redirects to /mealboard/planner
/mealboard/planner            → Weekly Meal Planner view (default)
/mealboard/shopping           → Shopping List view
/mealboard/recipes            → Recipe Catalog view
/mealboard/finder             → Recipe Finder (placeholder)
```

### Component Hierarchy
```
MealboardPage.jsx             # Layout wrapper with responsive navigation
├── MealboardNav.jsx          # Left panel (>=1200px) / dropdown (<1200px)
├── MealPlannerView.jsx       # Weekly calendar view
│   ├── WeekSelector.jsx      # Date navigation with week picker
│   ├── MealDayColumn.jsx     # Single day column with meal slots
│   ├── MealCard.jsx          # Individual meal card (recipe or custom)
│   ├── AddMealModal.jsx      # Modal to add recipe to meal plan
│   └── MealPlannerRightPanel.jsx  # Shopping list compact + Quick Add
├── ShoppingListView.jsx      # Full shopping list management
│   └── ShoppingListLinker.jsx  # Link existing list component
├── RecipesView.jsx           # Recipe catalog
│   ├── RecipeCard.jsx        # Recipe display card
│   ├── RecipeFilters.jsx     # Filter/sort controls
│   └── RecipeFormModal.jsx   # Create/edit recipe form
└── RecipeFinderView.jsx      # Placeholder component
```

### State Management
- Local component state for UI interactions
- API data fetched via Axios (following existing patterns)
- Optional: Introduce React Query for meal plan data caching

---

## Implementation Tasks

### Phase 1: Foundation & Navigation

#### 1.1 Update Sidebar
- [ ] Replace "Recipes" icon with "Mealboard" icon in `Sidebar.jsx`
- [ ] Update route from `/recipes` to `/mealboard`
- [ ] Use appropriate icon (calendar with food or similar)

#### 1.2 Create Mealboard Layout
- [ ] Create `MealboardPage.jsx` - main layout wrapper
- [ ] Implement responsive layout:
  - `>=1200px (xl:)`: Three-column layout (left nav, main content, right panel)
  - `<1200px`: Single column with dropdown navigation
- [ ] Add route definitions in `App.jsx`

#### 1.3 Create MealboardNav Component
- [ ] Create `MealboardNav.jsx`
- [ ] Menu items: "Meal Planner", "Shopping List", "Recipes", "Recipe Finder"
- [ ] Desktop (>=1200px): Fixed left panel, full height, similar to Image #1
- [ ] Mobile (<1200px): Compact dropdown menu replacing header title
- [ ] Active state styling matching existing terracotta/peach theme
- [ ] "Recipe Finder" item shows as disabled/placeholder

---

### Phase 2: Meal Planner View

#### 2.1 Week Selector Component
- [ ] Create `WeekSelector.jsx`
- [ ] Display: Current date, week range (e.g., "Jan 20 - 26")
- [ ] Previous/Next week navigation arrows
- [ ] Calculate week boundaries (Monday - Sunday)
- [ ] URL parameter for selected week (`?week=2025-01-20`)

#### 2.2 Meal Planner Header
- [ ] Page title: "What's cooking this week?" (or configurable)
- [ ] Current date display (e.g., "Monday, January 20")
- [ ] Visible at >=1200px
- [ ] At <1200px: Replace with MealboardNav dropdown

#### 2.3 Weekly Calendar Grid
- [ ] Create `MealPlannerView.jsx`
- [ ] Seven-day horizontal grid (Mon-Sun)
- [ ] Desktop (>=1200px): Horizontal layout per Image #1
- [ ] Mobile (<1200px): Single column, vertically stacked
- [ ] Default to current day on mobile open

#### 2.4 Day Column Component
- [ ] Create `MealDayColumn.jsx`
- [ ] Display: Day name, date number
- [ ] Highlight current day (terracotta accent)
- [ ] Three meal slots: Breakfast, Lunch, Dinner
- [ ] "Add meal" placeholder cards for empty slots

#### 2.5 Meal Card Component
- [ ] Create `MealCard.jsx`
- [ ] Display: Meal category label, recipe/meal name
- [ ] Show cook time if from recipe
- [ ] Show "Favorite" badge if recipe is favorited
- [ ] "Was Cooked" toggle (checkbox or button)
- [ ] Visual indicator for cooked vs planned
- [ ] Click to view recipe details or edit

#### 2.6 Add Meal Modal
- [ ] Create `AddMealModal.jsx`
- [ ] Recipe search/select from catalog
- [ ] Option to add custom meal name (not from recipe)
- [ ] Category selection (Breakfast, Lunch, Dinner)
- [ ] Notes field
- [ ] Save meal plan entry

#### 2.7 Meal Planner Right Panel
- [ ] Create `MealPlannerRightPanel.jsx`
- [ ] **Shopping List Compact View:**
  - Display linked shopping list items grouped by category
  - Checkbox to mark items
  - "View all" link to Shopping List view
  - Prompt to link list if none exists
- [ ] **Quick Add Section:**
  - Display favorited recipes sorted by times cooked, then alphabetically
  - Recipe card with image, name, cook time
  - Click to add to selected day/meal slot
  - "Browse" link to full Recipes view
  - Search field for finding recipes
- [ ] Desktop (>=1200px): Fixed right panel
- [ ] Mobile (<1200px): Hidden, toggleable via button (FAB or header button)

#### 2.8 Progress Summary
- [ ] Weekly progress bar (e.g., "3 of 7 days planned")
- [ ] Summary text (e.g., "3 dinners planned, 4 to go")
- [ ] Positioned below calendar grid per Image #1

---

### Phase 3: Shopping List View

#### 3.1 Shopping List View Component
- [ ] Create `ShoppingListView.jsx`
- [ ] Display full linked shopping list
- [ ] Group items by category (Produce, Protein, Pantry, etc.)

#### 3.2 List Linking
- [ ] Create `ShoppingListLinker.jsx`
- [ ] Dropdown to select from existing lists (`/lists` endpoint)
- [ ] Store linked list ID in localStorage or user preferences
- [ ] Prompt shown when no list is linked

#### 3.3 List Item Management
- [ ] Add new items to list (name, quantity, category)
- [ ] Edit existing items inline or via modal
- [ ] Delete items with confirmation
- [ ] Toggle checked/unchecked state
- [ ] Reuse existing list item patterns from `ListsPage.jsx`

---

### Phase 4: Recipes View

#### 4.1 Recipe Catalog View
- [ ] Create `RecipesView.jsx`
- [ ] Grid/list view of all recipes
- [ ] Recipe card display with:
  - Image (or placeholder)
  - Name
  - Cook time
  - Favorite star icon
  - Tags (optional display)

#### 4.2 Recipe Filters & Sorting
- [ ] Create `RecipeFilters.jsx`
- [ ] Filter: Is Favorite (Yes/No/All)
- [ ] Sort options:
  - Times cooked (most to least, least to most)
  - Alphabetically (A-Z, Z-A)
  - Recently added
- [ ] Clear filters button
- [ ] Persist filter state in URL params

#### 4.3 Recipe Card Component
- [ ] Create `RecipeCard.jsx`
- [ ] Image with fallback placeholder
- [ ] Recipe name, description preview
- [ ] Cook time, prep time, servings
- [ ] Favorite star (clickable to toggle)
- [ ] Edit/Delete action buttons (hover reveal on desktop)
- [ ] Tags display

#### 4.4 Recipe Form Modal
- [ ] Create `RecipeFormModal.jsx`
- [ ] Fields based on backend schema:
  - **Name** (required, text)
  - **Description** (optional, textarea)
  - **Ingredients** (dynamic list):
    - Name (text)
    - Quantity (number)
    - Unit (select: cups, tbsp, tsp, oz, lb, g, kg, ml, L, pieces, etc.)
    - Category (select: Produce, Protein, Dairy, Pantry, Frozen, etc.)
  - **Instructions** (required, textarea with rich text support or numbered steps)
  - **Prep Time** (optional, number in minutes)
  - **Cook Time** (optional, number in minutes)
  - **Servings** (number, default 4)
  - **Image** (file upload using existing PhotoUpload pattern)
  - **Is Favorite** (toggle)
  - **Tags** (comma-separated or chip input)
- [ ] Validation: Name and Instructions required
- [ ] Create mode: POST to `/recipes`
- [ ] Edit mode: PATCH to `/recipes/{id}`

#### 4.5 Recipe Detail View (Optional Enhancement)
- [ ] Could be modal or dedicated route
- [ ] Full recipe display with all details
- [ ] "Add to Meal Plan" button
- [ ] "Add Ingredients to Shopping List" button

#### 4.6 Recipe CRUD Operations
- [ ] Edit recipe via modal
- [ ] Delete recipe with confirmation dialog
- [ ] Use existing `ConfirmDialog.jsx` pattern

---

### Phase 5: Recipe Finder Placeholder

#### 5.1 Placeholder View
- [ ] Create `RecipeFinderView.jsx`
- [ ] Display "Coming Soon" message
- [ ] Brief description of upcoming AI-powered feature
- [ ] Visual placeholder (illustration or icon)
- [ ] Optional: Email/notification signup for feature launch

---

### Phase 6: Responsive Refinements

#### 6.1 Breakpoint Summary
| Feature | <1200px (mobile/tablet) | >=1200px (desktop) |
|---------|-------------------------|-------------------|
| MealboardNav | Dropdown menu | Fixed left panel |
| Page Header | Compact with dropdown | Full title + date |
| Weekly Calendar | Single column, scroll | Horizontal 7-day grid |
| Right Panel | Hidden, toggle button | Fixed right panel |
| Default Day | Current day focused | Full week visible |

#### 6.2 Mobile-Specific Features
- [ ] Swipe gestures for day navigation (optional)
- [ ] Floating action button for quick add meal
- [ ] Collapsible meal categories per day
- [ ] Pull-to-refresh (optional)

#### 6.3 Desktop-Specific Features
- [ ] Drag-and-drop meals between days/slots
- [ ] Hover states for action buttons
- [ ] Keyboard navigation support

---

### Phase 7: Testing

#### 7.1 Unit Tests
- [ ] `MealboardNav.test.jsx` - navigation rendering and active states
- [ ] `WeekSelector.test.jsx` - date calculations, navigation
- [ ] `MealCard.test.jsx` - rendering, cooked toggle, click handlers
- [ ] `RecipeCard.test.jsx` - rendering, favorite toggle, actions
- [ ] `RecipeFormModal.test.jsx` - form validation, submission
- [ ] `ShoppingListLinker.test.jsx` - list selection, linking

#### 7.2 Integration Tests
- [ ] Mealboard navigation between views
- [ ] Add meal to plan flow
- [ ] Create/edit/delete recipe flow
- [ ] Link shopping list flow
- [ ] Filter and sort recipes

#### 7.3 MSW Mock Handlers
- [ ] `GET /recipes` - list all recipes
- [ ] `POST /recipes` - create recipe
- [ ] `PATCH /recipes/:id` - update recipe
- [ ] `DELETE /recipes/:id` - delete recipe
- [ ] `GET /meal-plans` - get meal plans for date range
- [ ] `POST /meal-plans` - create meal plan entry
- [ ] `PATCH /meal-plans/:id` - update meal plan (was_cooked, etc.)
- [ ] `DELETE /meal-plans/:id` - delete meal plan entry

---

### Phase 8: Documentation Updates

#### 8.1 Update CLAUDE.md
- [ ] Add Mealboard to project overview
- [ ] Document new routes
- [ ] Add component descriptions
- [ ] Update data model section with Recipe and MealPlan

---

## File Structure (New Files)

```
frontend/src/
├── pages/
│   └── MealboardPage.jsx           # Main mealboard layout
├── components/
│   └── mealboard/
│       ├── MealboardNav.jsx        # Left panel / dropdown nav
│       ├── MealPlannerView.jsx     # Weekly planner main view
│       ├── WeekSelector.jsx        # Week navigation
│       ├── MealDayColumn.jsx       # Single day column
│       ├── MealCard.jsx            # Meal display card
│       ├── AddMealModal.jsx        # Add meal to plan modal
│       ├── MealPlannerRightPanel.jsx # Shopping + Quick Add panel
│       ├── ShoppingListView.jsx    # Full shopping list view
│       ├── ShoppingListLinker.jsx  # List linking component
│       ├── RecipesView.jsx         # Recipe catalog view
│       ├── RecipeCard.jsx          # Recipe display card
│       ├── RecipeFilters.jsx       # Filter/sort controls
│       ├── RecipeFormModal.jsx     # Create/edit recipe form
│       └── RecipeFinderView.jsx    # Placeholder view
└── tests/
    └── components/
        └── mealboard/
            ├── MealboardNav.test.jsx
            ├── WeekSelector.test.jsx
            ├── MealCard.test.jsx
            ├── RecipeCard.test.jsx
            ├── RecipeFormModal.test.jsx
            └── ShoppingListLinker.test.jsx
```

---

## API Endpoints (Frontend Consumption)

Based on backend models, expect these endpoints:

### Recipes
```
GET    /recipes                 # List all recipes
GET    /recipes/:id             # Get single recipe
POST   /recipes                 # Create recipe
PATCH  /recipes/:id             # Update recipe
DELETE /recipes/:id             # Delete recipe
```

### Meal Plans
```
GET    /meal-plans?start_date=&end_date=  # Get plans for date range
POST   /meal-plans              # Create meal plan entry
PATCH  /meal-plans/:id          # Update (was_cooked, notes, etc.)
DELETE /meal-plans/:id          # Delete plan entry
```

### Existing (reused)
```
GET    /lists                   # Get all lists (for linking)
GET    /tasks?list_id=          # Get list items
POST   /tasks                   # Add item to linked list
PATCH  /tasks/:id               # Update list item
DELETE /tasks/:id               # Delete list item
```

---

## Design Tokens (Extending Existing Theme)

```css
/* Mealboard-specific colors (suggestion) */
--color-meal-breakfast: #F7E4B4;  /* Warm yellow */
--color-meal-lunch: #E4F0E6;      /* Light sage */
--color-meal-dinner: #FCE8E4;     /* Light peach */
--color-cooked: #5D8A61;          /* Sage green checkmark */
```

---

## Dependencies

### Existing (No New Installs Needed)
- `@headlessui/react` - Modals, transitions
- `@heroicons/react` - Icons
- `axios` - API calls
- `react-router-dom` - Routing

### Optional Additions
- `date-fns` - Date manipulation (if not using native Date)
- `react-beautiful-dnd` - Drag and drop (if implementing meal drag)

---

## Risk Considerations

1. **Performance**: Loading full recipe catalog - implement pagination if >100 recipes
2. **State Sync**: Meal plan changes should reflect immediately in UI
3. **Mobile UX**: Weekly view on small screens needs careful attention
4. **List Linking**: Edge case when linked list is deleted
5. **Image Uploads**: Ensure existing PhotoUpload pattern handles recipe images

---

## Success Criteria

- [ ] Mealboard accessible from sidebar
- [ ] All four views navigable (Planner, Shopping, Recipes, Finder placeholder)
- [ ] Meals can be added to weekly plan
- [ ] Meals can be marked as cooked
- [ ] Recipes can be created, edited, deleted
- [ ] Recipes can be favorited
- [ ] Shopping list can be linked and viewed
- [ ] Responsive layout works at all breakpoints
- [ ] Dark mode fully supported
- [ ] All new components have tests
- [ ] Existing tests still pass

---

## Implementation Order (Recommended)

1. **Phase 1**: Foundation & Navigation (enables access to feature)
2. **Phase 4**: Recipes View (core functionality, no dependencies)
3. **Phase 2**: Meal Planner (depends on recipes existing)
4. **Phase 3**: Shopping List (simpler view, reuses existing patterns)
5. **Phase 5**: Recipe Finder Placeholder (trivial)
6. **Phase 6**: Responsive Refinements (polish)
7. **Phase 7**: Testing (throughout, but final pass here)
8. **Phase 8**: Documentation (finalize)
