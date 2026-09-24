import FreshnessDot from '../shared/FreshnessDot'
import useBackgroundJobs from '../../hooks/useBackgroundJobs'

// The one-line top alert under the Settings title (M8 item 15a). Rendered only in states
// 2–4 — a job behind, all stopped, or runs that can't be recorded — never for "can't
// check", waiting, running or loading. Plain text in reading order right after the h1: not
// role="alert" (it would interrupt every visit while a job is behind), no dismiss control
// (a dismissible outage warning is how an outage gets ignored), and no container, tint,
// border or icon (Design review, "Do not build"). The card announces changes; this never does.

function jumpToBackgroundJobs(event) {
  // No hash change: it would push a history entry through the data router.
  event.preventDefault()
  const heading = document.getElementById('background-jobs')
  if (!heading) return
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
  heading.scrollIntoView?.({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
  heading.focus({ preventScroll: true })
}

export default function BackgroundJobsAlert() {
  const view = useBackgroundJobs()
  if (!view.alert) return null

  return (
    // Inline text, not flex, so it wraps like a sentence at 375 px (8D). red-700, not red-600:
    // it sits on the page gradient, where red-600 is 4.3:1 at the warm-beige end (Design review 6).
    <p className="mt-2 text-sm text-red-700 dark:text-red-400">
      <FreshnessDot tone="bad" className="align-middle mr-1.5 mb-0.5" />
      {view.alert} <span aria-hidden="true">·</span>{' '}
      <a
        href="#background-jobs"
        onClick={jumpToBackgroundJobs}
        className="py-3 sm:py-0 whitespace-nowrap font-medium text-terracotta-700 dark:text-blue-400 underline underline-offset-2 hover:decoration-2 rounded focus:outline-none focus:ring-2 focus:ring-terracotta-500 dark:focus:ring-blue-500"
      >
        See background jobs
      </a>
    </p>
  )
}
