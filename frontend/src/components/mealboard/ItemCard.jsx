import { getRecipeGradient } from '../../constants/recipeGradients'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Category color map for food-item card stripe
const CATEGORY_COLORS = {
  fruit: 'bg-amber-300',
  vegetable: 'bg-green-300',
  protein: 'bg-red-300',
  dairy: 'bg-blue-300',
  grain: 'bg-amber-100',
  Other: 'bg-warm-sand',
}

const HEART_PATH = 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z'

// Pot SVG for recipe placeholder (ghosted utensil)
const POT_ICON = (
  <svg className="w-[22px] h-[22px] opacity-[0.16] dark:opacity-[0.10] text-text-muted dark:text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 11h18M5 11v6a3 3 0 003 3h8a3 3 0 003-3v-6M8 11V7a1 1 0 011-1h0a1 1 0 011 1v4M14 11V7a1 1 0 011-1h0a1 1 0 011 1v4M12 11V4" />
  </svg>
)

/**
 * Unified card for the Item model. Branches on `item.item_type`:
 *   - recipe: 16:9 image/gradient tile with floating heart + hover edit/delete
 *   - food_item: horizontal card with emoji + name + heart + right-side category stripe
 *     (redesigned per plan 20260415-164719 Chunk 3; replaces the pill layout)
 */
export default function ItemCard({ item, index = 0, onClick, onEdit, onDelete, onToggleFavorite }) {
  if (item.item_type === 'food_item') {
    return <FoodItemCard item={item} onClick={onClick || onEdit} onToggleFavorite={onToggleFavorite} />
  }
  return <RecipeTile item={item} index={index} onClick={onClick} onEdit={onEdit} onDelete={onDelete} onToggleFavorite={onToggleFavorite} />
}

// ---------------------------------------------------------------------------
// Recipe variant — 16:9 tile, preserved from the legacy RecipeCard
// ---------------------------------------------------------------------------

function RecipeTile({ item, index, onClick, onEdit, onDelete, onToggleFavorite }) {
  const rd = item.recipe_detail || {}
  const totalTime = (rd.prep_time_minutes || 0) + (rd.cook_time_minutes || 0)
  const isDark = document.documentElement.classList.contains('dark')
  const gradient = getRecipeGradient(item.name, isDark)

  const animStyle = {
    animation: `recipe-card-enter 0.3s ease both`,
    animationDelay: `${Math.min(index * 40, 800)}ms`,
  }

  const imgSrc = rd.image_url
    ? (rd.image_url.startsWith('http') ? rd.image_url : `${API_BASE}${rd.image_url}`)
    : null

  return (
    <div
      className="
        group bg-card-bg dark:bg-gray-800
        border border-card-border dark:border-gray-700
        rounded-xl overflow-hidden cursor-pointer
        transition-[transform,box-shadow] duration-[220ms] ease-[cubic-bezier(0.2,0,0,1)]
        hover:translate-y-[-3px]
        hover:shadow-[0_8px_24px_rgba(61,56,51,0.07),0_2px_8px_rgba(61,56,51,0.03)]
        dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.28),0_2px_8px_rgba(0,0,0,0.12)]
      "
      style={animStyle}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      tabIndex={0}
      role="button"
    >
      <div className="relative aspect-video overflow-hidden">
        {imgSrc ? (
          <img src={imgSrc} alt={item.name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center" style={{ background: gradient }}>
            {POT_ICON}
          </div>
        )}

        {/* Floating heart */}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onToggleFavorite?.() }}
          className="absolute top-2 right-2 p-[3px] border-none bg-transparent cursor-pointer z-[2] transition-transform duration-150 hover:scale-[1.15]"
          style={{ filter: 'drop-shadow(0 1px 3px rgba(0,0,0,0.16))' }}
          aria-label={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path
              d={HEART_PATH}
              fill={item.is_favorite ? '#E06B6B' : 'transparent'}
              stroke={item.is_favorite ? '#E06B6B' : 'rgba(255,255,255,0.78)'}
              strokeWidth={item.is_favorite ? 1.5 : 2}
            />
          </svg>
        </button>

        {/* Hover edit/delete actions */}
        <div className="absolute top-2 left-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-[180ms] z-[2]">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onEdit?.() }}
            className="p-[3px] bg-transparent border-none cursor-pointer transition-transform duration-150 hover:scale-110"
            style={{ filter: 'drop-shadow(0 1px 3px rgba(0,0,0,0.16))' }}
            aria-label={`Edit ${item.name}`}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.78)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onDelete?.() }}
            className="p-[3px] bg-transparent border-none cursor-pointer transition-transform duration-150 hover:scale-110"
            style={{ filter: 'drop-shadow(0 1px 3px rgba(0,0,0,0.16))' }}
            aria-label={`Delete ${item.name}`}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.78)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
          </button>
        </div>
      </div>

      <div className="px-2 py-1.5">
        <div className="text-[13px] font-semibold text-text-primary dark:text-gray-100 leading-[1.3] line-clamp-2">
          {item.name}
        </div>
        <div className="flex items-center gap-1 mt-0.5 text-[11px] text-text-muted dark:text-gray-400">
          {totalTime > 0 && <span>⏲ {totalTime}m</span>}
          {totalTime > 0 && rd.servings && <span className="text-card-border dark:text-gray-600">·</span>}
          {rd.servings && <span>{rd.servings} serving{rd.servings > 1 ? 's' : ''}</span>}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Food item variant — card with right-side category stripe
// (redesigned per plan 20260415-164719 Chunk 3)
// ---------------------------------------------------------------------------

function FoodItemCard({ item, onClick, onToggleFavorite }) {
  const fid = item.food_item_detail || {}
  const categoryKey = fid.category || 'Other'
  const stripeClass = CATEGORY_COLORS[categoryKey] || 'bg-warm-sand'

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick?.()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      className="
        relative flex items-center gap-3 px-4 py-4
        rounded-xl border border-card-border dark:border-gray-700
        bg-card-bg dark:bg-gray-800
        hover:bg-warm-beige dark:hover:bg-gray-700
        hover:border-terracotta-200 dark:hover:border-blue-700
        hover:shadow-sm transition-all text-left cursor-pointer overflow-hidden
        focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 focus-visible:ring-offset-2
      "
      aria-label={`Edit ${item.name}`}
    >
      <span className="text-3xl flex-shrink-0 leading-none" aria-hidden="true">
        {item.icon_emoji || '🍽'}
      </span>
      <span className="flex-1 text-sm font-medium text-text-primary dark:text-gray-100 truncate">
        {item.name}
      </span>
      {/* Favorite heart */}
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onToggleFavorite?.() }}
        onKeyDown={(e) => e.stopPropagation()}
        className="flex-shrink-0 p-0.5 rounded hover:bg-black/5 dark:hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500"
        aria-label={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
        aria-pressed={item.is_favorite}
      >
        <svg
          className={`w-4 h-4 ${item.is_favorite ? 'text-terracotta-500 dark:text-blue-400' : 'text-text-muted dark:text-gray-500'}`}
          fill={item.is_favorite ? 'currentColor' : 'none'}
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d={HEART_PATH} />
        </svg>
      </button>
      {/* Category stripe — right edge, full card height */}
      <div
        className={`absolute right-0 top-0 bottom-0 w-1.5 rounded-r-xl ${stripeClass}`}
        title={categoryKey}
        aria-hidden="true"
      />
    </div>
  )
}
