import { useState, useEffect } from 'react'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import ResponsibilityCard from './ResponsibilityCard'
import { EmptyDailyViewState } from './EmptyState'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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

  // Get all responsibilities for today (before category filter)
  const todaysResponsibilities = responsibilities.filter(r => r.frequency.includes(currentDayName))

  // Calculate category counts for filter badges
  const getCategoryCounts = () => {
    const counts = {}
    CATEGORIES.forEach(cat => {
      counts[cat.id] = todaysResponsibilities.filter(r => r.categories.includes(cat.id)).length
    })
    return counts
  }
  const categoryCounts = getCategoryCounts()
  const totalCount = todaysResponsibilities.length

  // Check if a responsibility is completed for the current date and category
  const isCompleted = (responsibilityId, memberId, categoryId) => {
    return completions.some(
      c => c.responsibility_id === responsibilityId && c.family_member_id === memberId && c.category === categoryId
    )
  }

  // Get responsibilities for a specific family member (filtered by day and category)
  const getResponsibilitiesForMember = (memberId) => {
    return responsibilities
      .filter(r => r.assigned_to === memberId || r.assigned_to === everyoneID)
      .filter(r => r.frequency.includes(currentDayName))
      .filter(r => !selectedCategory || r.categories.includes(selectedCategory))
  }

  // Get completion stats for a family member (counts per-category items)
  const getCompletionStats = (memberId) => {
    const memberResponsibilities = getResponsibilitiesForMember(memberId)
    // A responsibility in multiple categories counts once per visible category
    let total = 0
    let completed = 0
    memberResponsibilities.forEach(r => {
      const visibleCategories = selectedCategory
        ? r.categories.filter(c => c === selectedCategory)
        : r.categories
      visibleCategories.forEach(cat => {
        total++
        if (isCompleted(r.id, memberId, cat)) completed++
      })
    })
    return { completed, total }
  }

  // Group responsibilities by category
  const groupByCategory = (items) => {
    const grouped = {}
    CATEGORIES.forEach(cat => {
      const categoryItems = items.filter(r => r.categories.includes(cat.id))
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

    const percentage = stats.total > 0 ? (stats.completed / stats.total) * 100 : 0

    return (
      <div
        key={member.id}
        className={`bg-card-bg dark:bg-gray-800 rounded-2xl shadow-md overflow-hidden ${className}`}
      >
        {/* Member Header */}
        <div className="p-4 pb-3">
          <div className="flex items-center gap-3 mb-3">
            <MemberAvatar name={member.name} photoUrl={member.photo_url} size="xl" />
            <h3 className="text-lg font-semibold text-text-primary dark:text-gray-100">
              {member.name}
            </h3>
          </div>
          {/* Progress bar with stats - enhanced with sage gradient */}
          <div className="flex items-center gap-3">
            <div
              className="flex-1 h-2.5 bg-warm-sand/70 dark:bg-gray-700 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={stats.completed}
              aria-valuemin={0}
              aria-valuemax={stats.total}
              aria-label={`${member.name}'s progress: ${stats.completed} of ${stats.total} tasks completed`}
            >
              <div
                className="h-full bg-gradient-to-r from-sage-400 to-sage-500 dark:from-green-500 dark:to-green-400 transition-all duration-500 ease-out"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <span className="text-sm font-medium text-sage-600 dark:text-green-400 tabular-nums min-w-[3rem] text-right" aria-hidden="true">
              {stats.completed}/{stats.total}
            </span>
          </div>
        </div>

        {/* Responsibilities List */}
        <div className="p-4 space-y-4">
          {Object.entries(grouped).map(([categoryId, items]) => {
            const category = CATEGORIES.find(c => c.id === categoryId)
            return (
              <div key={categoryId}>
                <h4 className="text-xs font-semibold text-label-green dark:text-gray-400 uppercase tracking-wider mb-2">
                  {category?.icon} {category?.label}
                </h4>
                <div className="space-y-2">
                  {items.map(responsibility => (
                    <ResponsibilityCard
                      key={`${responsibility.id}-${categoryId}`}
                      responsibility={responsibility}
                      isCompleted={isCompleted(responsibility.id, member.id, categoryId)}
                      onToggle={(cat) => onToggleCompletion(responsibility.id, member.id, cat || categoryId)}
                      categoryContext={categoryId}
                      onEdit={onEditResponsibility || null}
                      onDelete={onDeleteResponsibility || null}
                    />
                  ))}
                </div>
              </div>
            )
          })}

          {memberResponsibilities.length === 0 && (
            <div className="py-4">
              <p className="text-sm text-text-muted dark:text-gray-500 text-center">
                No responsibilities for today
              </p>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-terracotta-500 dark:border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Date Navigation */}
      <div className="flex items-center justify-center gap-4 mb-4">
        <button
          onClick={onPreviousDay}
          className="p-2 rounded-full text-text-secondary hover:text-terracotta-600 hover:bg-peach-100 dark:hover:bg-gray-700 dark:hover:text-blue-400 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500"
          aria-label="Previous day"
        >
          <ChevronLeftIcon className="w-5 h-5" />
        </button>
        <div className="text-center min-w-[140px]">
          <p className="text-lg font-semibold text-text-primary dark:text-gray-100">
            {currentDayName}
          </p>
          <p className="text-sm text-text-muted dark:text-gray-400">
            {currentDate.toLocaleDateString()}
          </p>
        </div>
        <button
          onClick={onNextDay}
          className="p-2 rounded-full text-text-secondary hover:text-terracotta-600 hover:bg-peach-100 dark:hover:bg-gray-700 dark:hover:text-blue-400 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500"
          aria-label="Next day"
        >
          <ChevronRightIcon className="w-5 h-5" />
        </button>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 flex-wrap justify-center" role="group" aria-label="Filter by category">
        {/* All button */}
        <button
          onClick={() => setSelectedCategory(null)}
          aria-pressed={selectedCategory === null}
          className={`
            px-3 py-1.5 rounded-full text-sm font-medium transition-colors
            focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500
            ${selectedCategory === null
              ? 'bg-peach-100 text-terracotta-700 dark:bg-blue-600 dark:text-white'
              : 'bg-warm-sand/50 text-text-secondary hover:bg-warm-sand dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            }
          `}
        >
          All {totalCount > 0 && <span className="opacity-75">({totalCount})</span>}
        </button>
        {CATEGORIES.map(cat => {
          const count = categoryCounts[cat.id] || 0
          return (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(selectedCategory === cat.id ? null : cat.id)}
              aria-pressed={selectedCategory === cat.id}
              className={`
                px-3 py-1.5 rounded-full text-sm font-medium transition-colors
                focus:outline-none focus-visible:ring-2 focus-visible:ring-terracotta-500 dark:focus-visible:ring-blue-500
                ${selectedCategory === cat.id
                  ? 'bg-peach-100 text-terracotta-700 dark:bg-blue-600 dark:text-white'
                  : 'bg-warm-sand/50 text-text-secondary hover:bg-warm-sand dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }
              `}
            >
              {cat.icon} {cat.label} {count > 0 && <span className="opacity-75">({count})</span>}
            </button>
          )
        })}
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
                  flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors
                  ${selectedMemberId === member.id
                    ? 'bg-peach-100 text-terracotta-700 dark:bg-blue-600 dark:text-white'
                    : 'bg-warm-beige dark:bg-gray-700 text-text-secondary dark:text-gray-300'
                  }
                `}
              >
                <MemberAvatar
                  name={member.name}
                  photoUrl={member.photo_url}
                  size="sm"
                  className={selectedMemberId === member.id ? 'ring-2 ring-terracotta-500 dark:ring-white' : ''}
                />
                <span>{member.name}</span>
                <span className="opacity-75">({stats.completed}/{stats.total})</span>
              </button>
            )
          })}
        </div>

        {/* Single member card for selected member */}
        {selectedMemberId && familyMembers.find(m => m.id === selectedMemberId) && (
          renderMemberCard(familyMembers.find(m => m.id === selectedMemberId), 'w-full')
        )}
      </div>

      {/* Desktop/Tablet View - Responsive flex grid */}
      <div className="hidden sm:flex sm:flex-wrap sm:justify-center gap-4">
        {familyMembers.map(member => renderMemberCard(member, 'w-[calc(50%-0.5rem)] lg:w-[calc(33.333%-0.67rem)] xl:w-[calc(25%-0.75rem)]'))}
      </div>

      {familyMembers.length === 0 && (
        <EmptyDailyViewState />
      )}
    </div>
  )
}

// Avatar component that shows photo if available, otherwise shows initial
function MemberAvatar({ name, photoUrl, size = 'md', className = '' }) {
  const initial = name.charAt(0).toUpperCase()
  const colors = [
    { bg: 'bg-blue-100 dark:bg-blue-900/40', text: 'text-blue-600 dark:text-blue-400' },
    { bg: 'bg-pink-100 dark:bg-pink-900/40', text: 'text-pink-600 dark:text-pink-400' },
    { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-600 dark:text-green-400' },
    { bg: 'bg-purple-100 dark:bg-purple-900/40', text: 'text-purple-600 dark:text-purple-400' },
    { bg: 'bg-orange-100 dark:bg-orange-900/40', text: 'text-orange-600 dark:text-orange-400' },
  ]
  const colorIndex = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % colors.length
  const color = colors[colorIndex]

  const sizeClasses = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-10 h-10 text-base',
    xl: 'w-16 h-16 text-xl',
  }

  // If there's a photo URL, show the image
  if (photoUrl) {
    const imageSrc = photoUrl.startsWith('http') ? photoUrl : `${API_BASE}${photoUrl}`
    return (
      <img
        src={imageSrc}
        alt={name}
        className={`${sizeClasses[size].split(' ').slice(0, 2).join(' ')} rounded-full object-cover ${className}`}
      />
    )
  }

  // Otherwise show the initial
  return (
    <div className={`flex items-center justify-center rounded-full ${sizeClasses[size]} ${color.bg} ${className}`}>
      <span className={`font-semibold ${color.text}`}>{initial}</span>
    </div>
  )
}
