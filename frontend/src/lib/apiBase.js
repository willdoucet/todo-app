// Single source of truth for the backend origin. Request callers (axios
// instance, raw refresh) and image renderers (<img src> for /uploads/...)
// both consume from here so VITE_API_BASE_URL is read in exactly one place.

const _RAW_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Belt-and-suspenders: if the page is loaded over HTTPS, never let an
// http:// API base reach the network — auto-upgrade to https://.
// Localhost/loopback are exempt (developers running an HTTPS frontend
// against an HTTP backend on their machine is a legitimate dev setup).
//
// The real fix lives in the backend (uvicorn --proxy-headers so FastAPI's
// trailing-slash redirects emit https:// Location headers). This layer
// catches the same class of bug if a future env-var typo or backend
// regression reintroduces an http:// URL on the request path.
function _upgradeProtocolIfNeeded(url) {
  if (typeof window === 'undefined') return url
  if (window.location?.protocol !== 'https:') return url
  if (!/^http:\/\//i.test(url)) return url
  if (/^http:\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0)([:/]|$)/i.test(url)) return url
  return 'https://' + url.slice('http://'.length)
}

export const API_BASE_URL = _upgradeProtocolIfNeeded(_RAW_API_BASE_URL)

// Resolve a backend asset path to an absolute URL. Pass-through for
// already-absolute http(s) URLs and for empty/nullish inputs so callers
// don't have to branch.
export function apiUrl(path) {
  if (!path) return path
  if (/^https?:\/\//i.test(path)) return path
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}
