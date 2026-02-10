/**
 * MSW request handlers - define mock API responses.
 *
 * These handlers intercept HTTP requests during tests and return
 * controlled responses. This lets you test components without
 * hitting the real backend.
 *
 * Usage in tests:
 *   - Default handlers below work for most tests
 *   - Override for specific tests using server.use()
 *
 * Example override:
 *   import { server } from '../tests/mocks/server'
 *   import { http, HttpResponse } from 'msw'
 *
 *   test('handles error state', async () => {
 *     server.use(
 *       http.get('http://localhost:8000/tasks', () => {
 *         return HttpResponse.json({ error: 'Server error' }, { status: 500 })
 *       })
 *     )
 *     // ... test error handling
 *   })
 */

import { http, HttpResponse } from 'msw'

const API_BASE = 'http://localhost:8000'

// =============================================================================
// Sample Data
// =============================================================================

const mockFamilyMembers = [
  { id: 1, name: 'Everyone', is_system: true, photo_url: null, color: '#D97452' },
  { id: 2, name: 'Alice', is_system: false, photo_url: null, color: '#3B82F6' },
  { id: 3, name: 'Bob', is_system: false, photo_url: null, color: '#EF4444' },
]

const mockLists = [
  { id: 1, name: 'Personal', color: '#EF4444', icon: 'clipboard' },
  { id: 2, name: 'Work', color: '#3B82F6', icon: 'briefcase' },
]

const mockTasks = [
  {
    id: 1,
    title: 'Buy groceries',
    description: 'Milk, eggs, bread',
    due_date: new Date().toISOString().split('T')[0],
    completed: false,
    important: true,
    assigned_to: 2,
    list_id: 1,
    family_member: mockFamilyMembers[1],
    list: mockLists[0],
  },
  {
    id: 2,
    title: 'Finish report',
    description: 'Q4 summary',
    due_date: null,
    completed: false,
    important: false,
    assigned_to: null,
    list_id: 2,
    family_member: null,
    list: mockLists[1],
  },
]

const mockResponsibilities = [
  {
    id: 1,
    title: 'Make bed',
    description: 'Make your bed every morning',
    categories: ['MORNING'],
    assigned_to: 2,
    frequency: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    icon_url: null,
    family_member: mockFamilyMembers[1],
  },
]

const mockRecipes = [
  {
    id: 1,
    name: 'Honey Garlic Chicken',
    description: 'Sweet and savory chicken stir fry',
    ingredients: [
      { name: 'Chicken breast', quantity: 1, unit: 'lb', category: 'Protein' },
      { name: 'Honey', quantity: 3, unit: 'tbsp', category: 'Pantry' },
      { name: 'Garlic', quantity: 4, unit: 'cloves', category: 'Produce' },
    ],
    instructions: '1. Cut chicken into cubes\n2. Mix honey and garlic\n3. Cook chicken\n4. Add sauce',
    prep_time_minutes: 15,
    cook_time_minutes: 30,
    servings: 4,
    image_url: null,
    is_favorite: true,
    tags: ['quick', 'chicken', 'dinner'],
    created_at: '2025-01-15T10:00:00Z',
    updated_at: null,
  },
  {
    id: 2,
    name: 'Creamy Tuscan Pasta',
    description: 'Rich and creamy Italian pasta',
    ingredients: [
      { name: 'Pasta', quantity: 1, unit: 'lb', category: 'Pantry' },
      { name: 'Heavy cream', quantity: 1, unit: 'cups', category: 'Dairy' },
      { name: 'Sun-dried tomatoes', quantity: 0.5, unit: 'cups', category: 'Pantry' },
    ],
    instructions: '1. Cook pasta\n2. Make cream sauce\n3. Combine and serve',
    prep_time_minutes: 10,
    cook_time_minutes: 25,
    servings: 6,
    image_url: null,
    is_favorite: false,
    tags: ['pasta', 'italian'],
    created_at: '2025-01-10T10:00:00Z',
    updated_at: null,
  },
]

const mockCalendarEvents = [
  {
    id: 1,
    title: 'Team meeting',
    description: 'Weekly sync',
    date: new Date().toISOString().split('T')[0],
    start_time: '09:00',
    end_time: '10:00',
    all_day: false,
    source: 'MANUAL',
    external_id: null,
    assigned_to: 2,
    family_member: mockFamilyMembers[1],
    created_at: '2026-01-15T10:00:00Z',
    updated_at: null,
  },
  {
    id: 2,
    title: 'School holiday',
    description: null,
    date: new Date().toISOString().split('T')[0],
    start_time: null,
    end_time: null,
    all_day: true,
    source: 'MANUAL',
    external_id: null,
    assigned_to: null,
    family_member: null,
    created_at: '2026-01-10T10:00:00Z',
    updated_at: null,
  },
]

const mockMealPlans = [
  {
    id: 1,
    date: new Date().toISOString().split('T')[0],
    category: 'DINNER',
    recipe_id: 1,
    custom_meal_name: null,
    was_cooked: false,
    notes: null,
    created_at: '2025-01-20T10:00:00Z',
    updated_at: null,
  },
]

// =============================================================================
// Handlers
// =============================================================================

export const handlers = [
  // -------------------------------------------------------------------------
  // Family Members
  // -------------------------------------------------------------------------
  http.get(`${API_BASE}/family-members`, () => {
    return HttpResponse.json(mockFamilyMembers)
  }),

  http.get(`${API_BASE}/family-members/:id`, ({ params }) => {
    const member = mockFamilyMembers.find((m) => m.id === Number(params.id))
    if (!member) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(member)
  }),

  http.post(`${API_BASE}/family-members`, async ({ request }) => {
    const body = await request.json()
    const newMember = {
      id: mockFamilyMembers.length + 1,
      is_system: false,
      photo_url: null,
      ...body,
    }
    return HttpResponse.json(newMember, { status: 201 })
  }),

  // -------------------------------------------------------------------------
  // Lists
  // -------------------------------------------------------------------------
  http.get(`${API_BASE}/lists`, () => {
    return HttpResponse.json(mockLists)
  }),

  http.get(`${API_BASE}/lists/:id`, ({ params }) => {
    const list = mockLists.find((l) => l.id === Number(params.id))
    if (!list) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(list)
  }),

  http.post(`${API_BASE}/lists`, async ({ request }) => {
    const body = await request.json()
    const newList = {
      id: mockLists.length + 1,
      ...body,
    }
    return HttpResponse.json(newList, { status: 201 })
  }),

  // -------------------------------------------------------------------------
  // Tasks
  // -------------------------------------------------------------------------
  http.get(`${API_BASE}/tasks`, ({ request }) => {
    const url = new URL(request.url)
    const listId = url.searchParams.get('list_id')
    const startDate = url.searchParams.get('start_date')
    const endDate = url.searchParams.get('end_date')
    const assignedTo = url.searchParams.get('assigned_to')

    let tasks = mockTasks
    if (listId) {
      tasks = tasks.filter((t) => t.list_id === Number(listId))
    }
    if (startDate) {
      tasks = tasks.filter((t) => t.due_date && t.due_date >= startDate)
    }
    if (endDate) {
      tasks = tasks.filter((t) => t.due_date && t.due_date <= endDate)
    }
    if (assignedTo) {
      tasks = tasks.filter((t) => t.assigned_to === Number(assignedTo))
    }
    return HttpResponse.json(tasks)
  }),

  http.get(`${API_BASE}/tasks/:id`, ({ params }) => {
    const task = mockTasks.find((t) => t.id === Number(params.id))
    if (!task) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(task)
  }),

  http.post(`${API_BASE}/tasks`, async ({ request }) => {
    const body = await request.json()
    const newTask = {
      id: mockTasks.length + 1,
      completed: false,
      important: false,
      family_member: null,
      list: mockLists.find((l) => l.id === body.list_id) || null,
      ...body,
    }
    return HttpResponse.json(newTask, { status: 201 })
  }),

  http.patch(`${API_BASE}/tasks/:id`, async ({ params, request }) => {
    const body = await request.json()
    const task = mockTasks.find((t) => t.id === Number(params.id))
    if (!task) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json({ ...task, ...body })
  }),

  http.delete(`${API_BASE}/tasks/:id`, ({ params }) => {
    const task = mockTasks.find((t) => t.id === Number(params.id))
    if (!task) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(task)
  }),

  // -------------------------------------------------------------------------
  // Responsibilities
  // -------------------------------------------------------------------------
  http.get(`${API_BASE}/responsibilities`, () => {
    return HttpResponse.json(mockResponsibilities)
  }),

  http.get(`${API_BASE}/responsibilities/completions`, () => {
    return HttpResponse.json([])
  }),

  http.patch(`${API_BASE}/responsibilities/:id`, async ({ params, request }) => {
    const body = await request.json()
    const responsibility = mockResponsibilities.find((r) => r.id === Number(params.id))
    if (!responsibility) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json({ ...responsibility, ...body, updated_at: new Date().toISOString() })
  }),

  http.post(`${API_BASE}/responsibilities/:id/complete`, ({ request }) => {
    const url = new URL(request.url)
    const category = url.searchParams.get('category') || 'MORNING'
    const familyMemberId = Number(url.searchParams.get('family_member_id')) || 1
    const date = url.searchParams.get('date') || new Date().toISOString().split('T')[0]
    return HttpResponse.json({
      completed: true,
      completion: {
        id: 1,
        responsibility_id: Number(request.url.match(/responsibilities\/(\d+)/)?.[1]) || 1,
        family_member_id: familyMemberId,
        completion_date: date,
        category: category,
      },
    })
  }),

  // -------------------------------------------------------------------------
  // Uploads
  // -------------------------------------------------------------------------
  http.get(`${API_BASE}/upload/stock-icons`, () => {
    return HttpResponse.json(['icon1.svg', 'icon2.svg', 'icon3.svg'])
  }),

  http.post(`${API_BASE}/upload/family-photo`, () => {
    return HttpResponse.json({ url: '/uploads/test-photo.jpg' })
  }),

  http.post(`${API_BASE}/upload/responsibility-icon`, () => {
    return HttpResponse.json({ url: '/uploads/test-icon.jpg' })
  }),

  // -------------------------------------------------------------------------
  // Recipes
  // -------------------------------------------------------------------------
  http.get(`${API_BASE}/recipes`, () => {
    return HttpResponse.json(mockRecipes)
  }),

  http.get(`${API_BASE}/recipes/:id`, ({ params }) => {
    const recipe = mockRecipes.find((r) => r.id === Number(params.id))
    if (!recipe) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(recipe)
  }),

  http.post(`${API_BASE}/recipes`, async ({ request }) => {
    const body = await request.json()
    const newRecipe = {
      id: mockRecipes.length + 1,
      created_at: new Date().toISOString(),
      updated_at: null,
      ...body,
    }
    return HttpResponse.json(newRecipe, { status: 201 })
  }),

  http.patch(`${API_BASE}/recipes/:id`, async ({ params, request }) => {
    const body = await request.json()
    const recipe = mockRecipes.find((r) => r.id === Number(params.id))
    if (!recipe) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json({ ...recipe, ...body, updated_at: new Date().toISOString() })
  }),

  http.delete(`${API_BASE}/recipes/:id`, ({ params }) => {
    const recipe = mockRecipes.find((r) => r.id === Number(params.id))
    if (!recipe) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(recipe)
  }),

  // -------------------------------------------------------------------------
  // Meal Plans
  // -------------------------------------------------------------------------
  http.get(`${API_BASE}/meal-plans`, () => {
    return HttpResponse.json(mockMealPlans)
  }),

  http.post(`${API_BASE}/meal-plans`, async ({ request }) => {
    const body = await request.json()
    const newMealPlan = {
      id: mockMealPlans.length + 1,
      created_at: new Date().toISOString(),
      updated_at: null,
      was_cooked: false,
      ...body,
    }
    return HttpResponse.json(newMealPlan, { status: 201 })
  }),

  http.patch(`${API_BASE}/meal-plans/:id`, async ({ params, request }) => {
    const body = await request.json()
    const mealPlan = mockMealPlans.find((mp) => mp.id === Number(params.id))
    if (!mealPlan) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json({ ...mealPlan, ...body, updated_at: new Date().toISOString() })
  }),

  http.delete(`${API_BASE}/meal-plans/:id`, ({ params }) => {
    const mealPlan = mockMealPlans.find((mp) => mp.id === Number(params.id))
    if (!mealPlan) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(mealPlan)
  }),

  // -------------------------------------------------------------------------
  // Calendar Events
  // -------------------------------------------------------------------------
  http.get(`${API_BASE}/calendar-events`, ({ request }) => {
    const url = new URL(request.url)
    const startDate = url.searchParams.get('start_date')
    const endDate = url.searchParams.get('end_date')
    const assignedTo = url.searchParams.get('assigned_to')

    let events = mockCalendarEvents
    if (startDate) {
      events = events.filter((e) => e.date >= startDate)
    }
    if (endDate) {
      events = events.filter((e) => e.date <= endDate)
    }
    if (assignedTo) {
      events = events.filter((e) => e.assigned_to === Number(assignedTo))
    }
    return HttpResponse.json(events)
  }),

  http.get(`${API_BASE}/calendar-events/:id`, ({ params }) => {
    const event = mockCalendarEvents.find((e) => e.id === Number(params.id))
    if (!event) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(event)
  }),

  http.post(`${API_BASE}/calendar-events`, async ({ request }) => {
    const body = await request.json()
    const newEvent = {
      id: mockCalendarEvents.length + 1,
      family_member: body.assigned_to
        ? mockFamilyMembers.find((m) => m.id === body.assigned_to) || null
        : null,
      created_at: new Date().toISOString(),
      updated_at: null,
      ...body,
    }
    return HttpResponse.json(newEvent, { status: 201 })
  }),

  http.patch(`${API_BASE}/calendar-events/:id`, async ({ params, request }) => {
    const body = await request.json()
    const event = mockCalendarEvents.find((e) => e.id === Number(params.id))
    if (!event) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    if (event.source !== 'MANUAL') {
      return HttpResponse.json({ detail: 'Cannot modify synced events' }, { status: 400 })
    }
    return HttpResponse.json({ ...event, ...body, updated_at: new Date().toISOString() })
  }),

  http.delete(`${API_BASE}/calendar-events/:id`, ({ params }) => {
    const event = mockCalendarEvents.find((e) => e.id === Number(params.id))
    if (!event) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    if (event.source !== 'MANUAL') {
      return HttpResponse.json({ detail: 'Cannot delete synced events' }, { status: 400 })
    }
    return HttpResponse.json(event)
  }),
]
