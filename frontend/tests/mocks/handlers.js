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
  { id: 1, name: 'Everyone', is_system: true, photo_url: null },
  { id: 2, name: 'Alice', is_system: false, photo_url: null },
  { id: 3, name: 'Bob', is_system: false, photo_url: null },
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
    category: 'MORNING',
    assigned_to: 2,
    frequency: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    icon_url: null,
    family_member: mockFamilyMembers[1],
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

    let tasks = mockTasks
    if (listId) {
      tasks = mockTasks.filter((t) => t.list_id === Number(listId))
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

  http.post(`${API_BASE}/responsibilities/:id/complete`, () => {
    return HttpResponse.json({ id: 1, completed: true })
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
]
