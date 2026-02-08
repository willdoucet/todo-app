import { getMemberColor } from './calendarUtils'

/**
 * Horizontal row of family member avatar circles for filtering calendar items.
 */
export default function FamilyMemberFilter({ familyMembers, activeMembers, onToggle }) {
  if (!familyMembers || familyMembers.length === 0) return null

  return (
    <div className="mb-4 flex items-center gap-2 overflow-x-auto pb-1">
      {familyMembers.map((member) => {
        const isActive = activeMembers.has(member.id)
        const color = getMemberColor(member)
        const initial = (member.name || '?')[0].toUpperCase()

        return (
          <button
            key={member.id}
            onClick={() => onToggle(member.id)}
            className={`shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
              isActive
                ? 'ring-2 ring-offset-2 ring-terracotta-500 dark:ring-blue-500 dark:ring-offset-gray-900'
                : 'opacity-40'
            }`}
            style={{ backgroundColor: color }}
            title={member.name}
            aria-label={`${isActive ? 'Hide' : 'Show'} ${member.name}`}
            aria-pressed={isActive}
          >
            <span className="text-white drop-shadow-sm">{initial}</span>
          </button>
        )
      })}
    </div>
  )
}
