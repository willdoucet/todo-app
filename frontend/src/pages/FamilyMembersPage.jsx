import Header from '../components/layout/Header'
import Sidebar from '../components/layout/Sidebar'
import FamilyMemberManager from '../components/family-members/FamilyMemberManager'
import TimezoneSettings from '../components/settings/TimezoneSettings'
import ICloudSettings from '../components/settings/ICloudSettings'
import usePageTitle from '../hooks/usePageTitle'

export default function FamilyMembersPage() {
  usePageTitle('Settings')

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

        <div className="bg-card-bg dark:bg-gray-800 rounded-xl border border-card-border dark:border-gray-700 p-6 mt-6">
          <h2 className="text-lg font-semibold text-text-primary dark:text-gray-100 mb-4">
            Timezone
          </h2>
          <p className="text-sm text-text-muted dark:text-gray-400 mb-3">
            Synced calendar events will be displayed in this timezone.
          </p>
          <TimezoneSettings />
        </div>

        <div className="bg-card-bg dark:bg-gray-800 rounded-xl border border-card-border dark:border-gray-700 p-6 mt-6">
          <h2 className="text-lg font-semibold text-text-primary dark:text-gray-100 mb-4">
            Calendar Integrations
          </h2>
          <ICloudSettings />
        </div>
      </main>
    </div>
  )
}
