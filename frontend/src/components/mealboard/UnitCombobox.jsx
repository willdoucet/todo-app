import { useState, useRef, useEffect, useMemo } from 'react'
import { UNIT_GROUPS, ALL_UNITS, UNIT_TO_GROUP, GROUP_COLORS } from '../../constants/units'

/**
 * Searchable combobox for selecting a predefined ingredient unit.
 *
 * Features:
 *  - Type to filter (e.g. "cl" → narrows to "clove")
 *  - Grouped options with color-coded category tags (Weight/Volume/Count)
 *  - Keyboard navigation: arrow keys, Enter to select, Esc to close
 *  - "(no unit)" option at the top
 *
 * Props:
 *   value: currently selected unit (string) or null
 *   onChange: (unit) => void — null when user clears or selects "(no unit)"
 *   className: optional extra classes for the button
 */
export default function UnitCombobox({ value, onChange, className = '' }) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [highlightIdx, setHighlightIdx] = useState(0)
  const wrapperRef = useRef(null)
  const searchInputRef = useRef(null)

  // Close on click-outside
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Focus search when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => searchInputRef.current?.focus(), 0)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setHighlightIdx(0)
    }
  }, [open])

  // Build flat filtered list for keyboard navigation
  // First item is always "(no unit)"
  const filteredList = useMemo(() => {
    const q = search.trim().toLowerCase()
    const items = [{ value: null, label: '(no unit)', group: null }]
    for (const unit of ALL_UNITS) {
      if (!q || unit.value.toLowerCase().includes(q) || unit.name.toLowerCase().includes(q)) {
        items.push(unit)
      }
    }
    return items
  }, [search])

  // Group filtered results for display
  const filteredGroups = useMemo(() => {
    const groups = UNIT_GROUPS.map((g) => ({
      label: g.label,
      units: g.units.filter((u) => filteredList.some((f) => f.value === u.value)),
    })).filter((g) => g.units.length > 0)
    return groups
  }, [filteredList])

  const handleSelect = (unit) => {
    onChange(unit?.value || null)
    setOpen(false)
    setSearch('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightIdx((prev) => Math.min(prev + 1, filteredList.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightIdx((prev) => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filteredList[highlightIdx]) {
        handleSelect(filteredList[highlightIdx])
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setOpen(false)
      setSearch('')
    }
  }

  // Reset highlight when filter changes — the previous index may now point to
  // a row that's been filtered out.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHighlightIdx(0)
  }, [search])

  // Display label for closed state
  const displayLabel = value
    ? (ALL_UNITS.find((u) => u.value === value)?.label || value)
    : 'Unit'

  // Compute position of highlighted item in the grouped list for visual highlighting
  const getFlatIndex = (unit) => filteredList.findIndex((f) => f.value === unit.value)

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`
          w-full px-3 py-2 text-sm text-left rounded-lg
          border border-card-border dark:border-gray-600
          bg-white dark:bg-gray-700
          text-text-primary dark:text-gray-100
          focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500
          flex items-center justify-between gap-1
        `}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={value ? '' : 'text-text-muted dark:text-gray-500'}>{displayLabel}</span>
        <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          className="
            absolute z-50 mt-1 left-0 right-0 min-w-[220px]
            bg-card-bg dark:bg-gray-800
            border border-card-border dark:border-gray-700
            rounded-lg shadow-lg
            max-h-80 overflow-hidden flex flex-col
          "
        >
          {/* Search input */}
          <div className="p-2 border-b border-card-border dark:border-gray-700">
            <div className="relative">
              <svg
                className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                ref={searchInputRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type to filter..."
                className="
                  w-full pl-7 pr-2 py-1.5 text-xs rounded
                  border border-card-border dark:border-gray-600
                  bg-white dark:bg-gray-700
                  text-text-primary dark:text-gray-100
                  placeholder-text-muted
                  focus:outline-none focus:ring-1 focus:ring-terracotta-500 dark:focus:ring-blue-500
                "
              />
            </div>
          </div>

          {/* Options list */}
          <div className="overflow-y-auto">
            {/* (no unit) option always first */}
            <button
              type="button"
              onClick={() => handleSelect({ value: null })}
              className={`
                w-full flex items-center justify-between px-3 py-1.5 text-xs
                border-b border-card-border dark:border-gray-700
                ${
                  highlightIdx === 0
                    ? 'bg-warm-beige dark:bg-gray-700'
                    : 'hover:bg-warm-beige dark:hover:bg-gray-700'
                }
                ${value === null ? 'text-terracotta-600 dark:text-blue-400 font-medium' : 'text-text-secondary dark:text-gray-300'}
              `}
            >
              <span>(no unit)</span>
              {value === null && <span>✓</span>}
            </button>

            {filteredGroups.map((group) => (
              <div key={group.label}>
                <div className="px-3 py-1 text-[9px] font-bold uppercase tracking-wider text-text-muted dark:text-gray-500 bg-warm-beige/40 dark:bg-gray-700/30">
                  {group.label}
                </div>
                {group.units.map((unit) => {
                  const flatIdx = getFlatIndex(unit)
                  const isSelected = value === unit.value
                  const isHighlighted = highlightIdx === flatIdx
                  const groupColor = GROUP_COLORS[unit.group]
                  return (
                    <button
                      key={unit.value}
                      type="button"
                      onClick={() => handleSelect(unit)}
                      className={`
                        w-full flex items-center justify-between px-3 py-1.5 text-xs
                        ${isHighlighted ? 'bg-warm-beige dark:bg-gray-700' : 'hover:bg-warm-beige dark:hover:bg-gray-700'}
                        ${isSelected ? 'text-terracotta-600 dark:text-blue-400 font-medium' : 'text-text-primary dark:text-gray-100'}
                      `}
                    >
                      <span className="flex items-center gap-2">
                        <span>{unit.label}</span>
                        <span className="text-text-muted dark:text-gray-500">— {unit.name}</span>
                      </span>
                      <span className="flex items-center gap-1">
                        {groupColor && (
                          <span
                            className={`
                              px-1.5 py-0 text-[8px] uppercase font-bold tracking-wider rounded
                              ${groupColor.bg} ${groupColor.text}
                            `}
                          >
                            {unit.group}
                          </span>
                        )}
                        {isSelected && <span>✓</span>}
                      </span>
                    </button>
                  )
                })}
              </div>
            ))}

            {filteredList.length === 1 && ( // Only "(no unit)" remains
              <div className="px-3 py-3 text-center text-xs text-text-muted dark:text-gray-400">
                No matches for "{search}"
              </div>
            )}
          </div>

          {/* Keyboard hint */}
          <div className="px-3 py-1.5 border-t border-card-border dark:border-gray-700 text-[9px] text-text-muted dark:text-gray-500 bg-warm-beige/30 dark:bg-gray-700/30 flex gap-3">
            <span>↑↓ Navigate</span>
            <span>⏎ Select</span>
            <span>Esc Close</span>
          </div>
        </div>
      )}
    </div>
  )
}
