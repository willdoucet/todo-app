import { useEffect, useState } from 'react'

// Returns true only after `flag` has been true for at least `delayMs`.
// Intended use: gate a loading indicator so it never appears for fast loads.
// For loads faster than delayMs, the return value stays false the entire time,
// because `flag` flips back to false (load finished) before the timer fires.
export default function useDelayedFlag(flag, delayMs = 200) {
  const [delayed, setDelayed] = useState(false)
  useEffect(() => {
    // Reset on flag change so a true → false → true cycle re-arms the delay.
    // The effect-driven setState is the correct shape here: the hook owns its
    // internal timer and must reset its own state when the input flips.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!flag) { setDelayed(false); return }
    const id = setTimeout(() => setDelayed(true), delayMs)
    return () => clearTimeout(id)
  }, [flag, delayMs])
  return flag && delayed
}
