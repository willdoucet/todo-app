/**
 * Shared icon renderer for the unified Item model.
 *
 * Renders, in priority order:
 *   1. `icon_url` → <img>
 *   2. `icon_emoji` → the emoji character
 *   3. fallback → a neutral placeholder glyph (shopping bag for food_item, pot for recipe)
 *
 * Consumed by ItemCard, ItemRow, ItemDetailDrawer, MealCard, and UndoToast.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function ItemIcon({ item, size = 32, className = '' }) {
  const px = `${size}px`
  const style = { width: px, height: px, minWidth: px, minHeight: px }

  if (item?.icon_url) {
    // Uploaded icons return as relative `/uploads/item-icons/...` paths from the
    // backend; Vite has no proxy, so bare-relative URLs would 404 against the SPA
    // origin (5173) instead of the API origin (8000). Mirror the IconSquare prefix.
    const src = item.icon_url.startsWith('http')
      ? item.icon_url
      : `${API_BASE}${item.icon_url}`
    return (
      <img
        src={src}
        alt=""
        aria-hidden="true"
        loading="lazy"
        decoding="async"
        style={style}
        className={`object-cover rounded-lg ${className}`}
      />
    )
  }

  if (item?.icon_emoji) {
    return (
      <span
        style={{ ...style, fontSize: size * 0.72, lineHeight: 1 }}
        className={`inline-flex items-center justify-center ${className}`}
        aria-hidden="true"
      >
        {item.icon_emoji}
      </span>
    )
  }

  // Placeholder — minimal neutral glyph.
  const isFood = item?.item_type === 'food_item'
  return (
    <span
      style={style}
      className={`inline-flex items-center justify-center rounded-lg bg-warm-sand text-text-muted ${className}`}
      aria-hidden="true"
    >
      <svg width={size * 0.52} height={size * 0.52} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
        {isFood ? (
          // Shopping bag
          <path strokeLinecap="round" strokeLinejoin="round" d="M16 10V7a4 4 0 10-8 0v3M4 10h16l-1 11H5L4 10z" />
        ) : (
          // Simple pot outline
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 10h12l-1 9H7l-1-9zm2-3a4 4 0 018 0" />
        )}
      </svg>
    </span>
  )
}
