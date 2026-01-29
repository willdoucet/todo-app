import { useState, useEffect } from 'react'
import ResponsibilityCard from './ResponsibilityCard'

// Category definitions with icons
const CATEGORIES = [
  { id: 'MORNING', label: 'Morning', icon: '🌅' },
  { id: 'AFTERNOON', label: 'Afternoon', icon: '☀️' },
  { id: 'EVENING', label: 'Evening', icon: '🌙' },
  { id: 'CHORE', label: 'Chores', icon: '🧹' },
]

// Days of the week for frequency matching
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

export default function ScheduleView({
  familyMembers,
  responsibilities,
  completions,
  currentDate,
  isLoading,
  onToggleCompletion,
  onPreviousDay,
  onNextDay,
  everyoneID,
  onEditResponsibility,
  onDeleteResponsibility,
}) {
  // Local UI state only
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [selectedMemberId, setSelectedMemberId] = useState(null)

  // Set default selection when familyMembers load (for mobile tab view)
  useEffect(() => {
    if (familyMembers.length > 0 && !selectedMemberId) {
      setSelectedMemberId(familyMembers[0].id)
    }
    // Reset selection if current member was deleted
    if (selectedMemberId && !familyMembers.find(m => m.id === selectedMemberId)) {
      setSelectedMemberId(familyMembers[0]?.id || null)
    }
  }, [familyMembers, selectedMemberId])

  // Derived values
  const currentDayName = DAYS[currentDate.getDay()]

  // Check if a responsibility is completed for the current date
  const isCompleted = (responsibilityId, memberId) => {
    return completions.some(
      c => c.responsibility_id === responsibilityId && c.family_member_id === memberId
    )
  }

  // Get responsibilities for a specific family member (filtered by day and category)
  const getResponsibilitiesForMember = (memberId) => {
    return responsibilities
      .filter(r => r.assigned_to === memberId || r.assigned_to === everyoneID)
      .filter(r => r.frequency.includes(currentDayName))
      .filter(r => !selectedCategory || r.category === selectedCategory)
  }

  // Get completion stats for a family member
  const getCompletionStats = (memberId) => {
    const memberResponsibilities = getResponsibilitiesForMember(memberId)
    const completedCount = memberResponsibilities.filter(r => isCompleted(r.id, memberId)).length
    return { completed: completedCount, total: memberResponsibilities.length }
  }

  // Group responsibilities by category
  const groupByCategory = (items) => {
    const grouped = {}
    CATEGORIES.forEach(cat => {
      const categoryItems = items.filter(r => r.category === cat.id)
      if (categoryItems.length > 0) {
        grouped[cat.id] = categoryItems
      }
    })
    return grouped
  }

  // Render a member card (reusable for both mobile and desktop views)
  const renderMemberCard = (member, className = '') => {
    const stats = getCompletionStats(member.id)
    const memberResponsibilities = getResponsibilitiesForMember(member.id)
    const grouped = groupByCategory(memberResponsibilities)

    return (
      <div
        key={member.id}
        className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden ${className}`}
      >
        {/* Member Header */}
        <div className="p-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              {member.name}
            </h3>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {stats.completed}/{stats.total}
            </span>
          </div>
          {/* Progress bar */}
          <div className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all duration-300"
              style={{ width: stats.total > 0 ? `${(stats.completed / stats.total) * 100}%` : '0%' }}
            />
          </div>
        </div>

        {/* Responsibilities List */}
        <div className="p-4 space-y-4">
          {Object.entries(grouped).map(([categoryId, items]) => {
            const category = CATEGORIES.find(c => c.id === categoryId)
            return (
              <div key={categoryId}>
                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                  {category?.icon} {category?.label}
                </h4>
                <div className="space-y-2">
                  {items.map(responsibility => (
                    <ResponsibilityCard
                      key={responsibility.id}
                      responsibility={responsibility}
                      isCompleted={isCompleted(responsibility.id, member.id)}
                      onToggle={() => onToggleCompletion(responsibility.id, member.id)}
                      onEdit={onEditResponsibility}
                      onDelete={onDeleteResponsibility}
                    />
                  ))}
                </div>
              </div>
            )
          })}

          {memberResponsibilities.length === 0 && (
            <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-4">
              No responsibilities for today
            </p>
          )}
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Date Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onPreviousDay}
          className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors text-gray-600 dark:text-gray-400"
        >
          ← Prev
        </button>
        <div className="text-center">
          <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {currentDayName}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {currentDate.toLocaleDateString()}
          </p>
        </div>
        <button
          onClick={onNextDay}
          className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors text-gray-600 dark:text-gray-400"
        >
          Next →
        </button>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 flex-wrap justify-center">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(selectedCategory === cat.id ? null : cat.id)}
            className={`
              px-3 py-1.5 rounded-full text-sm font-medium transition-colors
              ${selectedCategory === cat.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }
            `}
          >
            {cat.icon} {cat.label}
          </button>
        ))}
      </div>

      {/* Mobile View - Tab bar + single card */}
      <div className="sm:hidden space-y-4">
        {/* Tab bar for member selection */}
        <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-none">
          {familyMembers.map(member => {
            const stats = getCompletionStats(member.id)
            return (
              <button
                key={member.id}
                onClick={() => setSelectedMemberId(member.id)}
                className={`
                  flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-colors
                  ${selectedMemberId === member.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                  }
                `}
              >
                {member.name} ({stats.completed}/{stats.total})
              </button>
            )
          })}
        </div>

        {/* Single member card for selected member */}
        {selectedMemberId && familyMembers.find(m => m.id === selectedMemberId) && (
          renderMemberCard(familyMembers.find(m => m.id === selectedMemberId), 'w-full')
        )}
      </div>

      {/* Desktop/Tablet View - Responsive grid */}
      <div className="hidden sm:grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {familyMembers.map(member => renderMemberCard(member))}
      </div>

      {familyMembers.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">
            No family members found. Add family members first.
          </p>
        </div>
      )}
    </div>
  )
}
