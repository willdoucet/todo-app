import { useState } from 'react'
import MemberAvatar from '../shared/MemberAvatar'

// Slot type color palette (different from family member colors)
const SLOT_COLORS = [
  '#F5A623', // amber (breakfast)
  '#6B8F71', // sage (lunch)
  '#E8927C', // peach (dinner)
  '#A78BDB', // lavender (snack)
  '#5B8DEF', // blue
  '#E06B9F', // pink
  '#7EC8A0', // green
  '#C4A0E8', // purple
]

export default function MealSlotCard({
  slot,
  familyMembers,
  isEditing,
  isNew = false,
  onStartEdit,
  onCancelEdit,
  onSave,
  onToggleActive,
  onDelete,
}) {
  // Edit form state
  const [name, setName] = useState(slot?.name || '')
  const [icon, setIcon] = useState(slot?.icon || '')
  const [color, setColor] = useState(slot?.color || SLOT_COLORS[0])
  const [participantIds, setParticipantIds] = useState(slot?.default_participants || [])

  const handleSave = () => {
    if (!name.trim()) return
    onSave({
      name: name.trim(),
      icon: icon || null,
      color,
      default_participants: participantIds,
    })
  }

  const toggleParticipant = (memberId) => {
    setParticipantIds((prev) =>
      prev.includes(memberId) ? prev.filter((id) => id !== memberId) : [...prev, memberId]
    )
  }

  const participantMembers = (slot?.default_participants || [])
    .map((id) => familyMembers.find((m) => m.id === id))
    .filter(Boolean)

  // Special: empty participants means "everyone"
  const showsEveryone = !slot?.default_participants || slot.default_participants.length === 0

  if (isEditing) {
    return (
      <div
        className={`
          p-3 rounded-xl border-2 border-terracotta-200 dark:border-blue-800
          bg-terracotta-50/30 dark:bg-blue-900/10
        `}
      >
        <div className="space-y-3">
          {/* Name + icon row */}
          <div className="flex gap-2">
            <input
              type="text"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              placeholder="🍽"
              maxLength={4}
              className="
                w-12 px-2 py-2 text-center text-lg
                border border-card-border dark:border-gray-600
                rounded-lg bg-white dark:bg-gray-700
                focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
              "
              aria-label="Icon"
            />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Slot name"
              autoFocus
              className="
                flex-1 px-3 py-2 text-sm
                border border-card-border dark:border-gray-600
                rounded-lg bg-white dark:bg-gray-700
                text-text-primary dark:text-gray-100
                focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
              "
              aria-label="Slot name"
            />
          </div>

          {/* Color picker */}
          <div>
            <label className="block text-xs font-medium text-text-secondary dark:text-gray-400 mb-1.5">
              Color
            </label>
            <div className="flex gap-2 flex-wrap">
              {SLOT_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`
                    w-7 h-7 rounded-full transition-transform
                    ${color === c ? 'ring-2 ring-offset-2 ring-terracotta-500 dark:ring-offset-gray-800 dark:ring-blue-500 scale-110' : 'hover:scale-110'}
                  `}
                  style={{ backgroundColor: c }}
                  aria-label={`Choose color ${c}`}
                />
              ))}
            </div>
          </div>

          {/* Participants */}
          <div>
            <label className="block text-xs font-medium text-text-secondary dark:text-gray-400 mb-1.5">
              Default participants {participantIds.length === 0 && <span className="text-text-muted">(empty = everyone)</span>}
            </label>
            <div className="flex gap-2 flex-wrap">
              {familyMembers.map((member) => {
                const active = participantIds.includes(member.id)
                return (
                  <button
                    key={member.id}
                    type="button"
                    onClick={() => toggleParticipant(member.id)}
                    className={`
                      flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium
                      border transition-all
                      ${
                        active
                          ? 'border-terracotta-500 bg-peach-100 text-terracotta-600 dark:border-blue-500 dark:bg-blue-900/30 dark:text-blue-400'
                          : 'border-card-border text-text-muted dark:border-gray-600 dark:text-gray-400 hover:border-text-secondary'
                      }
                    `}
                  >
                    <MemberAvatar name={member.name} photoUrl={member.photo_url} color={member.color} size="xs" />
                    {member.name}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={handleSave}
              className="
                px-3 py-1.5 text-sm font-medium rounded-lg
                bg-terracotta-500 dark:bg-blue-600
                hover:bg-terracotta-600 dark:hover:bg-blue-700
                text-white transition-colors
              "
            >
              {isNew ? 'Create' : 'Save'}
            </button>
            <button
              type="button"
              onClick={onCancelEdit}
              className="
                px-3 py-1.5 text-sm font-medium rounded-lg
                text-text-secondary dark:text-gray-400
                hover:bg-warm-beige dark:hover:bg-gray-700
                transition-colors
              "
            >
              Cancel
            </button>
            {!isNew && onDelete && !slot?.is_default && (
              <button
                type="button"
                onClick={onDelete}
                className="
                  ml-auto px-3 py-1.5 text-sm font-medium rounded-lg
                  text-red-600 dark:text-red-400
                  hover:bg-red-50 dark:hover:bg-red-900/20
                  transition-colors
                "
              >
                Delete
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Display mode (not editing)
  return (
    <div
      className={`
        flex items-center gap-3 p-3 rounded-xl border
        border-card-border dark:border-gray-700
        bg-card-bg dark:bg-gray-800
        ${!slot.is_active ? 'opacity-50' : ''}
      `}
    >
      {/* Drag handle (future feature) */}
      <span className="text-text-muted dark:text-gray-500 cursor-grab">⋮⋮</span>

      {/* Color dot + icon + name */}
      <span
        className="w-3 h-3 rounded-full flex-shrink-0"
        style={{ backgroundColor: slot.color }}
      />
      {slot.icon && <span className="text-base leading-none">{slot.icon}</span>}
      <span className="text-sm font-medium text-text-primary dark:text-gray-100">
        {slot.name}
        {!slot.is_active && <span className="ml-1 text-xs text-text-muted">(hidden)</span>}
      </span>

      {/* Participant avatars or "Everyone" */}
      <div className="flex-1 flex items-center">
        {showsEveryone ? (
          <span className="text-xs text-text-muted dark:text-gray-400">Everyone</span>
        ) : (
          <div className="flex -space-x-1">
            {participantMembers.slice(0, 4).map((m) => (
              <MemberAvatar
                key={m.id}
                name={m.name}
                photoUrl={m.photo_url}
                color={m.color}
                size="xs"
                className="ring-2 ring-card-bg dark:ring-gray-800"
              />
            ))}
            {participantMembers.length > 4 && (
              <span className="text-xs text-text-muted ml-1">+{participantMembers.length - 4}</span>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <button
        type="button"
        onClick={onStartEdit}
        className="
          p-1.5 rounded-md text-text-muted dark:text-gray-400
          hover:bg-warm-beige dark:hover:bg-gray-700
          hover:text-terracotta-600 dark:hover:text-blue-400
          transition-colors
        "
        title="Edit slot"
        aria-label="Edit slot"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      </button>
      <button
        type="button"
        onClick={onToggleActive}
        className="
          p-1.5 rounded-md text-text-muted dark:text-gray-400
          hover:bg-warm-beige dark:hover:bg-gray-700
          transition-colors
        "
        title={slot.is_active ? 'Hide slot' : 'Show slot'}
        aria-label={slot.is_active ? 'Hide slot' : 'Show slot'}
      >
        {slot.is_active ? (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" stroke="currentColor" fill="none" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
            <line x1="1" y1="1" x2="23" y2="23" strokeLinecap="round" />
          </svg>
        )}
      </button>
    </div>
  )
}
