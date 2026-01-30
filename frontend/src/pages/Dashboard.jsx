import { Link } from 'react-router-dom'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 sm:pl-20">
      <Sidebar />
      <Header />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Tasks Card */}
          <Link
            to="/tasks"
            className="
              group relative bg-white dark:bg-gray-800 rounded-xl 
              border border-gray-200 dark:border-gray-700
              p-6 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-lg 
              transition-all duration-200 cursor-pointer
            "
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50 transition-colors">
                <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <svg className="w-5 h-5 text-gray-400 dark:text-gray-500 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
              Tasks
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Manage your tasks and stay organized with our task manager.
            </p>
          </Link>

          {/* Placeholder Card 1 */}
          <div className="
            relative bg-white dark:bg-gray-800 rounded-xl 
            border border-gray-200 dark:border-gray-700
            p-6 opacity-50
          ">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-700">
                <svg className="w-6 h-6 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
            </div>
            <h2 className="text-lg font-semibold text-gray-500 dark:text-gray-400 mb-2">
              Coming Soon
            </h2>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Additional features will be available here.
            </p>
          </div>

          {/* Placeholder Card 2 */}
          <div className="
            relative bg-white dark:bg-gray-800 rounded-xl 
            border border-gray-200 dark:border-gray-700
            p-6 opacity-50
          ">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-700">
                <svg className="w-6 h-6 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
            </div>
            <h2 className="text-lg font-semibold text-gray-500 dark:text-gray-400 mb-2">
              Coming Soon
            </h2>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Additional features will be available here.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
