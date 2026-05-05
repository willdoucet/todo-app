// Open-redirect defense for ?return_to=... values pulled out of the URL
// at /auth. A malicious or accidental link like ?return_to=https://evil.com
// after login would otherwise let an attacker bounce a victim's freshly
// authenticated browser to an arbitrary origin.
//
// /auth* paths are also rejected — otherwise a self-loop becomes possible
// (?return_to=/auth → log in → land back on /auth → ?return_to=/auth → …).

const SAFE_PATH_REGEX = /^\/(?!\/)/

export function isSafeReturnTo(value) {
  if (typeof value !== 'string' || value.length === 0) return false

  // Reject control characters (newlines, carriage returns, NULs, etc.) before
  // any further parsing — header injection and URL-parser quirks both live
  // here.
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i)
    if (code < 0x20 || code === 0x7f) return false
  }

  // Must start with a single leading slash — and not two (which is a
  // protocol-relative URL, e.g. //evil.com).
  if (!SAFE_PATH_REGEX.test(value)) return false

  // No protocol component allowed mid-string (defensive belt + suspenders).
  if (value.includes('://')) return false

  // /auth and /auth/* both redirect-loop; reject. Match the bare path
  // segment so an accidental /authsomethingelse legitimate route would
  // still pass.
  if (value === '/auth' || value.startsWith('/auth?') || value.startsWith('/auth/')) {
    return false
  }

  return true
}

// Convenience wrapper: returns the input when safe, otherwise null. Callers
// fall back to '/' when null.
export function safeReturnTo(value) {
  return isSafeReturnTo(value) ? value : null
}
