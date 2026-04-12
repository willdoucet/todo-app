export default function ToolbarCount({ count, totalCount, singular, plural }) {
  const label = totalCount != null && count !== totalCount
    ? `${count} of ${totalCount}`
    : `${count} ${count === 1 ? singular : plural}`
  return (
    <span className="text-xs text-text-muted dark:text-gray-400 whitespace-nowrap hidden sm:inline">
      {label}
    </span>
  )
}
