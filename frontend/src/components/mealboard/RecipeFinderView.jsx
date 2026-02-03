export default function RecipeFinderView() {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-warm-sand dark:bg-gray-700 flex items-center justify-center">
          <svg className="w-10 h-10 text-text-muted dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-text-primary dark:text-gray-100 mb-3">
          Recipe Finder
        </h2>
        <p className="text-text-secondary dark:text-gray-400 mb-6">
          AI-powered recipe discovery is coming soon. You'll be able to search for recipes by ingredients, cuisine, or keywords.
        </p>
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-terracotta-100 dark:bg-blue-900/30 text-terracotta-600 dark:text-blue-400 rounded-full text-sm font-medium">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Coming Soon
        </div>
      </div>
    </div>
  )
}
