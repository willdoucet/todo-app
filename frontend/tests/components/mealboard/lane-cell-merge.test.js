import { describe, it, expect } from 'vitest'
import { mergeEntriesWithPendingDeletes } from '../../../src/components/mealboard/lane-cell-merge'

describe('mergeEntriesWithPendingDeletes', () => {
  const liveEntry = (id, sort_order) => ({ id, sort_order })
  const pendingEntry = (id, sort_order) => ({
    entry: { id, sort_order },
    undoToken: `tok-${id}`,
    expiresAt: new Date(Date.now() + 5000),
  })

  it('returns empty when nothing to render', () => {
    expect(mergeEntriesWithPendingDeletes([], [])).toEqual([])
  })

  it('returns live entries unchanged when there are no pending-deletes', () => {
    const live = [liveEntry(1, 0), liveEntry(2, 1), liveEntry(3, 2)]
    const merged = mergeEntriesWithPendingDeletes(live, [])
    expect(merged.map((i) => [i.kind, i.entry.id])).toEqual([
      ['live', 1], ['live', 2], ['live', 3],
    ])
  })

  it('preserves slot position: delete-middle of a 3-meal cell', () => {
    // Salad / Pasta / Cake — user deletes Pasta; the live array now has Salad + Cake,
    // pending has Pasta; merged must be [live, pending, live] in original sort order.
    const live = [liveEntry(1, 0), liveEntry(3, 2)]
    const pending = [pendingEntry(2, 1)]
    const merged = mergeEntriesWithPendingDeletes(live, pending)
    expect(merged.map((i) => [i.kind, i.entry.id])).toEqual([
      ['live', 1], ['pending', 2], ['live', 3],
    ])
  })

  it('handles multiple simultaneous pending-deletes', () => {
    // 5-meal cell, delete first + delete last simultaneously.
    const live = [liveEntry(2, 1), liveEntry(3, 2), liveEntry(4, 3)]
    const pending = [pendingEntry(1, 0), pendingEntry(5, 4)]
    const merged = mergeEntriesWithPendingDeletes(live, pending)
    expect(merged.map((i) => [i.kind, i.entry.id])).toEqual([
      ['pending', 1], ['live', 2], ['live', 3], ['live', 4], ['pending', 5],
    ])
  })

  it('tie-breaks pending after live at equal sort_order (defensive)', () => {
    const live = [liveEntry(1, 5)]
    const pending = [pendingEntry(2, 5)]
    const merged = mergeEntriesWithPendingDeletes(live, pending)
    expect(merged.map((i) => i.kind)).toEqual(['live', 'pending'])
  })

  it('threads undoToken and expiresAt onto the pending item', () => {
    const pending = [pendingEntry(42, 0)]
    const [out] = mergeEntriesWithPendingDeletes([], pending)
    expect(out.kind).toBe('pending')
    expect(out.undoToken).toBe('tok-42')
    expect(out.expiresAt).toBeInstanceOf(Date)
  })
})
