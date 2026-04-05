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
  }

  const mockFamilyMembers = [
    { id: 1, name: 'Dad', color: '#5B8DEF' },
    { id: 2, name: 'Mom', color: '#E06B9F' },
    { id: 3, name: 'Kid', color: '#F5A623' },
  ]

  const mockRecipe = {
    id: 1,
    name: 'Honey Garlic Chicken',
    cook_time_minutes: 30,
    is_favorite: true,
  }

  const mockRecipeEntry = {
    id: 10,
    date: '2026-04-04',
    meal_slot_type_id: 3,
    recipe_id: 1,
    food_item_id: null,
    custom_meal_name: null,
    item_type: 'recipe',
    was_cooked: false,
    notes: null,
    recipe: mockRecipe,
    food_item: null,
    participants: mockFamilyMembers, // all members = "everyone"
  }

  const defaultProps = {
    entry: mockRecipeEntry,
    slotType: mockSlotType,
    familyMembers: mockFamilyMembers,
    onUpdated: vi.fn(),
    onDeleted: vi.fn(),
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

  it('renders custom meal name when item_type is custom', () => {
    const entry = {
      ...mockRecipeEntry,
      item_type: 'custom',
      recipe_id: null,
      recipe: null,
      custom_meal_name: 'Leftover pizza',
    }
    render(<MealCard {...defaultProps} entry={entry} />)
    expect(screen.getByText('Leftover pizza')).toBeInTheDocument()
  })

  it('renders food item with emoji for food_item type', () => {
    const entry = {
      ...mockRecipeEntry,
      item_type: 'food_item',
      recipe_id: null,
      recipe: null,
      food_item_id: 5,
      food_item: { id: 5, name: 'Banana', emoji: '🍌', category: 'fruit' },
    }
    render(<MealCard {...defaultProps} entry={entry} />)
    expect(screen.getByText('Banana')).toBeInTheDocument()
    expect(screen.getByText('🍌')).toBeInTheDocument()
  })

  it('shows cook time for recipe meals', () => {
    render(<MealCard {...defaultProps} />)
    expect(screen.getByText(/30m/)).toBeInTheDocument()
  })

  it('shows favorite badge for favorite recipes', () => {
    render(<MealCard {...defaultProps} />)
    expect(screen.getByText(/★\s*FAV/)).toBeInTheDocument()
  })

  it('does not show favorite badge for non-favorite recipes', () => {
    const entry = {
      ...mockRecipeEntry,
      recipe: { ...mockRecipe, is_favorite: false },
    }
    render(<MealCard {...defaultProps} entry={entry} />)
    expect(screen.queryByText(/★\s*FAV/)).not.toBeInTheDocument()
  })

  it('displays notes when present', () => {
    const entry = { ...mockRecipeEntry, notes: 'Extra garlic tonight' }
    render(<MealCard {...defaultProps} entry={entry} />)
    expect(screen.getByText('Extra garlic tonight')).toBeInTheDocument()
  })

  it('shows "Everyone" badge when all family members are participants', () => {
    render(<MealCard {...defaultProps} />)
    expect(screen.getByText('Everyone')).toBeInTheDocument()
  })

  it('shows individual avatars when only some members are participants', () => {
    const entry = {
      ...mockRecipeEntry,
      participants: [mockFamilyMembers[0]], // Only Dad
    }
    render(<MealCard {...defaultProps} entry={entry} />)
    expect(screen.queryByText('Everyone')).not.toBeInTheDocument()
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

  it('shows cooked state with strikethrough and checkmark when was_cooked is true', () => {
    const entry = { ...mockRecipeEntry, was_cooked: true }
    const { container } = render(<MealCard {...defaultProps} entry={entry} />)
    const name = screen.getByText('Honey Garlic Chicken')
    expect(name.className).toContain('line-through')
    expect(container.querySelector('.from-sage-500')).toBeInTheDocument()
  })
})
