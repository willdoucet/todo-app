import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import TodoPage from './pages/TodoPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/todo" element={<TodoPage />} />
    </Routes>
  )
}