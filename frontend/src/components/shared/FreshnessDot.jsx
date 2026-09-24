// The 6 px status dot beside a freshness line: the iCloud "Last synced" line and the
// Background jobs headline and top alert (M8 item 15a). It renders no text, because every
// caller puts the words beside it — the dot is never the only signal (WCAG 1.4.1), so it
// is aria-hidden. Success is the sage token, not stock green (Design review 5A).
const TONES = {
  ok: 'bg-sage-500 dark:bg-green-400',
  bad: 'bg-red-500 dark:bg-red-400',
  unknown: 'bg-text-muted dark:bg-gray-500',
}

export default function FreshnessDot({ tone, className = '' }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${TONES[tone] ?? TONES.unknown} ${className}`.trim()}
    />
  )
}
