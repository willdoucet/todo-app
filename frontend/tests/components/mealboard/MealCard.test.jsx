import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
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

  it('shows combined cook time and servings for recipe meals', () => {
    render(<MealCard {...defaultProps} />)
    // prep (10) + cook (30) = 40m
    expect(screen.getByText(/40m/)).toBeInTheDocument()
    expect(screen.getByText(/4 servings/)).toBeInTheDocument()
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

  it('shows view recipe button for recipe entries', () => {
    render(<MealCard {...defaultProps} />)
    expect(screen.getByLabelText('View recipe')).toBeInTheDocument()
  })

  it('calls onViewRecipe when view recipe button is clicked', async () => {
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} />)
    await user.click(screen.getByLabelText('View recipe'))
    // onViewRecipe is called with the item.id (was recipe.id pre-refactor)
    expect(defaultProps.onViewRecipe).toHaveBeenCalledWith(1)
  })

  it('hides view recipe button for non-recipe entries', () => {
    const entry = {
      ...mockRecipeEntry,
      item_id: 5,
      item: mockFoodItem,
    }
    render(<MealCard {...defaultProps} entry={entry} />)
    expect(screen.queryByLabelText('View recipe')).not.toBeInTheDocument()
  })
})
