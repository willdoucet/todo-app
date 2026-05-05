// Rendered as the data router's `errorElement` for the protected layout
// route when rootAuthLoader throws a non-401 Response (5xx / network /
// timeout / malformed refresh). Distinct chromeless treatment communicates
// "the system is broken" rather than "we need something from you" — the
// auth portal is the latter, this is the former.
//
// Renders OUTSIDE RootLayout, so dark-mode is read inline from the same
// localStorage key DarkModeContext writes.

import { useMemo } from 'react'
import { useRevalidator } from 'react-router-dom'

function readDarkPreference() {
  if (typeof window === 'undefined') return false
  try {
    const stored = window.localStorage.getItem('darkMode')
    if (stored === 'true') return true
    if (stored === 'false') return false
  } catch {
    // ignore
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

export default function BootErrorScreen() {
  const isDark = useMemo(() => readDarkPreference(), [])
  const revalidator = useRevalidator()
  const isRevalidating = revalidator.state === 'loading'

  const wrapperBase = 'min-h-screen flex items-center justify-center px-4'
  const wrapperClass = isDark
    ? `${wrapperBase} bg-gray-900`
    : `${wrapperBase} bg-warm-cream`

  const headlineClass = isDark
    ? 'text-2xl font-semibold text-gray-100 max-w-[380px] text-center'
    : 'text-2xl font-semibold text-text-primary max-w-[380px] text-center'

  const bodyClass = isDark
    ? 'text-base text-gray-400 max-w-[420px] text-center leading-relaxed mt-3'
    : 'text-base text-text-secondary max-w-[420px] text-center leading-relaxed mt-3'

  const iconColor = isDark ? 'text-blue-400' : 'text-terracotta-500'

  return (
    <div className={wrapperClass}>
      <div className="flex flex-col items-center gap-6">
        <svg
          width="56"
          height="56"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={iconColor}
          aria-hidden="true"
        >
          <path d="M17.5 19a4.5 4.5 0 0 0 .5-8.97A6 6 0 0 0 6.18 9.5 4.5 4.5 0 0 0 7 18" />
          <line x1="3" y1="3" x2="21" y2="21" />
        </svg>
        <h1 className={headlineClass}>We can&apos;t reach our server right now</h1>
        <p className={bodyClass}>
          Check your internet, then try again. If this keeps happening, the
          server may be down.
        </p>
        <button
          type="button"
          onClick={() => revalidator.revalidate()}
          disabled={isRevalidating}
          className="px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 disabled:bg-terracotta-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-terracotta-500"
        >
          {isRevalidating ? 'Trying…' : 'Try again'}
        </button>
      </div>
    </div>
  )
}
