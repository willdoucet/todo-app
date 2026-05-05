// TanStack Query hooks for the /auth/* surface. Login/register/logout
// run through `api`, NOT raw axios — the response interceptor's
// /auth/* URL guard prevents a wrong-password 401 from triggering a
// refresh storm.

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { api } from '../api'
import { tokenStore } from './tokenStore'
import { performRefresh, setLoggingOut, waitForRefreshToSettle } from './refresh'

export const AUTH_STATUS_KEY = ['auth', 'status']

export function useAuthStatus() {
  return useQuery({
    queryKey: AUTH_STATUS_KEY,
    queryFn: async () => {
      const { data } = await api.get('/auth/status')
      return data
    },
  })
}

export function useLoginMutation({ onSuccess } = {}) {
  return useMutation({
    mutationFn: async ({ email, password }) => {
      const { data } = await api.post('/auth/login', { email, password })
      return data
    },
    onSuccess: (data) => {
      if (typeof data?.access_token === 'string') {
        tokenStore.setToken(data.access_token)
      }
      onSuccess?.(data)
    },
  })
}

export function useRegisterMutation({ onSuccess } = {}) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ email, password, access_key }) => {
      const { data } = await api.post('/auth/register', {
        email,
        password,
        access_key,
      })
      return data
    },
    onSuccess: (data) => {
      // Invalidate before setting token + navigating so the next mount of
      // /auth (e.g., user logs out within 30s) refetches /auth/status and
      // renders LoginForm rather than a stale SetupForm.
      queryClient.invalidateQueries({ queryKey: AUTH_STATUS_KEY })
      if (typeof data?.access_token === 'string') {
        tokenStore.setToken(data.access_token)
      }
      onSuccess?.(data)
    },
    onError: (err) => {
      // 409 is kept for older/mixed-version responses that explicitly reveal
      // account-exists. Current backend returns byte-identical 401 for wrong
      // key and account-exists; AuthPortalPage refetches status before showing
      // copy so it can distinguish those without leaking through this hook.
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        queryClient.invalidateQueries({ queryKey: AUTH_STATUS_KEY })
      }
    },
  })
}

export function useLogoutMutation({ onSettled } = {}) {
  return useMutation({
    mutationFn: async () => {
      // First let any existing refresh land, then proactively mint a fresh
      // bearer for /auth/logout. Logout is an /auth/* endpoint, so the api
      // interceptor deliberately will not refresh-retry a 401 for us.
      await waitForRefreshToSettle()
      try {
        await performRefresh()
      } catch {
        // Best effort: if refresh is unavailable, try the current bearer.
        // onSettled still fail-closes locally and tells the user if the
        // server-side revocation could not be confirmed.
      }
      // Block any refresh that starts after the logout click from writing a
      // new token while the logout request is in flight.
      setLoggingOut(true)
      await api.post('/auth/logout')
      return { ok: true }
    },
    // onSettled runs in BOTH success and error branches — fail-closed
    // local state regardless of what the server reported.
    onSettled: (data, error) => {
      tokenStore.clear()
      setLoggingOut(false)
      onSettled?.(data, error)
    },
  })
}
