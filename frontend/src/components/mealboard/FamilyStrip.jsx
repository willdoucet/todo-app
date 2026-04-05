import MemberAvatar from '../shared/MemberAvatar'

/**
 * Horizontal strip of family member pills at the top of the mealboard.
 * Click a pill to filter the swimlane grid to only meals that include that person.
 * Click the same pill again to clear the filter.
 */
export default function FamilyStrip({ familyMembers, selectedId, onSelect }) {
  if (familyMembers.length === 0) return null

  return (
    <div
      className="
        flex-1 flex items-center gap-2 flex-wrap
        px-3 py-2 rounded-xl
        bg-card-bg dark:bg-gray-800
        border border-card-border dark:border-gray-700
      "
    >
      <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted dark:text-gray-400 px-1">
        Family
      </span>
      {familyMembers.map((member) => {
        const isSelected = selectedId === member.id
        return (
          <button
            key={member.id}
            type="button"
            onClick={() => onSelect(member.id)}
            className={`
              flex items-center gap-1.5 pl-0.5 pr-2 py-0.5 rounded-full
              text-xs font-semibold transition-all
              ${
                isSelected
                  ? 'bg-peach-100 dark:bg-blue-900/40 text-terracotta-600 dark:text-blue-400 ring-1 ring-terracotta-500 dark:ring-blue-500'
                  : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-peach-100 dark:hover:bg-blue-900/30'
              }
            `}
            aria-pressed={isSelected}
            title={isSelected ? `Clear filter` : `Show only ${member.name}'s meals`}
          >
            <MemberAvatar name={member.name} photoUrl={member.photo_url} color={member.color} size="xs" />
            {member.name}
          </button>
        )
      })}
      {selectedId && (
        <button
          type="button"
          onClick={() => onSelect(selectedId)}
          className="ml-auto text-xs text-text-muted hover:text-text-secondary dark:text-gray-500 dark:hover:text-gray-300 underline"
        >
          Clear filter
        </button>
      )}
    </div>
  )
}
