# UI Improvements Plan

Based on comprehensive UX/UI review of Lists and Responsibilities pages.

## Overview

**Branch**: `ui-improvements`
**Review Date**: February 2, 2026
**Scope**: Lists page, Responsibilities page (daily view, edit view)
**Viewports Tested**: 375px (mobile), 768px (tablet), 1440px (desktop)

---

## Phase 1: Critical Accessibility Fixes (Week 1) ✅ COMPLETE

### 1.1 Add Keyboard Focus Indicators
- [x] Add `focus-visible:ring-2 focus-visible:ring-terracotta-500 focus-visible:ring-offset-2` to all interactive elements
- [x] **Files**: `ListPanel.jsx`, `TaskItem.jsx`, `ResponsibilityCard.jsx`, `AddButton.jsx`
- [x] Ensure tab order is logical throughout both pages
- [x] Add `tabIndex={0}` and keyboard event handlers where missing

### 1.2 Add ARIA Labels to Unlabeled Elements
- [x] Color picker buttons in `ListPanel.jsx` - add `aria-label="Select [color] color"` with specific color names
- [x] FAB in `AddButton.jsx` - already had `aria-label="Add new task"` ✓
- [x] Date navigation arrows on Responsibilities page - add `aria-label="Previous day"` / `aria-label="Next day"`
- [x] Category filter buttons - added `aria-pressed` state and group role

### 1.3 Replace `window.confirm()` with Modal
- [x] Use existing `ConfirmDialog` component for list deletion in `ListPanel.jsx`
- [x] Maintain consistent modal pattern throughout app

### 1.4 Add Title Attributes to Truncated Text
- [x] Add `title={list.name}` to truncated list names in sidebar
- [x] Add `title` to mobile list selector button when truncated

---

## Phase 2: Usability Improvements (Week 2-3) ✅ COMPLETE

### 2.1 Dynamic Page Titles ✅ COMPLETE
- [x] Update `document.title` based on current route/context
- [x] Pattern: `[Context] - Family Planner`
  - Dashboard: "Dashboard - Family Planner"
  - Lists: "[List Name] - Family Planner"
  - Responsibilities: "Responsibilities - Family Planner"
  - Settings: "Settings - Family Planner"
- [x] Created `usePageTitle` custom hook in `src/hooks/usePageTitle.js`
- [x] Updated `index.html` default title to "Family Planner"

### 2.2 Enhanced Empty States ✅ COMPLETE
- [x] Created reusable `EmptyState` component with:
  - Configurable icon/illustration
  - Heading and description text
  - Optional CTA button
- [x] Created pre-configured variants:
  - `EmptyListsState` - For no lists
  - `EmptyTasksState` - For no tasks in list
  - `EmptyResponsibilitiesState` - For no responsibilities
  - `EmptyDailyViewState` - For no scheduled items for today
- [x] Applied to TaskListView, ResponsibilitiesPage, ScheduleView

### 2.3 Category Filter Visual Feedback ✅ COMPLETE
- [x] Add visual distinction for active/selected category filters
- [x] Show item count per category: `[Morning (2)]`
- [x] Toggle button pattern with `aria-pressed` state
- [x] Added "All" option with total count

### 2.4 Hide Zero Task Counts ✅ COMPLETE
- [x] Hide task count badge when count is 0
- [x] Reduces visual noise in sidebar

---

## Phase 3: Enhanced Accessibility (Week 3-4) ✅ COMPLETE

### 3.1 Progress Bar ARIA Attributes ✅ COMPLETE
- [x] Add to responsibility progress bars in `ScheduleView`:
  - `role="progressbar"`
  - `aria-valuenow={completedCount}`
  - `aria-valuemin={0}`
  - `aria-valuemax={totalCount}`
  - `aria-label="[Member name]'s progress: [X] of [Y] tasks completed"`
- [x] Added `aria-hidden="true"` to visual count text (redundant with aria-label)

### 3.2 Form Validation Improvements ✅ COMPLETE
- [x] Add inline validation feedback to New List modal
- [x] Show error messages near form fields with icon
- [x] Add `aria-invalid` and `aria-describedby` for error states
- [x] Validate: required, min 2 chars, max 50 chars
- [x] Clear error on user input, error border styling

### 3.3 Touch Accessibility for Action Buttons ✅ COMPLETE
- [x] Added `sm:group-focus-within:opacity-100` to show buttons when focused via keyboard
- [x] Buttons already visible on mobile (`opacity-100`)
- [x] Updated focus-visible ring styles for consistency
- [x] Enhanced aria-labels to include item title (e.g., "Edit task: Task Name")
- [x] Updated tests to use regex patterns for new label format

---

## Phase 4: Mobile Enhancements (Month 2) ✅ COMPLETE

### 4.1 Swipe Gestures ✅ COMPLETE
- [x] Created `SwipeableItem` component using `react-swipeable` library
- [x] Swipe-to-delete for task items (swipe left reveals red Delete button)
- [x] Swipe-to-complete for responsibilities (swipe left reveals green Done button)
- [x] Auto-trigger action when swiping past threshold
- [x] Tap revealed action button or swipe further to confirm
- [x] Desktop: swipe UI hidden (uses hover buttons instead)

### 4.2 Tooltip Component ✅ COMPLETE
- [x] Created `Tooltip` component with:
  - Hover to show on desktop (with configurable delay)
  - Long-press to show on mobile
  - Smart positioning (keeps tooltip in viewport)
  - Arrow indicator pointing to trigger element
- [x] Created `TruncatedText` component:
  - Auto-detects if text is truncated
  - Only shows tooltip when needed
- [x] Applied to list names in sidebar
- [x] Added CSS animations for smooth fade-in

---

## Implementation Notes

### Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/ListPanel.jsx` | Focus styles, aria-labels for colors, title attrs, ConfirmDialog |
| `frontend/src/components/AddButton.jsx` | Context-aware aria-label |
| `frontend/src/components/TaskItem.jsx` | Focus styles, touch accessibility |
| `frontend/src/components/ResponsibilityCard.jsx` | Focus styles |
| `frontend/src/pages/Responsibilities.jsx` | Date nav aria-labels, filter feedback, progress bar ARIA |
| `frontend/src/pages/Lists.jsx` | Dynamic page title |
| `frontend/src/App.jsx` or layout | Page title hook integration |

### New Components Created

- [x] `EmptyState.jsx` - Reusable empty state with illustration, text, and CTA
- [x] `usePageTitle.js` - Custom hook for dynamic page titles
- [x] `Tooltip.jsx` - Tooltip with TruncatedText for enhanced truncated text display
- [x] `SwipeableItem.jsx` - Swipe-to-action wrapper for mobile

### CSS/Styling Additions

```css
/* Focus visible utility - add to index.css if not using Tailwind classes */
.focus-ring {
  @apply focus-visible:ring-2 focus-visible:ring-terracotta-500 focus-visible:ring-offset-2 focus-visible:outline-none;
}
```

---

## Testing Checklist

### Accessibility Testing
- [ ] Keyboard-only navigation through entire app
- [ ] Screen reader testing (VoiceOver on Mac)
- [ ] Focus visible on all interactive elements
- [ ] ARIA labels announced correctly
- [ ] Color contrast passes WCAG AA (4.5:1)

### Responsive Testing
- [ ] 375px (iPhone SE)
- [ ] 390px (iPhone 14)
- [ ] 768px (iPad)
- [ ] 1024px (iPad landscape)
- [ ] 1440px (Desktop)

### Functional Testing
- [ ] All existing functionality still works
- [ ] Empty states display correctly
- [ ] Page titles update on navigation
- [ ] Filter states persist and display correctly

---

## Success Metrics

- All interactive elements have visible focus indicators
- Screen reader can navigate and understand all UI elements
- Empty states provide clear guidance to new users
- Browser tab shows meaningful page title
- Zero accessibility errors in axe DevTools audit

---

## References

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [HeadlessUI Documentation](https://headlessui.com/)
- [Tailwind CSS Focus Ring](https://tailwindcss.com/docs/ring-width)
