import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { DarkModeProvider } from './contexts/DarkModeContext'
import { ToastProvider } from './components/shared/ToastProvider'
import { UndoToastProvider } from './components/shared/UndoToast'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <DarkModeProvider>
        <ToastProvider>
          <UndoToastProvider>
            <App />
          </UndoToastProvider>
        </ToastProvider>
      </DarkModeProvider>
    </BrowserRouter>
  </StrictMode>,
)
