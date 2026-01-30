import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import FamilyMemberManager from '../components/FamilyMemberManager'

export default function FamilyMembersPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 sm:pl-20">
      <Sidebar />
      <Header />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 dark:text-gray-100 tracking-tight mb-6 sm:mb-8">
          Settings
        </h1>
        
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <FamilyMemberManager />
        </div>
      </main>
    </div>
  )
}