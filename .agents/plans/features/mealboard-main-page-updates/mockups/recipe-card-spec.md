# Recipe Card — Design Spec

**Decision:** Option D (5 per row max, compact)
**Mockup:** `recipe-card-variations-v2.html` → Option D
**Date:** 2026-04-05

---

## Grid Layout

```css
grid-template-columns: repeat(5, 1fr);
gap: 0.875rem;
max-width: 1400px;
```

**Responsive breakpoints:**
- ≥1100px: 5 columns
- 800–1099px: 4 columns
- 500–799px: 3 columns
- 400–499px: 2 columns
- <400px: 1 column

**Partial-row behavior:** Cards in the last row stay at their column width — they do NOT stretch to fill the remaining space. This is handled naturally by the fixed `repeat(N, 1fr)` grid.

---

## Card Structure

```
┌─────────────────────────┐
│  [edit] [delete]    [♡] │  ← hover-reveal actions + floating heart
│                         │
│       (gradient)        │  ← 16:9 aspect ratio
│         [pot]           │  ← small muted utensil icon
│                         │
├─────────────────────────┤
│  Recipe Name            │  ← 13px/600, 2-line clamp
│  ⏲ 35m · 4 servings    │  ← 11px, muted
└─────────────────────────┘
```

### Dimensions
- Border radius: `12px`
- Border: `1px solid #E8E2D9` (card-border)
- Background: `#FFFDFB` (card-bg)

### Image/Placeholder Area
- Aspect ratio: `16:9`
- **With image:** `<img>` with `object-fit: cover`
- **Without image:** Gradient placeholder (see below)

### Content Area
- Padding: `0.4rem 0.5rem 0.5rem`
- Name: `13px`, weight `600`, color `text-primary`, `line-height: 1.3`, `-webkit-line-clamp: 2`
- Metadata: `11px`, color `text-muted`, `margin-top: 0.25rem`
  - Format: `⏲ {totalTime}m · {servings} serving(s)`
  - Separator dot in `card-border` color

---

## Gradient Placeholder (no-image state)

Hash the recipe name to select from 6 preset gradient pairs:

| Index | Name | CSS |
|-------|------|-----|
| 0 | Terracotta | `linear-gradient(145deg, #FEF3F0, #FAC9BD)` |
| 1 | Sage | `linear-gradient(145deg, #F4F7F4, #C8DBC9)` |
| 2 | Amber | `linear-gradient(145deg, #FFF8E7, #F5DEB3)` |
| 3 | Lavender | `linear-gradient(145deg, #F5F0FA, #DDD0EE)` |
| 4 | Teal | `linear-gradient(145deg, #F0F7F7, #C8E6E6)` |
| 5 | Mocha | `linear-gradient(145deg, #F5F0EB, #DDD0C4)` |

**Dark mode variants:**

| Index | CSS |
|-------|-----|
| 0 | `linear-gradient(145deg, #2A1A14, #3A2218)` |
| 1 | `linear-gradient(145deg, #1A221A, #223022)` |
| 2 | `linear-gradient(145deg, #2A2414, #3A3018)` |
| 3 | `linear-gradient(145deg, #221A2A, #2A2038)` |
| 4 | `linear-gradient(145deg, #1A2424, #203030)` |
| 5 | `linear-gradient(145deg, #241E18, #302820)` |

**Hash function:** Simple char-code hash of `recipe.name`, modulo 6.

**Utensil icon:** Pot SVG, `22px × 22px`, `opacity: 0.16` (light) / `0.10` (dark), color `text-muted`, centered in the gradient area.

**No letters. No emojis.** Just gradient + ghosted icon.

---

## Favorite Heart (Airbnb-style)

- Position: `absolute`, `top: 8px`, `right: 8px`
- No background circle or pill — SVG floats directly on the image/gradient
- `filter: drop-shadow(0 1px 3px rgba(0,0,0,0.16))`

| State | Fill | Stroke | Stroke width |
|-------|------|--------|--------------|
| Unfavorited | `transparent` | `rgba(255,255,255,0.78)` | 2 |
| Favorited | `#E06B6B` | `#E06B6B` | 1.5 |

- Hover: `transform: scale(1.15)`, `transition: 150ms ease`
- SVG size: `16px × 16px` (compact variant)
- Click: `stopPropagation()` (doesn't trigger card click)

---

## Hover Actions (Edit / Delete)

- Position: `absolute`, `top: 8px`, `left: 8px`
- Hidden by default (`opacity: 0`), fade in on card hover (`opacity: 1`, `transition: 180ms`)
- Same floating style as heart: no background, white SVG stroke with `drop-shadow`
- SVG size: `14px × 14px` (compact variant)
- Each button: `padding: 3px`, `hover: scale(1.1)`
- Click: `stopPropagation()`

---

## Hover / Interaction

- Card hover: `transform: translateY(-3px)`
- Shadow on hover: `0 8px 24px rgba(61,56,51,0.07), 0 2px 8px rgba(61,56,51,0.03)`
- Dark mode shadow: `0 8px 24px rgba(0,0,0,0.28), 0 2px 8px rgba(0,0,0,0.12)`
- Transition: `220ms cubic-bezier(0.2, 0, 0, 1)`
- Click card → opens `RecipeDetailDrawer` (existing component)
- `cursor: pointer`, `tabindex="0"`, `Enter` key triggers click

---

## Dark Mode

| Token | Light | Dark |
|-------|-------|------|
| card-bg | #FFFDFB | #1C1C1E |
| card-border | #E8E2D9 | #2C2C2E |
| text-primary | #3D3833 | #F0EDE8 |
| text-muted | #9A9287 | #6B645A |

Gradient placeholders use the dark variant table above. Heart and action icons remain white-stroked (visible on both light and dark gradients).
