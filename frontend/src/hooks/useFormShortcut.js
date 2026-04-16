import { useEffect } from 'react'

/**
 * Wires Cmd+S / Ctrl+S to submit a form via requestSubmit().
 * Prevents the browser's native "Save" dialog.
 */
export default function useFormShortcut(formRef) {
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        formRef.current?.requestSubmit()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [formRef])
}
