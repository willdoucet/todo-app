import { Routes, Route } from 'react-router-dom'
import CalendarPage from './components/calendar/CalendarPage'
import ListsPage from './pages/ListsPage'
import ResponsibilitiesPage from './pages/ResponsibilitiesPage'
import FamilyMembersPage from './pages/FamilyMembersPage'
import MealboardPage from './pages/MealboardPage'
import PlumbingShell from './PlumbingShell'

export default function App() {
  // Vercel prod build sets VITE_M2_SHELL=true to swap the full app for the
  // M2 placeholder shell. Local docker-compose, CI, and visual-tests leave
  // it unset → the existing Routes tree renders unchanged.
  if (import.meta.env.VITE_M2_SHELL === 'true') {
    return <PlumbingShell />
  }
  return (
    <Routes>
      <Route path="/" element={<CalendarPage />} />
      <Route path="/lists" element={<ListsPage />} />
      <Route path="/responsibilities" element={<ResponsibilitiesPage />} />
      <Route path="/settings" element={<FamilyMembersPage />} />
      <Route path="/mealboard/*" element={<MealboardPage />} />
    </Routes>
  )
}