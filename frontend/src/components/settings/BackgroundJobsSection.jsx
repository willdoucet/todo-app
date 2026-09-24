import { useEffect, useRef } from 'react'
import FreshnessDot from '../shared/FreshnessDot'
import useBackgroundJobs, { announcementFor } from '../../hooks/useBackgroundJobs'
import useDelayedFlag from '../../hooks/useDelayedFlag'

// The Background jobs card on Settings (M8 item 15a; mockup
// .agents/plans/features/prod-launch-release/mockups/background-jobs-card-option-a.html).
// One headline that follows the worst job, one "what this means" line in states 2–4, and
// every job's row whenever there is a reading, so green is backed by four visible ages.
// The state ladder lives in useBackgroundJobs.deriveJobsState; this file only renders it.

const HEADLINE_TONE = {
  bad: 'text-red-600 dark:text-red-400',
  ok: 'text-text-primary dark:text-gray-100',
  unknown: 'text-text-primary dark:text-gray-100',
}

function Headline({ tone, children }) {
  return (
    <p className={`flex items-start gap-1.5 text-sm font-medium ${HEADLINE_TONE[tone]}`}>
      {/* mt-[7px] keeps the dot on the first line when the headline wraps on a phone (8D) */}
      <FreshnessDot tone={tone} className="mt-[7px]" />
      <span>{children}</span>
    </p>
  )
}

function Line({ children }) {
  return <p className="text-sm text-text-secondary dark:text-gray-400 mt-1 max-w-prose">{children}</p>
}

function Rows({ rows }) {
  return (
    <dl className="mt-4 space-y-3 sm:space-y-2">
      {rows.map((row) => (
        <div key={row.task} className="sm:grid sm:grid-cols-[11rem_1fr] sm:gap-x-4">
          <dt className="text-sm text-text-primary dark:text-gray-200">{row.label}</dt>
          <dd
            className={`text-sm ${
              row.overdue ? 'text-red-600 dark:text-red-400' : 'text-text-secondary dark:text-gray-400'
            }`}
          >
            {row.dateTime ? (
              <time dateTime={row.dateTime} title={row.title}>
                {row.text}
              </time>
            ) : (
              row.text
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function Body({ view }) {
  const checking = useDelayedFlag(Boolean(view.loading), 200)
  if (view.loading) {
    return checking ? <Headline tone="unknown">Checking…</Headline> : null
  }
  if (view.state === 1) {
    return (
      <>
        <Headline tone="unknown">{view.headline}</Headline>
        {view.lines.map((line) => (
          <Line key={line}>{line}</Line>
        ))}
      </>
    )
  }
  return (
    <>
      <Headline tone={view.tone}>{view.headline}</Headline>
      {view.lines.map((line) => (
        <Line key={line}>{line}</Line>
      ))}
      <Rows rows={view.rows} />
      {view.footnote && <p className="text-xs text-text-secondary dark:text-gray-400 mt-3">{view.footnote}</p>}
    </>
  )
}

export default function BackgroundJobsSection() {
  const view = useBackgroundJobs()

  // The one live region: announce only when the state NUMBER changes after the first
  // reading. Not on mount, not on loading → first reading, not on an age or footnote change,
  // not on a headline change inside one state ("Waiting for the first runs" → "Waiting on 2
  // jobs"). The previous state lives in a ref updated in an effect, never during render, so
  // Strict Mode's double render announces nothing extra; the text is written to the empty
  // node directly, so the announcement costs no re-render.
  const statusRef = useRef(null)
  const previousState = useRef(null)
  useEffect(() => {
    if (view.loading) return
    if (previousState.current !== null && previousState.current !== view.state && statusRef.current) {
      statusRef.current.textContent = announcementFor(view)
    }
    previousState.current = view.state
  })

  return (
    <section
      aria-labelledby="background-jobs"
      className="bg-card-bg dark:bg-gray-800 rounded-xl border border-card-border dark:border-gray-700 p-6 mt-6"
    >
      <h2
        id="background-jobs"
        tabIndex={-1}
        className="text-lg font-semibold text-text-primary dark:text-gray-100 mb-4 scroll-mt-20 sm:scroll-mt-6 focus:outline-none"
      >
        Background jobs
      </h2>
      <p className="text-sm text-text-secondary dark:text-gray-400 mb-3 max-w-prose">
        Work the app does on its own: iCloud sync and clearing out deleted items and unused photos.
      </p>
      <p ref={statusRef} role="status" className="sr-only" />
      <Body view={view} />
    </section>
  )
}
