// M2-only placeholder. Renders when VITE_M2_SHELL=true (Vercel prod build
// during M2-M5). Bypasses the full app routes so the production deploy can
// stand behind Cloudflare Access before any real auth/UI ships. Slice 5
// adds the "Test plumbing" button + cookie round-trip logic; M5 PR #2
// deletes this file in one git rm and removes the App.jsx env-gate.

import { useState } from 'react'

export default function PlumbingShell() {
  const [state, setState] = useState({ status: 'idle' })

  async function runTest() {
    // Read API base inside the handler so vitest's vi.stubEnv in tests
    // takes effect per-test instead of being captured at module import.
    const apiBase = import.meta.env.VITE_API_BASE_URL || ''
    setState({ status: 'loading' })

    let probe
    try {
      const postRes = await fetch(`${apiBase}/plumbing-test`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!postRes.ok) {
        setState({ status: 'post_failed', code: postRes.status })
        return
      }
      const postBody = await postRes.json()
      probe = postBody.probe
      if (typeof probe !== 'string' || probe.length === 0) {
        setState({ status: 'post_malformed' })
        return
      }
    } catch (err) {
      setState({ status: 'network_error', message: err.message, phase: 'post' })
      return
    }

    let value
    try {
      const getRes = await fetch(`${apiBase}/plumbing-test/read`, {
        method: 'GET',
        credentials: 'include',
        cache: 'no-store',
      })
      if (!getRes.ok) {
        setState({ status: 'get_failed', code: getRes.status })
        return
      }
      const getBody = await getRes.json()
      value = getBody.value
    } catch (err) {
      setState({ status: 'network_error', message: err.message, phase: 'get' })
      return
    }

    if (value === null || value === undefined) {
      setState({ status: 'cookie_missing', probe })
      return
    }
    if (value !== probe) {
      setState({ status: 'mismatch', probe, got: value })
      return
    }
    setState({ status: 'success', probe })
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="text-center max-w-lg">
        <h1 className="text-2xl font-semibold">M2 plumbing alive</h1>
        <p className="mt-2 text-gray-600">
          Production deploy skeleton. Auth, mealboard, and the rest of the
          app land in M3-M7.
        </p>
        <button
          type="button"
          onClick={runTest}
          disabled={state.status === 'loading'}
          className="mt-6 px-4 py-2 rounded bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {state.status === 'loading' ? 'Testing…' : 'Test plumbing'}
        </button>
        <ResultDisplay state={state} />
      </div>
    </main>
  )
}

function ResultDisplay({ state }) {
  if (state.status === 'idle' || state.status === 'loading') return null

  if (state.status === 'success') {
    return (
      <p className="mt-4 text-green-700" data-testid="plumbing-result">
        ✓ Cookie round-trip succeeded — probe matched exactly.
      </p>
    )
  }
  if (state.status === 'mismatch') {
    return (
      <p className="mt-4 text-red-700" data-testid="plumbing-result">
        ✗ Probe mismatch. Sent: {state.probe.slice(0, 12)}… Got: {state.got.slice(0, 12)}…
      </p>
    )
  }
  if (state.status === 'cookie_missing') {
    return (
      <p className="mt-4 text-red-700" data-testid="plumbing-result">
        ✗ Cookie not echoed back (value: null). Likely cause: SameSite,
        Secure, third-party-cookie, or __Host- attribute rejection.
      </p>
    )
  }
  if (state.status === 'post_failed') {
    return (
      <p className="mt-4 text-red-700" data-testid="plumbing-result">
        ✗ POST /plumbing-test failed (HTTP {state.code}).
      </p>
    )
  }
  if (state.status === 'post_malformed') {
    return (
      <p className="mt-4 text-red-700" data-testid="plumbing-result">
        ✗ POST returned an unexpected body (no probe string).
      </p>
    )
  }
  if (state.status === 'get_failed') {
    return (
      <p className="mt-4 text-red-700" data-testid="plumbing-result">
        ✗ GET /plumbing-test/read failed (HTTP {state.code}).
      </p>
    )
  }
  if (state.status === 'network_error') {
    return (
      <p className="mt-4 text-red-700" data-testid="plumbing-result">
        ✗ Network error during {state.phase}: {state.message}
      </p>
    )
  }
  return null
}
