import { createContext, useContext, useState, useCallback } from 'react'

const ToastContext = createContext(null)

let toastId = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, { type = 'error', duration = 4000 } = {}) => {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, duration)
    return id
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = useCallback({
    error: (msg) => addToast(msg, { type: 'error' }),
    success: (msg) => addToast(msg, { type: 'success', duration: 2000 }),
    info: (msg) => addToast(msg, { type: 'info' }),
  }, [addToast])

  // Workaround: useCallback doesn't work with object literal
  const api = { error: (msg) => addToast(msg, { type: 'error' }), success: (msg) => addToast(msg, { type: 'success', duration: 2000 }), info: (msg) => addToast(msg, { type: 'info' }) }

  return (
    <ToastContext.Provider value={api}>
      {children}

      {/* Toast container */}
      {toasts.length > 0 && (
        <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 max-w-sm" role="status" aria-live="assertive">
          {toasts.map(t => (
            <div
              key={t.id}
              className={`
                flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium
                animate-[fade-in_0.2s_ease-out]
                ${t.type === 'error'
                  ? 'bg-red-600 text-white dark:bg-red-700'
                  : t.type === 'success'
                  ? 'bg-sage-600 text-white dark:bg-green-700'
                  : 'bg-gray-800 text-white dark:bg-gray-700'}
              `}
              role="alert"
            >
              <span className="flex-1">{t.message}</span>
              <button
                onClick={() => removeToast(t.id)}
                className="text-white/70 hover:text-white transition-colors flex-shrink-0"
                aria-label="Dismiss"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
