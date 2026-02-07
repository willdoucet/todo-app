import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import Header from '../components/Header'
import MealboardNav from '../components/mealboard/MealboardNav'
import MealPlannerView from '../components/mealboard/MealPlannerView'
import RecipesView from '../components/mealboard/RecipesView'
import ShoppingListView from '../components/mealboard/ShoppingListView'
import RecipeFinderView from '../components/mealboard/RecipeFinderView'
import usePageTitle from '../hooks/usePageTitle'

export default function MealboardPage() {
  usePageTitle('Mealboard')

  return (
    <div className="min-h-screen bg-gradient-to-br from-warm-cream to-warm-beige dark:from-gray-900 dark:to-gray-800 sm:pl-20">
      <Sidebar />

      {/* Mobile Header - only visible below xl breakpoint */}
      <div className="xl:hidden">
        <Header />
      </div>

      {/* Main Layout */}
      <div className="flex h-screen xl:h-screen">
        {/* Left Navigation Panel - visible at xl and above */}
        <div className="hidden xl:flex flex-shrink-0">
          <MealboardNav variant="sidebar" />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <Routes>
            <Route index element={<Navigate to="planner" replace />} />
            <Route path="planner" element={<MealPlannerView />} />
            <Route path="recipes" element={<RecipesView />} />
            <Route path="shopping" element={<ShoppingListView />} />
            <Route path="finder" element={<RecipeFinderView />} />
          </Routes>
        </div>
      </div>
    </div>
  )
}
