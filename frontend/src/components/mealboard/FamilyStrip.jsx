import MemberAvatar from '../shared/MemberAvatar'

/**
 * Family member filter strip — flat horizontal pill row.
 * Click a pill to filter meals to that person. Click again to clear.
 * Fades in on mount (family members load async).
 */
export default function FamilyStrip({ familyMembers, selectedId, onSelect }) {
  if (familyMembers.length === 0) return null

  return (
    <div
      className="
        inline-flex items-center gap-2
        px-3 py-2.5 rounded-2xl
        bg-card-bg dark:bg-gray-800
        border border-card-border dark:border-gray-700
        shadow-[0_2px_8px_rgba(0,0,0,0.03)]
      "
      style={{ animation: 'swimlane-enter 0.4s ease-out both' }}
    >
      <span className="text-xs font-bold text-text-muted dark:text-gray-400 mr-1">
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
              flex items-center gap-1.5 pl-1 pr-2.5 py-1 rounded-full
              text-xs font-semibold transition-all duration-150
              ${
                isSelected
                  ? 'bg-peach-100 dark:bg-blue-900/40 text-terracotta-600 dark:text-blue-400 ring-1 ring-terracotta-500 dark:ring-blue-500'
                  : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-peach-100 dark:hover:bg-blue-900/30 hover:text-terracotta-600 dark:hover:text-blue-400'
              }
            `}
            aria-pressed={isSelected}
            title={isSelected ? 'Clear filter' : `Show only ${member.name}'s meals`}
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
          className="ml-auto text-xs text-text-muted hover:text-text-secondary dark:text-gray-500 dark:hover:text-gray-300 underline transition-colors"
        >
          Clear
        </button>
      )}
    </div>
  )
}
