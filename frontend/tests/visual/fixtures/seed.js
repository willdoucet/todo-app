// Idempotent visual-test seeding. Runs once per job via Playwright's
// `globalSetup` (Eng 10). Writes through the real API — no DB-direct access.
//
// M5 PR1 update: every protected route now requires `Authorization:
// Bearer <jwt>`. The seed flow accepts a JWT minted by globalSetup's
// login-or-register and threads it through `apiFetch` so every
// downstream call carries the header. Callers without a token (legacy
// callers, if any) still work locally on stacks where APP_ENV != test
// AND the env vars are unset; we leave token optional rather than
// hard-required so an out-of-tree caller can opt in.
//
// Contract (Adversarial review A1):
//   POST /items/                      — unified item create
//   POST /meal-entries/               — create meal for a (date, slot) cell
//   GET  /meal-entries/?start_date=&end_date=
//   DELETE /meal-entries/{id}         — soft-delete
//   GET  /meal-slot-types/            — to discover the first slot ID
//   GET  /items/?search=VRT           — for cleanup
//   DELETE /items/{id}                — soft-delete (15s undo window)
//
// The seeded week is the *current* week (Mon..Sun) because MealPlannerView
// loads `new Date()` by default. Three canonical entries land on Monday in
// the first slot so specs can locate them without relying on sort order.

const API_URL = process.env.API_URL || 'http://localhost:8000'

const CANONICAL_ITEMS = [
  {
    name: 'VRT Recipe Alpha',
    item_type: 'recipe',
    icon_emoji: '🥞',
    recipe_detail: {
      description: 'Seeded recipe for visual regression tests.',
      ingredients: [],
      instructions: null,
      prep_time_minutes: 10,
      cook_time_minutes: 15,
      servings: 4,
    },
  },
  {
    name: 'VRT Recipe Beta',
    item_type: 'recipe',
    icon_emoji: '🍲',
    recipe_detail: {
      description: 'Second seeded recipe.',
      ingredients: [],
      instructions: null,
      prep_time_minutes: 5,
      cook_time_minutes: 20,
      servings: 2,
    },
  },
  {
    name: 'VRT Food Item Alpha',
    item_type: 'food_item',
    icon_emoji: '🥕',
    food_item_detail: {
      category: 'Other',
      shopping_quantity: 1,
      shopping_unit: 'each',
    },
  },
]

class SeedError extends Error {
  constructor(message) {
    super(message)
    this.name = 'SeedError'
  }
}

// Wraps fetch with a 10s per-call timeout (Eng 7A) and a consistent error
// shape. Every response body is captured on non-OK so CI failure reports
// include the reason. `token` (optional) attaches Authorization: Bearer.
async function apiFetch(method, path, body = null, token = null) {
  const url = `${API_URL}${path}`
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`
  let res
  try {
    res = await fetch(url, {
      method,
      headers: Object.keys(headers).length ? headers : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(10_000),
    })
  } catch (err) {
    if (err.name === 'TimeoutError' || err.name === 'AbortError') {
      throw new SeedError(
        `SeedError: timeout after 10s on ${method} ${url}. Likely cause: api-test deadlocked or migration hang.`,
      )
    }
    throw new SeedError(`SeedError: fetch error on ${method} ${url} — ${err.message}`)
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '<unreadable body>')
    throw new SeedError(
      `SeedError: ${method} ${url} returned ${res.status}. Response body: ${text}. ` +
        `Likely cause: schema validation or stale route contract.`,
    )
  }
  if (res.status === 204) return null
  return res.json()
}

function formatDateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

// Mirrors getWeekDates() in MealPlannerView.jsx (Monday-anchored).
function currentWeekMonSun() {
  const d = new Date()
  const dayOfWeek = d.getDay() // 0=Sun, 1=Mon, ..., 6=Sat
  const offset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  const monday = new Date(d)
  monday.setDate(d.getDate() + offset)
  monday.setHours(0, 0, 0, 0)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return { monday, sunday }
}

function isVrtEntry(entry) {
  const itemName = entry.item?.name || ''
  const custom = entry.custom_meal_name || ''
  return itemName.startsWith('VRT ') || custom.startsWith('VRT ')
}

/**
 * Idempotent seed of the known week. Safe to run repeatedly — prior VRT
 * entries and items are soft-deleted before the canonical set is re-created.
 *
 * @param {string} [token] — optional JWT minted by globalSetup. Required
 *   in M5+ when api-test runs with auth enforcement on; ignored if absent.
 */
export async function seedKnownWeek(token = null) {
  const { monday, sunday } = currentWeekMonSun()
  const start = formatDateKey(monday)
  const end = formatDateKey(sunday)

  // Step 1 — clean up stale VRT meal entries from the target week.
  const existingEntries = await apiFetch(
    'GET',
    `/meal-entries/?start_date=${start}&end_date=${end}`,
    null,
    token,
  )
  const vrtEntries = existingEntries.filter(isVrtEntry)
  for (const entry of vrtEntries) {
    await apiFetch('DELETE', `/meal-entries/${entry.id}`, null, token)
  }

  // Step 2 — clean up stale VRT items so names don't compound. `?search=VRT`
  // does a case-insensitive LIKE match against the name column.
  const existingItems = await apiFetch('GET', '/items/?search=VRT', null, token)
  for (const item of existingItems.filter((it) => it.name.startsWith('VRT '))) {
    await apiFetch('DELETE', `/items/${item.id}`, null, token)
  }

  // Step 3 — discover the first slot type. The migration seeds 3 defaults
  // (Breakfast, Lunch, Dinner); we always put the canonical set on the first
  // one so specs have a stable target.
  const slotTypes = await apiFetch('GET', '/meal-slot-types/', null, token)
  if (!slotTypes.length) {
    throw new SeedError(
      'SeedError: no meal_slot_types found. Migration may not have run.',
    )
  }
  const firstSlot = slotTypes[0]

  // Step 4 — create the canonical items and matching meal entries on Monday.
  const createdItems = []
  for (const payload of CANONICAL_ITEMS) {
    const item = await apiFetch('POST', '/items/', payload, token)
    createdItems.push(item)
  }

  for (let i = 0; i < createdItems.length; i++) {
    const item = createdItems[i]
    await apiFetch(
      'POST',
      '/meal-entries/',
      {
        date: start,
        meal_slot_type_id: firstSlot.id,
        item_id: item.id,
        sort_order: i,
      },
      token,
    )
  }

  return { weekStart: start, weekEnd: end, slotId: firstSlot.id, items: createdItems }
}
