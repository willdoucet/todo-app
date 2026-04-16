import { useState, useEffect } from 'react'

export default function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(query).matches
  )

  useEffect(() => {
    const mql = window.matchMedia(query)
    const handler = (e) => setMatches(e.matches)
    mql.addEventListener('change', handler)
    // Resync after subscribing in case the query value changed between the
    // initial useState lazy-init and the effect running. This is the
    // canonical "subscribe + sync" pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMatches(mql.matches)
    return () => mql.removeEventListener('change', handler)
  }, [query])

  return matches
}
