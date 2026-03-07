export const FAMILY_MEMBER_COLORS = [
  { hex: '#D4695A', name: 'Soft Red' },
  { hex: '#D4915A', name: 'Apricot' },
  { hex: '#BFA04A', name: 'Ochre' },
  { hex: '#5E9E6B', name: 'Sage' },
  { hex: '#4A9E9E', name: 'Teal' },
  { hex: '#5A80B0', name: 'Steel Blue' },
  { hex: '#8A60B0', name: 'Lavender' },
  { hex: '#B06085', name: 'Rose' },
  { hex: '#7A8A55', name: 'Olive' },
  { hex: '#9A7055', name: 'Mocha' },
]

export function getFirstUnusedColor(existingColors) {
  const used = new Set(existingColors.map(c => c?.toUpperCase()))
  const unused = FAMILY_MEMBER_COLORS.find(c => !used.has(c.hex.toUpperCase()))
  return unused ? unused.hex : null
}
