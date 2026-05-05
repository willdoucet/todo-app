// /auth — single auto-discriminated route. /auth/status's account_exists
// flag tells us whether to render the login form or the first-run setup
// form. No mode toggle UI is rendered: this is a single-family deploy and
// register is a one-time operator event.
//
// Already-authenticated users typing /auth bounce to safeReturnTo() ?? '/'
// without ever rendering a form.

import { forwardRef, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'

import { tokenStore } from '../lib/auth/tokenStore'
import {
  resetRedirectGuard,
} from '../lib/auth/redirect'
import { safeReturnTo } from '../lib/auth/returnTo'
import {
  useAuthStatus,
  useLoginMutation,
  useRegisterMutation,
} from '../lib/auth/queries'

const COPY = {
  login: {
    headline: 'Welcome back',
    subhead: 'Sign in to your household',
    submit: 'Sign in',
    submitting: 'Signing in…',
  },
  setup: {
    headline: 'Set up your household',
    subhead: 'First time here? Create the operator account.',
    submit: 'Create household',
    submitting: 'Creating…',
  },
  bounce: 'Your session ended. Sign in to pick up where you left off.',
  status5xx: {
    headline: "Can't reach the server",
    body: 'Try again, or contact your operator if it persists.',
    button: 'Try again',
  },
  errors: {
    login: {
      401: 'Invalid email or password',
      429: 'Too many attempts. Please wait a moment.',
      422: 'Please check the fields and try again.',
      networkOr5xx: "Couldn't reach the server. Try again.",
    },
    register: {
      401: 'Invalid household access key',
      429: 'Too many attempts. Please wait a moment.',
      422: 'Please check the fields and try again.',
      networkOr5xx: "Couldn't reach the server. Try again.",
    },
  },
}

function classifyMutationError(error, surface) {
  if (!axios.isAxiosError(error)) {
    return COPY.errors[surface].networkOr5xx
  }
  const status = error.response?.status
  if (status === 401) return COPY.errors[surface][401]
  if (status === 429) return COPY.errors[surface][429]
  if (status === 422) return COPY.errors[surface][422]
  // 5xx, network, timeout, and any other non-401/409/429 land here.
  return COPY.errors[surface].networkOr5xx
}

export default function AuthPortalPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const returnToRaw = searchParams.get('return_to')
  const safeReturn = safeReturnTo(returnToRaw)
  const showBounceBanner = returnToRaw !== null

  // Reset the one-shot auth-redirect guard on EVERY mount, including the
  // already-logged-in short-circuit path that never renders the form.
  // Without this, a second redirect storm in the same session would no-op.
  useEffect(() => {
    resetRedirectGuard()
  }, [])

  // Already-logged-in short-circuit. Run synchronously on first render so
  // the form never flashes for a user who hits /auth directly while
  // signed in.
  useEffect(() => {
    if (tokenStore.getSnapshot() !== null) {
      navigate(safeReturn ?? '/', { replace: true })
    }
  }, [navigate, safeReturn])

  // Status fetch decides which form to render.
  const status = useAuthStatus()

  if (status.isLoading) {
    return <Centered><StatusSkeleton /></Centered>
  }

  if (status.isError) {
    return (
      <Centered>
        <Card>
          <Wordmark />
          <ErrorBanner data-testid="status-error">
            <h2 className="text-lg font-medium text-text-primary dark:text-gray-100">
              {COPY.status5xx.headline}
            </h2>
            <p className="text-sm text-text-secondary dark:text-gray-400 mt-1">
              {COPY.status5xx.body}
            </p>
            <button
              type="button"
              className="mt-3 inline-flex px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-terracotta-500"
              onClick={() => status.refetch()}
            >
              {COPY.status5xx.button}
            </button>
          </ErrorBanner>
        </Card>
      </Centered>
    )
  }

  // Defensive: a backend bug returning {} or non-boolean account_exists
  // must default to LoginForm. The setup form requires a positive `false`.
  const data = status.data
  const showSetup = data?.account_exists === false

  return (
    <Centered>
      <Card>
        <Wordmark />
        {showSetup ? (
          <SetupForm
            statusLoading={status.isLoading}
            statusRefetch={status.refetch}
            safeReturn={safeReturn}
            navigate={navigate}
          />
        ) : (
          <LoginForm
            statusLoading={status.isLoading}
            safeReturn={safeReturn}
            navigate={navigate}
            showBounceBanner={showBounceBanner}
          />
        )}
      </Card>
    </Centered>
  )
}

function Centered({ children }) {
  return (
    <div className="min-h-screen flex items-start sm:items-center justify-center px-4 py-8 bg-warm-cream dark:bg-gray-900">
      {children}
    </div>
  )
}

function Card({ children }) {
  return (
    <div className="w-full max-w-md rounded-xl bg-card-bg dark:bg-gray-800 border border-card-border dark:border-gray-700 p-6 sm:p-8">
      {children}
    </div>
  )
}

function Wordmark() {
  return (
    <div className="flex items-center gap-2.5 leading-none">
      <span
        aria-hidden="true"
        className="inline-block w-3 h-3 rounded-full bg-terracotta-500"
      />
      <span className="text-3xl font-bold tracking-tight text-text-primary dark:text-gray-100">
        Mealy
      </span>
    </div>
  )
}

function StatusSkeleton() {
  return (
    <Card>
      <Wordmark />
      <div className="mt-6 space-y-3 animate-pulse">
        <div className="h-5 bg-warm-sand dark:bg-gray-700 rounded w-2/3" />
        <div className="h-4 bg-warm-sand dark:bg-gray-700 rounded w-1/2" />
        <div className="mt-6 space-y-4">
          <div className="h-10 bg-warm-sand dark:bg-gray-700 rounded-lg" />
          <div className="h-10 bg-warm-sand dark:bg-gray-700 rounded-lg" />
          <div className="h-10 bg-terracotta-200 dark:bg-gray-600 rounded-lg" />
        </div>
      </div>
    </Card>
  )
}

const ErrorBanner = forwardRef(function ErrorBanner({ children, ...rest }, ref) {
  return (
    <div
      ref={ref}
      role="alert"
      aria-live="polite"
      className="mt-6 rounded-lg bg-terracotta-100 dark:bg-orange-900/30 border border-terracotta-200 dark:border-orange-900/50 px-3 py-2 text-sm text-terracotta-700 dark:text-orange-300"
      {...rest}
    >
      {children}
    </div>
  )
})

function BounceBanner() {
  return (
    <div
      className="mt-6 rounded-lg bg-terracotta-50 dark:bg-orange-900/20 border border-terracotta-100 dark:border-orange-900/40 px-3 py-2 text-sm text-text-secondary dark:text-gray-300"
    >
      {COPY.bounce}
    </div>
  )
}

function PasswordInput({
  id,
  label,
  value,
  onChange,
  autoComplete,
  required = true,
  describedBy,
}) {
  const [shown, setShown] = useState(false)
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-text-primary dark:text-gray-300 mb-1"
      >
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={shown ? 'text' : 'password'}
          autoComplete={autoComplete}
          required={required}
          aria-describedby={describedBy}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 pr-10 border border-card-border dark:border-gray-600 rounded-lg bg-card-bg dark:bg-gray-800 text-text-primary dark:text-gray-100 placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-terracotta-500"
        />
        <button
          type="button"
          aria-label={shown ? 'Hide password' : 'Show password'}
          onClick={() => setShown((s) => !s)}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-text-secondary focus:outline-none focus:ring-2 focus:ring-terracotta-500 rounded"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            {shown ? (
              <>
                <path d="M3 3l18 18" />
                <path d="M10.58 10.58a2 2 0 0 0 2.83 2.83" />
                <path d="M9.88 5.06A10.94 10.94 0 0 1 12 5c7 0 11 7 11 7a17 17 0 0 1-3.06 3.79M6.61 6.61A17 17 0 0 0 1 12s4 7 11 7a10.94 10.94 0 0 0 5.39-1.39" />
              </>
            ) : (
              <>
                <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" />
                <circle cx="12" cy="12" r="3" />
              </>
            )}
          </svg>
        </button>
      </div>
    </div>
  )
}

function TextInput({
  id,
  label,
  type = 'text',
  value,
  onChange,
  autoComplete,
  required = true,
  autoFocus = false,
  helperId,
  helperText,
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-text-primary dark:text-gray-300 mb-1"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        autoComplete={autoComplete}
        required={required}
        autoFocus={autoFocus}
        aria-describedby={helperId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-card-border dark:border-gray-600 rounded-lg bg-card-bg dark:bg-gray-800 text-text-primary dark:text-gray-100 placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-terracotta-500"
      />
      {helperText ? (
        <p id={helperId} className="mt-1 text-xs text-text-muted dark:text-gray-500">
          {helperText}
        </p>
      ) : null}
    </div>
  )
}

function SubmitButton({ disabled, label, submittingLabel, isPending }) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="w-full px-4 py-2 bg-terracotta-500 hover:bg-terracotta-600 disabled:bg-terracotta-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-terracotta-500 inline-flex items-center justify-center gap-2"
    >
      {isPending ? (
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
      ) : null}
      <span>{isPending ? submittingLabel : label}</span>
    </button>
  )
}

function LoginForm({ statusLoading, safeReturn, navigate, showBounceBanner }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMsg, setErrorMsg] = useState(null)
  const errorRef = useRef(null)

  const mutation = useLoginMutation({
    onSuccess: () => {
      navigate(safeReturn ?? '/', { replace: true })
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    setErrorMsg(null)
    mutation.mutate(
      { email, password },
      {
        onError: (err) => {
          setErrorMsg(classifyMutationError(err, 'login'))
          // Move keyboard focus to the alert so screen-reader users hear it
          // and TAB lands on the retry button next.
          requestAnimationFrame(() => errorRef.current?.focus())
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1 className="text-lg font-medium text-text-primary dark:text-gray-100 mt-6">
        {COPY.login.headline}
      </h1>
      <p className="text-sm text-text-secondary dark:text-gray-400 mt-1">
        {COPY.login.subhead}
      </p>

      {showBounceBanner ? <BounceBanner /> : null}
      {errorMsg ? (
        <ErrorBanner ref={errorRef} tabIndex={-1}>
          {errorMsg}
        </ErrorBanner>
      ) : null}

      <div className="mt-6 space-y-4">
        <TextInput
          id="login-email"
          label="Email"
          type="email"
          autoComplete="email"
          autoFocus
          value={email}
          onChange={setEmail}
        />
        <PasswordInput
          id="login-password"
          label="Password"
          autoComplete="current-password"
          value={password}
          onChange={setPassword}
        />
        <SubmitButton
          disabled={mutation.isPending || statusLoading}
          isPending={mutation.isPending}
          label={COPY.login.submit}
          submittingLabel={COPY.login.submitting}
        />
      </div>
    </form>
  )
}

function SetupForm({ statusLoading, statusRefetch, safeReturn, navigate }) {
  const accessKeyHelpId = 'access-key-help'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [accessKey, setAccessKey] = useState('')
  const [errorMsg, setErrorMsg] = useState(null)
  const errorRef = useRef(null)

  const mutation = useRegisterMutation({
    onSuccess: () => {
      navigate(safeReturn ?? '/', { replace: true })
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    setErrorMsg(null)
    if (password !== confirm) {
      setErrorMsg('Passwords do not match.')
      requestAnimationFrame(() => errorRef.current?.focus())
      return
    }
    mutation.mutate(
      { email, password, access_key: accessKey },
      {
        onError: async (err) => {
          // Backend returns the same 401 for "wrong key" and "account already
          // exists" to avoid leaking setup state. Refetch status before showing
          // copy; if another request claimed the account, the parent flips to
          // LoginForm instead of blaming the key.
          if (axios.isAxiosError(err) && err.response?.status === 401) {
            const refreshed = await statusRefetch()
            if (refreshed.data?.account_exists === true) {
              return
            }
          }
          if (axios.isAxiosError(err) && err.response?.status === 409) {
            return
          }
          setErrorMsg(classifyMutationError(err, 'register'))
          requestAnimationFrame(() => errorRef.current?.focus())
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1 className="text-lg font-medium text-text-primary dark:text-gray-100 mt-6">
        {COPY.setup.headline}
      </h1>
      <p className="text-sm text-text-secondary dark:text-gray-400 mt-1">
        {COPY.setup.subhead}
      </p>

      {errorMsg ? (
        <ErrorBanner ref={errorRef} tabIndex={-1}>
          {errorMsg}
        </ErrorBanner>
      ) : null}

      <div className="mt-6 space-y-4">
        <TextInput
          id="setup-email"
          label="Email"
          type="email"
          autoComplete="email"
          autoFocus
          value={email}
          onChange={setEmail}
        />
        <PasswordInput
          id="setup-password"
          label="Password"
          autoComplete="new-password"
          value={password}
          onChange={setPassword}
        />
        <PasswordInput
          id="setup-confirm"
          label="Confirm password"
          autoComplete="new-password"
          value={confirm}
          onChange={setConfirm}
        />
        <PasswordInput
          id="setup-access-key"
          label="Household access key"
          autoComplete="off"
          value={accessKey}
          onChange={setAccessKey}
          describedBy={accessKeyHelpId}
        />
        <p
          id={accessKeyHelpId}
          className="-mt-3 text-xs text-text-muted dark:text-gray-500"
        >
          From your server config (HOUSEHOLD_ACCESS_KEY).
        </p>
        <SubmitButton
          disabled={mutation.isPending || statusLoading}
          isPending={mutation.isPending}
          label={COPY.setup.submit}
          submittingLabel={COPY.setup.submitting}
        />
      </div>
    </form>
  )
}
