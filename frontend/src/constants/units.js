/**
 * Predefined unit system for recipe ingredients and shopping list aggregation.
 * Must stay in sync with backend/app/constants/units.py
 */

export const WEIGHT_UNITS = [
  { value: 'lb', label: 'lb', name: 'pound', group: 'weight' },
  { value: 'oz', label: 'oz', name: 'ounce', group: 'weight' },
  { value: 'g', label: 'g', name: 'gram', group: 'weight' },
  { value: 'kg', label: 'kg', name: 'kilogram', group: 'weight' },
]

export const VOLUME_UNITS = [
  { value: 'cup', label: 'cup', name: 'cup', group: 'volume' },
  { value: 'tbsp', label: 'tbsp', name: 'tablespoon', group: 'volume' },
  { value: 'tsp', label: 'tsp', name: 'teaspoon', group: 'volume' },
  { value: 'ml', label: 'ml', name: 'milliliter', group: 'volume' },
  { value: 'l', label: 'l', name: 'liter', group: 'volume' },
  { value: 'fl oz', label: 'fl oz', name: 'fluid ounce', group: 'volume' },
  { value: 'quart', label: 'quart', name: 'quart', group: 'volume' },
  { value: 'pint', label: 'pint', name: 'pint', group: 'volume' },
  { value: 'gallon', label: 'gallon', name: 'gallon', group: 'volume' },
]

export const COUNT_UNITS = [
  { value: 'each', label: 'each', name: 'each', group: 'count' },
  { value: 'piece', label: 'piece', name: 'piece', group: 'count' },
  { value: 'clove', label: 'clove', name: 'clove', group: 'count' },
  { value: 'slice', label: 'slice', name: 'slice', group: 'count' },
  { value: 'bunch', label: 'bunch', name: 'bunch', group: 'count' },
  { value: 'can', label: 'can', name: 'can', group: 'count' },
  { value: 'package', label: 'package', name: 'package', group: 'count' },
  { value: 'head', label: 'head', name: 'head', group: 'count' },
  { value: 'stalk', label: 'stalk', name: 'stalk', group: 'count' },
  { value: 'sprig', label: 'sprig', name: 'sprig', group: 'count' },
  { value: 'ear', label: 'ear', name: 'ear', group: 'count' },
]

// All units in grouped structure (for combobox dropdown)
export const UNIT_GROUPS = [
  { label: 'Weight', units: WEIGHT_UNITS },
  { label: 'Volume', units: VOLUME_UNITS },
  { label: 'Count', units: COUNT_UNITS },
]

// Flat list of all units (for validation)
export const ALL_UNITS = [...WEIGHT_UNITS, ...VOLUME_UNITS, ...COUNT_UNITS]

// Quick lookup: value → group
export const UNIT_TO_GROUP = Object.fromEntries(
  ALL_UNITS.map(u => [u.value, u.group])
)

// Group color tags for the combobox UI
export const GROUP_COLORS = {
  weight: { bg: 'bg-terracotta-50', text: 'text-terracotta-600', label: 'Weight' },
  volume: { bg: 'bg-sage-50', text: 'text-sage-600', label: 'Volume' },
  count: { bg: 'bg-peach-100', text: 'text-text-secondary', label: 'Count' },
}
