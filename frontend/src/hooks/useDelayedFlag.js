import { useEffect, useState } from 'react'

// Returns true only after `flag` has been true for at least `delayMs`.
// Intended use: gate a loading indicator so it never appears for fast loads.
// For loads faster than delayMs, the return value stays false the entire time,
// because `flag` flips back to false (load finished) before the timer fires.
export default function useDelayedFlag(flag, delayMs = 200) {
  const [delayed, setDelayed] = useState(false)
  useEffect(() => {
    if (!flag) { setDelayed(false); return }
    const id = setTimeout(() => setDelayed(true), delayMs)
    return () => clearTimeout(id)
  }, [flag, delayMs])
  return flag && delayed
}
