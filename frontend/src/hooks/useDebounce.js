import { useRef, useCallback } from 'react'

export default function useDebounce(fn, delay = 500) {
  const timerRef = useRef(null)
  return useCallback((...args) => {
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => fn(...args), delay)
  }, [fn, delay])
}
