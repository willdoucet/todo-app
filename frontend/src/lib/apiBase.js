// Single source of truth for the backend origin. Request callers (axios
// instance, raw refresh) and image renderers (<img src> for /uploads/...)
// both consume from here so VITE_API_BASE_URL is read in exactly one place.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Resolve a backend asset path to an absolute URL. Pass-through for
// already-absolute http(s) URLs and for empty/nullish inputs so callers
// don't have to branch.
export function apiUrl(path) {
  if (!path) return path
  if (/^https?:\/\//i.test(path)) return path
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}
