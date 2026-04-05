/**
 * Food emoji auto-suggestion and curated picker.
 *
 * FOOD_EMOJI_LOOKUP maps ~100 common food names to emojis for auto-suggestion.
 * When a user types a food item name, the emoji field auto-fills from this lookup.
 *
 * CURATED_FOOD_EMOJIS groups ~50 food-relevant emojis for the override picker.
 */

// Food name → emoji lookup (lowercased keys)
export const FOOD_EMOJI_LOOKUP = {
  // Fruits
  apple: '🍎', banana: '🍌', orange: '🍊', strawberry: '🍓', grapes: '🍇',
  peach: '🍑', blueberries: '🫐', watermelon: '🍉', pineapple: '🍍', mango: '🥭',
  pear: '🍐', lemon: '🍋', cherry: '🍒', kiwi: '🥝', avocado: '🥑',
  coconut: '🥥', plum: '🟣', melon: '🍈',

  // Vegetables
  carrot: '🥕', tomato: '🍅', broccoli: '🥦', lettuce: '🥬', corn: '🌽',
  potato: '🥔', onion: '🧅', garlic: '🧄', cucumber: '🥒', pepper: '🫑',
  eggplant: '🍆', mushroom: '🍄', sweet_potato: '🍠', 'sweet potato': '🍠',
  'bell pepper': '🫑', spinach: '🥬', celery: '🥬',

  // Protein
  chicken: '🍗', beef: '🥩', 'ground beef': '🥩', steak: '🥩', pork: '🥓',
  bacon: '🥓', sausage: '🌭', fish: '🐟', salmon: '🐟', shrimp: '🦐',
  tuna: '🐟', eggs: '🥚', egg: '🥚', tofu: '🥡', turkey: '🦃',
  lamb: '🥩', hamburger: '🍔', 'hot dog': '🌭',

  // Dairy
  milk: '🥛', cheese: '🧀', yogurt: '🥛', butter: '🧈', cream: '🥛',
  'sour cream': '🥛', 'cream cheese': '🧀', mozzarella: '🧀',
  cheddar: '🧀', parmesan: '🧀',

  // Grains / Carbs
  bread: '🍞', rice: '🍚', pasta: '🍝', spaghetti: '🍝', noodles: '🍜',
  bagel: '🥯', croissant: '🥐', pancakes: '🥞', waffles: '🧇',
  cereal: '🥣', oats: '🌾', oatmeal: '🥣', flour: '🌾', quinoa: '🌾',
  tortilla: '🫓', pita: '🫓', biscuit: '🍪',

  // Drinks
  coffee: '☕', tea: '🍵', juice: '🧃', water: '💧', beer: '🍺',
  wine: '🍷', soda: '🥤', smoothie: '🥤', milk_tea: '🧋',

  // Sweets / Snacks
  cookies: '🍪', cookie: '🍪', cake: '🍰', donut: '🍩', chocolate: '🍫',
  candy: '🍬', ice_cream: '🍦', 'ice cream': '🍦', crackers: '🍪',
  chips: '🍟', popcorn: '🍿', pretzel: '🥨', pie: '🥧', muffin: '🧁',
  cupcake: '🧁',

  // Pantry / Condiments
  'olive oil': '🫒', salt: '🧂', pepper: '🌶️', sugar: '🍬', honey: '🍯',
  'soy sauce': '🍶', vinegar: '🫗', mustard: '🟡', ketchup: '🍅',
  mayo: '🥚', mayonnaise: '🥚', 'peanut butter': '🥜', jelly: '🍓',
  jam: '🍓', nutella: '🍫', 'maple syrup': '🥞',

  // Nuts / Seeds
  peanuts: '🥜', almonds: '🥜', cashews: '🥜', walnuts: '🥜',
  'mixed nuts': '🥜', sunflower_seeds: '🌻',
}

/**
 * Look up an emoji for a food name. Returns null if no match found.
 * Matches exact (case-insensitive) first, then tries single-word match.
 */
export function suggestEmoji(foodName) {
  if (!foodName) return null
  const key = foodName.trim().toLowerCase()

  // Exact match
  if (FOOD_EMOJI_LOOKUP[key]) return FOOD_EMOJI_LOOKUP[key]

  // Try matching individual words (e.g. "organic bananas" → "banana")
  const words = key.split(/\s+/)
  for (const word of words) {
    // Strip trailing 's' for simple pluralization
    const singular = word.endsWith('s') ? word.slice(0, -1) : word
    if (FOOD_EMOJI_LOOKUP[word]) return FOOD_EMOJI_LOOKUP[word]
    if (FOOD_EMOJI_LOOKUP[singular]) return FOOD_EMOJI_LOOKUP[singular]
  }

  return null
}

// Curated food emoji picker grid (for manual override)
export const CURATED_FOOD_EMOJIS = [
  {
    label: 'Fruits',
    emojis: ['🍎', '🍌', '🍊', '🍓', '🍇', '🍑', '🫐', '🍉', '🍍', '🥭', '🍐', '🍋', '🍒', '🥝', '🥥', '🍈'],
  },
  {
    label: 'Vegetables',
    emojis: ['🥕', '🍅', '🥦', '🥬', '🌽', '🥔', '🧅', '🧄', '🥒', '🫑', '🍆', '🍄', '🍠', '🥗'],
  },
  {
    label: 'Protein',
    emojis: ['🍗', '🥩', '🥓', '🌭', '🐟', '🦐', '🥚', '🦃', '🍔', '🥡'],
  },
  {
    label: 'Dairy',
    emojis: ['🥛', '🧀', '🧈', '🍦'],
  },
  {
    label: 'Grains',
    emojis: ['🍞', '🍚', '🍝', '🍜', '🥯', '🥐', '🥞', '🧇', '🥣', '🌾', '🫓'],
  },
  {
    label: 'Drinks',
    emojis: ['☕', '🍵', '🧃', '💧', '🍺', '🍷', '🥤', '🧋'],
  },
  {
    label: 'Sweets & Snacks',
    emojis: ['🍪', '🍰', '🍩', '🍫', '🍬', '🍿', '🥨', '🥧', '🧁'],
  },
  {
    label: 'Pantry',
    emojis: ['🫒', '🧂', '🌶️', '🍯', '🥜', '🌻'],
  },
]
