import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import axios from 'axios'
import MealCard from '../../../src/components/mealboard/MealCard'

vi.mock('axios')

describe('MealCard', () => {
  const mockSlotType = {
    id: 3,
    name: 'Dinner',
    color: '#E8927C',
    icon: '🍽',
    default_participants: [],
  }

  const mockFamilyMembers = [
    { id: 1, name: 'Dad', color: '#5B8DEF' },
    { id: 2, name: 'Mom', color: '#E06B9F' },
    { id: 3, name: 'Kid', color: '#F5A623' },
  ]

  // Post-refactor: meal_entries reference an Item via item_id, and the response
  // embeds the full Item object (with detail eager-loaded) under entry.item.
  const mockRecipeItem = {
    id: 1,
    name: 'Honey Garlic Chicken',
    item_type: 'recipe',
    icon_emoji: null,
    icon_url: null,
    tags: [],
    is_favorite: true,
    recipe_detail: {
      description: null,
      ingredients: [],
      instructions: null,
      prep_time_minutes: 10,
      cook_time_minutes: 30,
      servings: 4,
      image_url: null,
    },
    food_item_detail: null,
  }

  const mockFoodItem = {
    id: 5,
    name: 'Banana',
    item_type: 'food_item',
    icon_emoji: '🍌',
    icon_url: null,
    tags: [],
    is_favorite: false,
    recipe_detail: null,
    food_item_detail: {
      category: 'fruit',
      shopping_quantity: 1,
      shopping_unit: 'each',
    },
  }

  const mockRecipeEntry = {
    id: 10,
    date: '2026-04-04',
    meal_slot_type_id: 3,
    item_id: 1,
    item: mockRecipeItem,
    custom_meal_name: null,
    was_cooked: false,
    notes: null,
    participants: mockFamilyMembers, // all members = "everyone"
  }

  const defaultProps = {
    entry: mockRecipeEntry,
    slotType: mockSlotType,
    familyMembers: mockFamilyMembers,
    onUpdated: vi.fn(),
    onDeleted: vi.fn(),
    onViewRecipe: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    axios.patch = vi.fn().mockResolvedValue({ data: { ...mockRecipeEntry, was_cooked: true } })
    axios.delete = vi.fn().mockResolvedValue({ data: {} })
  })

  it('renders recipe name when item_type is recipe', () => {
    render(<MealCard {...defaultProps} />)
    expect(screen.getByText('Honey Garlic Chicken')).toBeInTheDocument()
  })

  it('renders custom meal name for an entry with no item', () => {
    const entry = {
      ...mockRecipeEntry,
      item_id: null,
      item: null,
      custom_meal_name: 'Leftover pizza',
    }
    render(<MealCard {...defaultProps} entry={entry} />)
    expect(screen.getByText('Leftover pizza')).toBeInTheDocument()
  })

  it('renders food item name for food_item type', () => {
    const entry = {
      ...mockRecipeEntry,
      item_id: 5,
      item: mockFoodItem,
    }
    render(<MealCard {...defaultProps} entry={entry} />)
    expect(screen.getByText('Banana')).toBeInTheDocument()
  })

  it('shows combined cook time for recipe meals', () => {
    render(<MealCard {...defaultProps} />)
    // prep (10) + cook (30) = 40m
    expect(screen.getByText(/40m/)).toBeInTheDocument()
  })

  it('does not render the "n servings" text on the recipe card', () => {
    render(<MealCard {...defaultProps} />)
    expect(screen.queryByText(/servings/)).not.toBeInTheDocument()
  })

  it('hides participant avatars when all family members are participants (everyone)', () => {
    render(<MealCard {...defaultProps} />)
    const avatarContainer = document.querySelector('.-space-x-1')
    expect(avatarContainer).not.toBeInTheDocument()
  })

  it('shows individual avatars when only some members are participants', () => {
    const entry = {
      ...mockRecipeEntry,
      participants: [mockFamilyMembers[0]], // Only Dad
    }
    render(<MealCard {...defaultProps} entry={entry} />)
    const avatarContainer = document.querySelector('.-space-x-1')
    expect(avatarContainer).toBeInTheDocument()
  })

  it('calls onUpdated via axios when toggling cooked', async () => {
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} />)
    const toggleButton = screen.getByLabelText(/Mark as cooked/i)
    await user.click(toggleButton)
    expect(axios.patch).toHaveBeenCalledWith(
      expect.stringContaining('/meal-entries/10'),
      { was_cooked: true }
    )
    expect(defaultProps.onUpdated).toHaveBeenCalled()
  })

  it('calls onDeleted via axios when clicking delete', async () => {
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} />)
    const deleteButton = screen.getByLabelText(/Delete meal/i)
    await user.click(deleteButton)
    expect(axios.delete).toHaveBeenCalledWith(expect.stringContaining('/meal-entries/10'))
    expect(defaultProps.onDeleted).toHaveBeenCalledWith(10)
  })

  it('shows cooked state with strikethrough and cooked badge', () => {
    const entry = { ...mockRecipeEntry, was_cooked: true }
    render(<MealCard {...defaultProps} entry={entry} />)
    const name = screen.getByText('Honey Garlic Chicken')
    expect(name.className).toContain('line-through')
    expect(screen.getByText('✓ Cooked')).toBeInTheDocument()
  })

  it('does not render a view-recipe button — only Mark cooked + Delete on hover', () => {
    render(<MealCard {...defaultProps} />)
    expect(screen.queryByLabelText('View recipe')).not.toBeInTheDocument()
  })

  it('opens recipe drawer when the card body is clicked (recipe entries)', async () => {
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} />)
    // Click the recipe name — acts as card body click
    await user.click(screen.getByText('Honey Garlic Chicken'))
    expect(defaultProps.onViewRecipe).toHaveBeenCalledWith(1)
  })

  it('renders the action zone with the collapse/expand classes on desktop and always-on classes for mobile', () => {
    render(<MealCard {...defaultProps} />)
    // Find the Cooked button, walk up to its action-zone parent
    const cookedBtn = screen.getByLabelText(/Mark as cooked/i)
    const actionZone = cookedBtn.parentElement
    // Mobile: permanently expanded
    expect(actionZone.className).toMatch(/max-md:max-h-\[48px\]/)
    expect(actionZone.className).toMatch(/max-md:opacity-100/)
    // Desktop: collapsed at rest
    expect(actionZone.className).toMatch(/md:max-h-0/)
    expect(actionZone.className).toMatch(/md:opacity-0/)
    // Desktop: expanded on group-hover and group-focus-within
    expect(actionZone.className).toMatch(/md:group-hover:max-h-\[48px\]/)
    expect(actionZone.className).toMatch(/md:group-focus-within:max-h-\[48px\]/)
  })

  it('gates the max-height/opacity transition on motion-safe so reduced-motion users get no animation', () => {
    render(<MealCard {...defaultProps} />)
    const cookedBtn = screen.getByLabelText(/Mark as cooked/i)
    const actionZone = cookedBtn.parentElement
    // motion-safe: prefix means the transition is only applied when prefers-reduced-motion:no-preference
    expect(actionZone.className).toMatch(/motion-safe:transition-\[max-height,opacity,padding-bottom\]/)
    expect(actionZone.className).toMatch(/motion-safe:duration-180/)
  })

  // ---- Food-item variant: icon-on-top + hover-expand (plan 20260418-183015) ----

  const foodItemEntry = {
    id: 21,
    date: '2026-04-04',
    meal_slot_type_id: 3,
    item_id: 5,
    item: mockFoodItem,
    custom_meal_name: null,
    was_cooked: false,
    notes: null,
    participants: mockFamilyMembers, // all members = "everyone"
  }

  it('food-item card has icon above title in the vertical stack', () => {
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    const title = screen.getByText('Banana')
    const body = title.parentElement
    // First child of the body is the icon (aria-hidden), title is second.
    expect(body.firstElementChild).toHaveAttribute('aria-hidden', 'true')
    expect(body.children[1]).toBe(title)
  })

  it('food-item card action zone uses the hover-expand class string', () => {
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    const cookedBtn = screen.getByLabelText(/Mark as cooked/i)
    const actionZone = cookedBtn.parentElement
    expect(actionZone.className).toMatch(/md:max-h-0/)
    expect(actionZone.className).toMatch(/md:group-hover:max-h-\[48px\]/)
    expect(actionZone.className).toMatch(/md:group-focus-within:max-h-\[48px\]/)
    expect(actionZone.className).toMatch(/motion-safe:transition-\[max-height,opacity,padding-bottom\]/)
    expect(actionZone.className).toMatch(/max-md:opacity-100/)
  })

  it('food-item card caps long names at two lines via line-clamp-2', () => {
    const longItem = {
      ...mockFoodItem,
      name: 'Roasted Brussels Sprouts with Maple Glaze and Pecan Crumble',
    }
    const entry = { ...foodItemEntry, item: longItem }
    render(<MealCard {...defaultProps} entry={entry} />)
    const title = screen.getByText(longItem.name)
    expect(title.className).toMatch(/line-clamp-2/)
  })

  it('food-item card preserves cooked-state strikethrough and sage text', () => {
    const entry = { ...foodItemEntry, was_cooked: true }
    render(<MealCard {...defaultProps} entry={entry} />)
    const title = screen.getByText('Banana')
    expect(title.className).toMatch(/line-through/)
    expect(title.className).toMatch(/text-sage-600/)
  })

  it('food-item card calls onUpdated via PATCH when Mark as cooked is clicked', async () => {
    axios.patch = vi.fn().mockResolvedValue({ data: { ...foodItemEntry, was_cooked: true } })
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    await user.click(screen.getByLabelText(/Mark as cooked/i))
    expect(axios.patch).toHaveBeenCalledWith(
      expect.stringContaining('/meal-entries/21'),
      { was_cooked: true }
    )
    expect(defaultProps.onUpdated).toHaveBeenCalled()
  })

  it('food-item card forwards undo metadata on delete when the backend returns it', async () => {
    axios.delete = vi.fn().mockResolvedValue({
      data: {
        entry: foodItemEntry,
        undo_token: 'tok-abc',
        expires_at: '2026-04-04T12:00:05Z',
      },
    })
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    await user.click(screen.getByLabelText(/Delete meal/i))
    expect(defaultProps.onDeleted).toHaveBeenCalledWith(
      21,
      expect.objectContaining({
        undoToken: 'tok-abc',
        expiresAt: '2026-04-04T12:00:05Z',
        entry: foodItemEntry,
      })
    )
  })

  it('food-item card falls back to legacy hard-delete behavior when undo metadata is missing', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    axios.delete = vi.fn().mockResolvedValue({ data: {} })
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    await user.click(screen.getByLabelText(/Delete meal/i))
    expect(defaultProps.onDeleted).toHaveBeenCalledWith(21)
    expect(consoleError).toHaveBeenCalledWith('delete_missing_undo_token', 21)
    consoleError.mockRestore()
  })

  it('food-item card shows generic error text when Mark as cooked fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    axios.patch = vi.fn().mockRejectedValue(new Error('network'))
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    await user.click(screen.getByLabelText(/Mark as cooked/i))
    const status = await screen.findByRole('status')
    expect(status.textContent).toMatch(/couldn't save/i)
    // Button is re-enabled for retry (isWorking resets in finally).
    expect(screen.getByLabelText(/Mark as cooked/i)).not.toBeDisabled()
    consoleError.mockRestore()
  })

  it('food-item card shows "already deleted" text when delete returns 404', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    axios.delete = vi.fn().mockRejectedValue({ response: { status: 404 } })
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    await user.click(screen.getByLabelText(/Delete meal/i))
    const status = await screen.findByRole('status')
    expect(status.textContent).toMatch(/already deleted/i)
    consoleError.mockRestore()
  })

  it('recipe card shows generic error text when Mark as cooked fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    axios.patch = vi.fn().mockRejectedValue(new Error('network'))
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} />)
    await user.click(screen.getByLabelText(/Mark as cooked/i))
    const status = await screen.findByRole('status')
    expect(status.textContent).toMatch(/couldn't save/i)
    consoleError.mockRestore()
  })

  it('recipe action button click does not open the recipe drawer (stopPropagation)', async () => {
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} />)
    await user.click(screen.getByLabelText(/Mark as cooked/i))
    expect(axios.patch).toHaveBeenCalled()
    expect(defaultProps.onUpdated).toHaveBeenCalled()
    expect(defaultProps.onViewRecipe).not.toHaveBeenCalled()
  })

  it('food-item action buttons have 44×44 tap areas (w-11 h-11)', () => {
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    expect(screen.getByLabelText(/Mark as cooked/i).className).toMatch(/w-11 h-11/)
    expect(screen.getByLabelText(/Delete meal/i).className).toMatch(/w-11 h-11/)
  })

  it('recipe action buttons have 44×44 tap areas (w-11 h-11)', () => {
    render(<MealCard {...defaultProps} />)
    expect(screen.getByLabelText(/Mark as cooked/i).className).toMatch(/w-11 h-11/)
    expect(screen.getByLabelText(/Delete meal/i).className).toMatch(/w-11 h-11/)
  })

  it('error flash element renders outside the collapsible action zone', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    axios.patch = vi.fn().mockRejectedValue(new Error('network'))
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} entry={foodItemEntry} />)
    await user.click(screen.getByLabelText(/Mark as cooked/i))
    const status = await screen.findByRole('status')
    const actionZone = screen.getByLabelText(/Mark as cooked/i).parentElement
    // Desktop mouse-leave collapses the action zone (max-h-0). If status lives
    // inside it, the 3-second window gets clipped. Guarantee it does not.
    expect(actionZone.contains(status)).toBe(false)
    consoleError.mockRestore()
  })
})

describe('MealCard error timer behavior', () => {
  const mockSlotType = { id: 3, name: 'Dinner', color: '#E8927C', icon: '🍽', default_participants: [] }
  const mockFamilyMembers = [
    { id: 1, name: 'Dad', color: '#5B8DEF' },
    { id: 2, name: 'Mom', color: '#E06B9F' },
  ]
  const mockFoodItem = {
    id: 5,
    name: 'Banana',
    item_type: 'food_item',
    icon_emoji: '🍌',
    icon_url: null,
    tags: [],
    is_favorite: false,
    recipe_detail: null,
    food_item_detail: { category: 'fruit', shopping_quantity: 1, shopping_unit: 'each' },
  }
  const foodItemEntry = {
    id: 21,
    date: '2026-04-04',
    meal_slot_type_id: 3,
    item_id: 5,
    item: mockFoodItem,
    custom_meal_name: null,
    was_cooked: false,
    notes: null,
    participants: mockFamilyMembers,
  }
  const defaultProps = {
    entry: foodItemEntry,
    slotType: mockSlotType,
    familyMembers: mockFamilyMembers,
    onUpdated: vi.fn(),
    onDeleted: vi.fn(),
    onViewRecipe: vi.fn(),
  }

  let consoleError

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
    consoleError.mockRestore()
  })

  it('error text auto-clears after 3 seconds', async () => {
    axios.patch = vi.fn().mockRejectedValue(new Error('network'))
    render(<MealCard {...defaultProps} />)

    await act(async () => {
      screen.getByLabelText(/Mark as cooked/i).click()
    })
    expect(screen.getByRole('status').textContent).toMatch(/couldn't save/i)

    await act(async () => {
      vi.advanceTimersByTime(3100)
    })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('successful retry immediately clears a stale error before the 3s timer fires', async () => {
    axios.patch = vi.fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ data: { ...foodItemEntry, was_cooked: true } })
    render(<MealCard {...defaultProps} />)

    await act(async () => {
      screen.getByLabelText(/Mark as cooked/i).click()
    })
    expect(screen.getByRole('status').textContent).toMatch(/couldn't save/i)

    // Retry before the 3s timer fires — status must disappear on success.
    await act(async () => {
      screen.getByLabelText(/Mark as cooked/i).click()
    })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(defaultProps.onUpdated).toHaveBeenCalled()
  })
})
