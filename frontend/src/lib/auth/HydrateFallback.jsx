// Boot-time spinner shown while the data router's rootAuthLoader is
// running its first refresh attempt (~50–200ms typical). Renders OUTSIDE
// RootLayout — DarkModeProvider / ToastProvider have not mounted yet, so
// dark-mode appearance is read directly from the same localStorage key
// DarkModeContext writes ('darkMode' → 'true' | 'false'), with
// prefers-color-scheme as the no-preference fallback.

import { useMemo } from 'react'

function readDarkPreference() {
  if (typeof window === 'undefined') return false
  try {
    const stored = window.localStorage.getItem('darkMode')
    if (stored === 'true') return true
    if (stored === 'false') return false
  } catch {
    // Private mode / quota exceeded → fall through.
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

export default function HydrateFallback() {
  const isDark = useMemo(() => readDarkPreference(), [])

  const wrapperClass = isDark
    ? 'min-h-screen flex items-center justify-center bg-gray-900'
    : 'min-h-screen flex items-center justify-center bg-warm-cream'

  return (
    <div className={wrapperClass} role="status" aria-label="Loading">
      <svg
        className="animate-spin"
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeOpacity="0.2"
          strokeWidth="3"
          className="text-terracotta-500"
        />
        <path
          d="M22 12a10 10 0 0 0-10-10"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          className="text-terracotta-500"
        />
      </svg>
    </div>
  )
}
