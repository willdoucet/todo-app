import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import FamilyMemberManager from '../components/FamilyMemberManager'

export default function FamilyMembersPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-warm-cream to-warm-beige dark:from-gray-900 dark:to-gray-800 sm:pl-20">
      <Sidebar />
      <Header />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-text-primary dark:text-gray-100 tracking-tight mb-6 sm:mb-8">
          Settings
        </h1>

        <div className="bg-card-bg dark:bg-gray-800 rounded-xl border border-card-border dark:border-gray-700 p-6">
          <FamilyMemberManager />
        </div>
      </main>
    </div>
  )
}