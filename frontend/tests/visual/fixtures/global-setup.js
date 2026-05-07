// M5 PR1 — auth-aware seeding. The api-test stack now requires auth on
// every protected route (the seed flow uses /items, /meal-entries, etc.)
// so globalSetup mints a real JWT before seedKnownWeek runs.
//
// Idempotency: the api-test DB persists across runs locally. M3's
// /auth/register is closed once any account exists, so we try login
// first and only register on 401. In CI, `down -v` runs after every
// visual-tests job, so each CI run starts with a fresh DB and the
// register-on-401 path always succeeds.
import { seedKnownWeek } from './seed.js'
import fs from 'node:fs'

const API_URL = process.env.API_URL || 'http://localhost:8000'
// EmailStr requires a valid TLD — `@local` (no dot) fails Pydantic
// validation with 422, breaking globalSetup. `@example.com` is the
// IETF reserved test domain (RFC 2606).
const FIXTURE_EMAIL = process.env.VISUAL_TEST_USER_EMAIL || 'visual-test@example.com'
const FIXTURE_PASSWORD =
  process.env.VISUAL_TEST_USER_PASSWORD || 'visual-test-pw-do-not-use-in-prod'
const HOUSEHOLD_KEY = process.env.HOUSEHOLD_ACCESS_KEY

async function loginOrRegister() {
  // Try login first (works on subsequent runs against a persistent DB).
  const loginRes = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: FIXTURE_EMAIL, password: FIXTURE_PASSWORD }),
  })
  if (loginRes.ok) {
    const body = await loginRes.json()
    return body.access_token
  }
  if (loginRes.status !== 401) {
    throw new Error(`globalSetup: unexpected login status ${loginRes.status}`)
  }
  // 401 → user doesn't exist yet. Register, then login.
  if (!HOUSEHOLD_KEY) {
    throw new Error('globalSetup: HOUSEHOLD_ACCESS_KEY env var not set')
  }
  // RegisterIn schema (app/auth/schemas.py L18-28) expects field name
  // `access_key`, NOT `household_access_key`. Wrong field name → 422.
  const regRes = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: FIXTURE_EMAIL,
      password: FIXTURE_PASSWORD,
      access_key: HOUSEHOLD_KEY,
    }),
  })
  if (!regRes.ok) {
    const text = await regRes.text().catch(() => '<unreadable body>')
    throw new Error(`globalSetup: register failed ${regRes.status}: ${text}`)
  }
  const loginRes2 = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: FIXTURE_EMAIL, password: FIXTURE_PASSWORD }),
  })
  if (!loginRes2.ok) {
    throw new Error(`globalSetup: login-after-register failed ${loginRes2.status}`)
  }
  const body = await loginRes2.json()
  return body.access_token
}

// Eng 10 — runs once per Playwright job, before any spec starts. Specs no
// longer declare beforeAll for seeding; they only do per-test state
// manipulation (e.g. the undo spec's throwaway row).
export default async function globalSetup() {
  const token = await loginOrRegister()
  // Persist token for the spec phase. Path is absolute (under
  // frontend/tests/visual/) so the spec-side import in auth-base.js
  // resolves identically regardless of Playwright's cwd. Token expires
  // 15 minutes from issue (ACCESS_TOKEN_TTL_SECONDS); the visual-test
  // CI job is currently ~3 min wall-time, comfortably below expiry.
  const tokenPath = new URL('../.vrt-token', import.meta.url).pathname
  fs.writeFileSync(tokenPath, token)
  await seedKnownWeek(token)
}
