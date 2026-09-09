# Mealboard UI Improvements Plan

## Overview
Responsive UI improvements for the Mealboard feature including dark mode toggle relocation, layout refinements, and mobile-optimized controls.

---

## Changes Summary

### 1. Dark Mode Toggle - Move to Sidebar Bottom
**File:** `frontend/src/components/Sidebar.jsx`

- Remove fixed position wrapper (lines 66-69)
- Move `<DarkModeToggle />` inside `<aside>` with `mt-auto` to push to bottom
- Mobile (<640px) keeps toggle in Header.jsx (no change needed there)

```jsx
// Inside <aside>, after menuItems.map():
<div className="mt-auto pb-4">
  <DarkModeToggle />
</div>
```

---

### 2. Shopping List Min Height
**File:** `frontend/src/components/mealboard/MealPlannerRightPanel.jsx`

- Add `min-h-[25%]` to shopping list section container
- Add `overflow-y-auto` for scrolling when content exceeds space

---

### 3. Unified Header with Aligned Controls
**File:** `frontend/src/components/mealboard/MealPlannerView.jsx`

**Current structure (to remove):**
- Lines 150-163: Mobile nav (dropdown + panel toggle)
- Lines 165-182: Desktop header (title + week selector)
- Lines 184-191: Mobile week selector

**New structure:** Single unified header bar for all screen sizes:
- Left: MealboardNav dropdown
- Center: WeekSelector
- Right: Panel toggle (hidden on xl+)

Remove the desktop-only header with title/date since dropdown nav is now always visible.

---

### 4. Vertical Calendar Layout (<1200px)
**File:** `frontend/src/components/mealboard/MealPlannerView.jsx`

Change from horizontal scroll to vertical stack below 1200px:

**Option A - CSS class in index.css:**
```css
.meal-calendar {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
@media (min-width: 1200px) {
  .meal-calendar {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
  }
}
```

**Option B - Inline media query via state** (if CSS class approach is problematic)

Update day column classes to remove fixed width on vertical layout.

---

### 5. Compact Mode for Mobile (<620px)
**Files:**
- `frontend/src/components/mealboard/MealPlannerView.jsx`
- `frontend/src/components/mealboard/MealboardNav.jsx`
- `frontend/src/components/mealboard/WeekSelector.jsx`

Add `isCompactMode` state with resize listener (620px threshold):
```jsx
const [isCompactMode, setIsCompactMode] = useState(() => window.innerWidth < 620)
useEffect(() => {
  const handleResize = () => setIsCompactMode(window.innerWidth < 620)
  window.addEventListener('resize', handleResize)
  return () => window.removeEventListener('resize', handleResize)
}, [])
```

Pass `compact` prop to components:
- **MealboardNav:** Show icon + chevron only (hide text label)
- **WeekSelector:** Show prev/next buttons only (hide date range text)

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/Sidebar.jsx` | Move DarkModeToggle to bottom |
| `frontend/src/components/mealboard/MealPlannerView.jsx` | Unified header, vertical calendar, compact mode state |
| `frontend/src/components/mealboard/MealPlannerRightPanel.jsx` | Shopping list min-height |
| `frontend/src/components/mealboard/MealboardNav.jsx` | Add `compact` prop support |
| `frontend/src/components/mealboard/WeekSelector.jsx` | Add `compact` prop support |
| `frontend/src/index.css` | Add `.meal-calendar` responsive class |

---

## Implementation Order

1. **Sidebar toggle** - Simple, no dependencies
2. **Shopping list min-height** - Simple CSS
3. **Vertical calendar CSS** - Add to index.css
4. **Unified header** - Restructure MealPlannerView.jsx
5. **Compact mode** - Add state + update child components

---

## Verification

- [ ] Dark mode toggle at sidebar bottom (>=640px)
- [ ] Dark mode toggle in header (mobile <640px)
- [ ] Shopping list has ~25% minimum height in panel
- [ ] Panel toggle aligns with week selector on tablet/mobile
- [ ] No title header on tablet+ (>=640px)
- [ ] Calendar stacks vertically below 1200px
- [ ] Calendar shows 7-column grid at >=1200px
- [ ] Icon-only nav dropdown below 620px
- [ ] Icon-only week selector below 620px
- [ ] Rebuild Docker container and test at various breakpoints
