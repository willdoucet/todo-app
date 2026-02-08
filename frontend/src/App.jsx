import { Routes, Route } from 'react-router-dom'
import CalendarPage from './components/calendar/CalendarPage'
import ListsPage from './pages/ListsPage'
import ResponsibilitiesPage from './pages/ResponsibilitiesPage'
import FamilyMembersPage from './pages/FamilyMembersPage'
import MealboardPage from './pages/MealboardPage'

export default function App() {
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