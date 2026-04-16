import MemberAvatar from '../shared/MemberAvatar'

/**
 * Horizontal row of family member pill buttons for filtering calendar items.
 */
export default function FamilyMemberFilter({ familyMembers, activeMembers, onToggle }) {
  if (!familyMembers || familyMembers.length === 0) return null

  const visibleMembers = familyMembers.filter((m) => !m.is_system)

  if (visibleMembers.length === 0) return null

  return (
    <div className="mb-4 flex items-center gap-5 overflow-x-auto pb-1">
      {visibleMembers.map((member) => {
        const isActive = activeMembers.has(member.id)

        return (
          <button
            key={member.id}
            onClick={() => onToggle(member.id)}
            className={`flex items-center gap-2 transition-all ${
              isActive
                ? 'text-text-primary dark:text-gray-100'
                : 'text-text-secondary dark:text-gray-300 opacity-40'
            }`}
            title={member.name}
            aria-label={`${isActive ? 'Hide' : 'Show'} ${member.name}`}
            aria-pressed={isActive}
          >
            <MemberAvatar
              name={member.name}
              photoUrl={member.photo_url}
              color={member.color}
              size="md"
            />
            <span
              className="rounded-lg bg-card-bg dark:bg-gray-700 px-3 py-1.5 text-sm font-medium"
              style={{
                borderRight: `4px solid ${member.color || '#9CA3AF'}`,
              }}
            >
              {member.name}
            </span>
          </button>
        )
      })}
    </div>
  )
}
