import { FAMILY_MEMBER_COLORS } from '../../constants/familyColors'

export default function ColorPicker({ selectedColor, onSelect, disabledColors = [] }) {
  const disabledSet = new Set(disabledColors.map(c => c?.toUpperCase()))

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Choose a color">
      {FAMILY_MEMBER_COLORS.map(({ hex, name }) => {
        const isSelected = selectedColor?.toUpperCase() === hex.toUpperCase()
        const isDisabled = disabledSet.has(hex.toUpperCase())
        return (
          <button
            key={hex}
            type="button"
            aria-label={name}
            aria-pressed={isSelected}
            aria-disabled={isDisabled || undefined}
            disabled={isDisabled}
            onClick={() => onSelect(hex)}
            className={`w-7 h-7 rounded-full transition-transform focus:outline-none relative overflow-hidden ${
              isDisabled
                ? 'opacity-40 cursor-not-allowed'
                : 'hover:scale-110'
            }`}
            style={{
              backgroundColor: hex,
              boxShadow: isSelected
                ? `0 0 0 2px white, 0 0 0 4px ${hex}`
                : 'none',
            }}
          >
            {isDisabled && (
              <span
                className="absolute inset-0 flex items-center justify-center"
                aria-hidden="true"
              >
                <span className="block w-[140%] h-0.5 bg-white/80 dark:bg-gray-300/80 rotate-45" />
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
