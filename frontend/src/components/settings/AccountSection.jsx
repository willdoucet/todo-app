import { useNavigate } from 'react-router-dom'
import { useLogoutMutation } from '../../lib/auth/queries'
import { useToast } from '../shared/ToastProvider'

// Smallest-possible logout entry. The mutation hook waits for any in-flight
// refresh to settle before posting /auth/logout (so a late refresh response
// cannot resurrect the in-memory token), and fail-closes locally on
// onSettled regardless of server outcome.
//
// The HttpOnly refresh cookie cannot be cleared from JS, so a 5xx/network/
// timeout on logout means the local UI is signed out but the server may
// still hold a valid refresh token until expiry. The toast is honest about
// that limitation.

export default function AccountSection() {
  const navigate = useNavigate()
  const toast = useToast()

  const logout = useLogoutMutation({
    onSettled: (_data, error) => {
      if (error) {
        toast.error(
          "Signed out on this device. We couldn't confirm with the server — sign out again later if this is a shared device.",
        )
      }
      navigate('/auth', { replace: true })
    },
  })

  return (
    <div className="bg-card-bg dark:bg-gray-800 rounded-xl border border-card-border dark:border-gray-700 p-6 mt-6">
      <h2 className="text-lg font-semibold text-text-primary dark:text-gray-100 mb-4">
        Account
      </h2>
      <button
        type="button"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
        className="px-4 py-2.5 bg-warm-sand dark:bg-gray-700 text-text-secondary dark:text-gray-300 hover:bg-warm-beige rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-terracotta-500 inline-flex items-center gap-2 w-full sm:w-auto justify-center"
      >
        {logout.isPending ? (
          <>
            <svg
              className="animate-spin"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
              <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
            <span>Signing out…</span>
          </>
        ) : (
          <span>Sign out</span>
        )}
      </button>
    </div>
  )
}
