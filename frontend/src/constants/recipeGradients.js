/**
 * Gradient presets for recipe card placeholders.
 * Hash recipe name to pick a consistent gradient — gives visual variety
 * without actual images. Shared by RecipeCard and RecipeRow.
 */

const GRADIENT_PRESETS = [
  { name: 'Terracotta', light: ['#FEF3F0', '#FAC9BD'], dark: ['#2A1A14', '#3A2218'] },
  { name: 'Sage',       light: ['#F4F7F4', '#C8DBC9'], dark: ['#1A221A', '#223022'] },
  { name: 'Amber',      light: ['#FFF8E7', '#F5DEB3'], dark: ['#2A2414', '#3A3018'] },
  { name: 'Lavender',   light: ['#F5F0FA', '#DDD0EE'], dark: ['#221A2A', '#2A2038'] },
  { name: 'Teal',       light: ['#F0F7F7', '#C8E6E6'], dark: ['#1A2424', '#203030'] },
  { name: 'Mocha',      light: ['#F5F0EB', '#DDD0C4'], dark: ['#241E18', '#302820'] },
]

function hashName(name) {
  let h = 0
  for (let i = 0; i < name.length; i++) {
    h = ((h << 5) - h) + name.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h)
}

/**
 * Get a CSS linear-gradient string for a recipe's placeholder.
 * @param {string} name - Recipe name (hashed to pick gradient)
 * @param {boolean} isDark - Whether dark mode is active
 * @returns {string} CSS gradient value
 */
export function getRecipeGradient(name, isDark = false) {
  const idx = hashName(name || '') % GRADIENT_PRESETS.length
  const colors = isDark ? GRADIENT_PRESETS[idx].dark : GRADIENT_PRESETS[idx].light
  return `linear-gradient(145deg, ${colors[0]}, ${colors[1]})`
}

/**
 * Get the dot color for a recipe row (second/darker color of the gradient pair).
 * @param {string} name - Recipe name
 * @param {boolean} isDark - Whether dark mode is active
 * @returns {string} Hex color
 */
export function getRecipeDotColor(name, isDark = false) {
  const idx = hashName(name || '') % GRADIENT_PRESETS.length
  const colors = isDark ? GRADIENT_PRESETS[idx].dark : GRADIENT_PRESETS[idx].light
  return colors[1]
}

export { GRADIENT_PRESETS }
