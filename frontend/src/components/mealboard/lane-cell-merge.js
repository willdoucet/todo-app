/**
 * Merge a cell's live meal entries with its pending-delete entries into a
 * single ordered render list that preserves each entry's original slot
 * position.
 *
 * This helper exists so LaneCell (and MobileDayView) can render UndoMealCards
 * inline in the same slot the deleted card vacated — without that, neighbors
 * would jump up to fill the gap, breaking the "nothing teleports" invariant
 * that the whole in-place-undo feature hangs on.
 *
 * Input:
 *   - liveEntries: array of meal entries already filtered to this cell, sorted
 *                  by `sort_order` ascending.
 *   - pendingDeletesForCell: array of pending-delete descriptors, each shaped
 *                  `{ entry, undoToken, expiresAt }`, where `entry` is a
 *                  snapshot of the meal entry at delete time (so the UndoMealCard
 *                  can render its name without another fetch).
 *
 * Output: ordered array of `{ kind, entry, undoToken? }` items, sorted by
 *   `entry.sort_order`. Tie-breaker: if a pending-delete shares `sort_order`
 *   with a live entry, the PENDING item sorts AFTER the live one — defensive
 *   against a future bug where a live entry gets re-created at the same
 *   sort_order before the pending-delete timer fires. Shouldn't happen in
 *   practice; documented here so we don't get surprised.
 */
export function mergeEntriesWithPendingDeletes(liveEntries, pendingDeletesForCell) {
  const liveItems = liveEntries.map((entry) => ({
    kind: 'live',
    entry,
    sortKey: entry.sort_order ?? 0,
    tieBreak: 0, // live before pending at equal sort_order
  }))

  const pendingItems = (pendingDeletesForCell || []).map((pd) => ({
    kind: 'pending',
    entry: pd.entry,
    undoToken: pd.undoToken,
    expiresAt: pd.expiresAt,
    sortKey: pd.entry?.sort_order ?? 0,
    tieBreak: 1, // pending after live at equal sort_order
  }))

  return [...liveItems, ...pendingItems]
    .sort((a, b) => {
      if (a.sortKey !== b.sortKey) return a.sortKey - b.sortKey
      return a.tieBreak - b.tieBreak
    })
    .map((item) => {
      // Strip the internal sort/tie-break keys so consumers only see the
      // rendering fields.
      const { sortKey: _sk, tieBreak: _tb, ...rest } = item
      void _sk
      void _tb
      return rest
    })
}
