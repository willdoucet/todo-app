import { useEffect } from 'react'

const APP_NAME = 'Family Planner'

/**
 * Custom hook to update the document title dynamically.
 * @param {string} title - The page-specific title (e.g., "Tasks", "Shopping List")
 * @param {string} [suffix] - Optional suffix to append after the title
 */
export default function usePageTitle(title, suffix = '') {
  useEffect(() => {
    const previousTitle = document.title

    if (title) {
      const fullTitle = suffix
        ? `${title} - ${suffix} - ${APP_NAME}`
        : `${title} - ${APP_NAME}`
      document.title = fullTitle
    } else {
      document.title = APP_NAME
    }

    // Restore previous title on unmount (optional, for SPA navigation)
    return () => {
      document.title = previousTitle
    }
  }, [title, suffix])
}
