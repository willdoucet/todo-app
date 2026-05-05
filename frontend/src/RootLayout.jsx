// Root layout for the data router. Mounts the provider stack ONCE for
// every protected route + /auth — DarkMode/Toast/UndoToast/QueryClient
// all live here. The data router renders <Outlet/> for the matching child
// route inside this tree.

import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { DarkModeProvider } from './contexts/DarkModeContext'
import { ToastProvider } from './components/shared/ToastProvider'
import { UndoToastProvider } from './components/shared/UndoToast'
import { createQueryClient } from './lib/queryClient'

export default function RootLayout() {
  // useState's lazy initializer is React Query's documented pattern for a
  // singleton client — useMemo is a perf hint React may discard, which would
  // wipe the query cache.
  const [queryClient] = useState(() => createQueryClient())

  return (
    <QueryClientProvider client={queryClient}>
      <DarkModeProvider>
        <ToastProvider>
          <UndoToastProvider>
            <Outlet />
          </UndoToastProvider>
        </ToastProvider>
      </DarkModeProvider>
    </QueryClientProvider>
  )
}
