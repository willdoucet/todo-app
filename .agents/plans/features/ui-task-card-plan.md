# TaskItem Component UI Improvements Plan

Based on comprehensive UX review of the task card component.

## Overview

**Component**: `frontend/src/components/TaskItem.jsx`
**Issue**: Icon misalignment and inconsistent sizing between status icons and action buttons
**Priority**: High (affects visual polish and perceived quality)

---

## Problem Analysis

### Current Structure
```
┌─────────────────────────────────────────────────────────────────┐
│ ○  Task Title                              ★    W   [Ed] [Del] │
│    Description                            16px 24px 32px 32px  │
│    📅 Due date                              ↑         ↑        │
│                                      Two separate containers   │
│                                      with different heights    │
└─────────────────────────────────────────────────────────────────┘
```

### Issues
1. **Vertical misalignment**: Star (16px), Avatar (24px), Buttons (32px) have different centers
2. **Two separate containers**: Status icons and action buttons in different flex containers
3. **Inconsistent tap targets**: Star/avatar are smaller than recommended 44px touch target
4. **Cross-component inconsistency**: TaskItem uses `items-start`, other components use `items-center`

---

## Implementation Plan

### Phase 1: Fix Icon Alignment (Priority 1)

#### 1.1 Merge Right-Side Containers
- [x] Combine status icons container and action buttons container into single flex container
- [x] Use `items-center` for vertical alignment
- [x] Maintain `gap-1` spacing between elements (matching action buttons)

#### 1.2 Standardize Icon Wrappers
- [x] Wrap star icon in 32x32 (`w-8 h-8`) centered container
- [x] Wrap AssignedIcon in 32x32 centered container
- [x] All elements now share same height, ensuring perfect center alignment

#### 1.3 Add Title Tooltip to Star
- [x] Add `title="Important"` to star wrapper for accessibility

**Files to modify:**
- `frontend/src/components/TaskItem.jsx` (lines 153-213)

---

### Phase 2: Enhance Overdue Indicator (Priority 2)

#### 2.1 Add Warning Icon
- [x] Add warning triangle icon before calendar icon for overdue tasks
- [x] Provides visual indicator beyond color alone (WCAG 1.4.1)

#### 2.2 Add Screen Reader Text
- [x] Add `<span className="sr-only">Overdue: </span>` for screen readers

---

### Phase 3: Cross-Component Consistency Audit (Priority 3)

#### 3.1 Document Current Sizes
| Component | Action Button Size | Alignment |
|-----------|-------------------|-----------|
| TaskItem | 32x32 | `items-start` → fix to unified |
| ResponsibilityCard | ~28px (p-1.5) | `items-center` |
| ListPanel ListItem | ~28px (p-1.5) | `items-center` |

#### 3.2 Future Consideration
- [ ] Consider standardizing all action buttons to 32x32 for consistency
- [ ] Or document intentional size differences in design system

---

## Code Changes

### TaskItem.jsx - Current Structure (lines 153-213)

```jsx
{/* Status icons - SEPARATE CONTAINER */}
<div className="flex items-center gap-2 flex-shrink-0">
  {task.important && (
    <svg className="w-4 h-4 text-amber-500" .../>  {/* 16px */}
  )}
  {task.family_member && (
    <AssignedIcon familyMember={task.family_member} />  {/* 24px */}
  )}
</div>

{/* Action buttons - SEPARATE CONTAINER */}
<div className="flex items-center gap-1 flex-shrink-0">
  <button className="w-8 h-8 ..." />  {/* 32px */}
  <button className="w-8 h-8 ..." />  {/* 32px */}
</div>
```

### TaskItem.jsx - New Structure

```jsx
{/* Right side: Status icons + Action buttons (UNIFIED CONTAINER) */}
<div className="flex items-center gap-1 flex-shrink-0">
  {/* Important star - in 32px wrapper */}
  {task.important && (
    <div
      className="w-8 h-8 flex items-center justify-center"
      title="Important"
    >
      <svg
        className="w-4 h-4 text-amber-500"
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </svg>
    </div>
  )}

  {/* Assigned to icon - in 32px wrapper */}
  {task.family_member && (
    <div className="w-8 h-8 flex items-center justify-center">
      <AssignedIcon familyMember={task.family_member} />
    </div>
  )}

  {/* Edit button - 32px */}
  <button
    onClick={onEdit}
    className="
      sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 opacity-100
      w-8 h-8 flex items-center justify-center
      text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
      hover:bg-gray-100 dark:hover:bg-gray-800
      rounded-lg transition-all duration-200
      focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500
    "
    aria-label={`Edit task: ${task.title}`}
  >
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  </button>

  {/* Delete button - 32px */}
  <button
    onClick={() => onDelete(task.id)}
    className="
      sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 opacity-100
      w-8 h-8 flex items-center justify-center
      text-gray-400 hover:text-red-500 dark:hover:text-red-400
      hover:bg-gray-100 dark:hover:bg-gray-800
      rounded-lg transition-all duration-200
      focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500
    "
    aria-label={`Delete task: ${task.title}`}
  >
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  </button>
</div>
```

---

## Visual Comparison

### Before (Misaligned)
```
┌─────────────────────────────────────────────────────────────────┐
│ ○  Send Email                              ★   W   [Edit][Del] │
│    Hawaii info                            ───────  ───────────  │
│    📅 Feb 2                               16+24px    32+32px    │
│                                           (gap-2)    (gap-1)    │
│                                              ↑          ↑       │
│                                         Different containers    │
│                                         Different heights       │
│                                         Centers off by ~4px     │
└─────────────────────────────────────────────────────────────────┘
```

### After (Aligned)
```
┌─────────────────────────────────────────────────────────────────┐
│ ○  Send Email                         [★]  [W]  [Edit] [Del]   │
│    Hawaii info                        ─────────────────────────  │
│    📅 Feb 2                           32   32    32     32 px   │
│                                           (gap-1 throughout)    │
│                                                  ↑              │
│                                         Single container        │
│                                         All 32px wrappers       │
│                                         Perfectly aligned       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Testing Checklist

### Visual Testing
- [x] Icons align vertically with action buttons
- [x] Spacing looks balanced (gap-1 = 4px between all elements)
- [x] Works with important star only
- [x] Works with assigned avatar only
- [x] Works with both star AND avatar
- [x] Works with neither (just action buttons)

### Functional Testing
- [x] Edit button click works
- [x] Delete button click works
- [x] Swipe-to-delete still works on mobile
- [x] Hover reveal works on desktop
- [x] Focus reveal works for keyboard users
- [x] Star tooltip shows on hover

### Responsive Testing
- [x] Mobile (375px): All elements visible, properly spaced
- [x] Tablet (768px): Hover reveal works
- [x] Desktop (1280px): Hover reveal works

### Accessibility Testing
- [x] Star has title tooltip ("Important")
- [x] Touch targets are 32x32 (improved from 16-24px)
- [x] Focus states visible on all buttons
- [x] Screen reader announces button labels correctly

### Regression Testing
- [x] Run `npm run test:run` - all 96 tests pass

---

## Success Criteria

1. All right-side icons and buttons align to the same vertical center
2. No visual "jitter" when hovering (action buttons don't shift other elements)
3. Touch targets improved to 32x32 for star and avatar
4. Star has tooltip for discoverability
5. All existing tests pass
6. Consistent spacing throughout right-side elements

---

## Estimated Scope

| Metric | Value |
|--------|-------|
| Files changed | 1 (`TaskItem.jsx`) |
| Lines changed | ~40 (restructure right-side section) |
| Risk level | Low (UI-only, no logic changes) |
| Testing required | Visual + run existing tests |

---

## Completion Status

**Status**: Complete
**Completed**: 2026-02-02

All Phase 1 and Phase 2 items implemented. All 96 tests passing. Phase 3 (cross-component consistency audit) deferred as future consideration.
