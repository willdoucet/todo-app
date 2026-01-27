import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import TaskPage from './pages/TaskPage'
import FamilyMembersPage from './pages/FamilyMembersPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/tasks" element={<TaskPage />} />
      <Route path="/settings" element={<FamilyMembersPage />} />
    </Routes>
  )
}