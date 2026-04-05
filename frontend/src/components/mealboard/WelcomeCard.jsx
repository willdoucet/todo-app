/**
 * Welcome card shown above the swimlane grid when the mealboard is 100% empty
 * (no meal entries for the entire week). Dismissed permanently after the first
 * meal is added (tracked via localStorage).
 */
export default function WelcomeCard({ onDismiss, onAddFirst }) {
  return (
    <div
      className="
        relative rounded-2xl p-4 mb-4
        bg-gradient-to-br from-peach-100 to-warm-beige
        dark:from-blue-900/20 dark:to-gray-800
        border border-terracotta-200 dark:border-blue-800
      "
    >
      <button
        type="button"
        onClick={onDismiss}
        className="
          absolute top-2 right-2 p-1 rounded-md
          text-text-muted dark:text-gray-400
          hover:text-text-secondary dark:hover:text-gray-300
          hover:bg-white/40 dark:hover:bg-white/10
        "
        aria-label="Dismiss welcome card"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <div className="flex items-start gap-3 pr-6">
        <div className="text-2xl">🍳</div>
        <div className="flex-1">
          <h3 className="text-base font-bold text-text-primary dark:text-gray-100 mb-1">
            Plan your week!
          </h3>
          <p className="text-sm text-text-secondary dark:text-gray-300 mb-3">
            Add meals to your week — tap any <span className="font-semibold">+</span> to start. Link a shopping list and ingredients will sync automatically.
          </p>
          {onAddFirst && (
            <button
              type="button"
              onClick={onAddFirst}
              className="
                inline-flex items-center gap-2 px-3 py-1.5 rounded-lg
                bg-terracotta-500 hover:bg-terracotta-600
                dark:bg-blue-600 dark:hover:bg-blue-700
                text-white text-sm font-semibold
                transition-colors
              "
            >
              Add your first meal
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
