import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ListsPage from './pages/ListsPage'
import ResponsibilitiesPage from './pages/ResponsibilitiesPage'
import FamilyMembersPage from './pages/FamilyMembersPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/lists" element={<ListsPage />} />
      <Route path="/responsibilities" element={<ResponsibilitiesPage />} />
      <Route path="/settings" element={<FamilyMembersPage />} />
    </Routes>
  )
}