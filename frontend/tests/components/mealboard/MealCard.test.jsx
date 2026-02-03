import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MealCard from '../../../src/components/mealboard/MealCard'

describe('MealCard', () => {
  const mockRecipe = {
    id: 1,
    name: 'Honey Garlic Chicken',
    cook_time_minutes: 30,
    is_favorite: true,
  }

  const mockMeal = {
    id: 1,
    category: 'DINNER',
    recipe_id: 1,
    custom_meal_name: null,
    was_cooked: false,
    notes: null,
  }

  const defaultProps = {
    meal: mockMeal,
    recipe: mockRecipe,
    onToggleCooked: vi.fn(),
    onDelete: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders recipe name when from recipe', () => {
    render(<MealCard {...defaultProps} />)

    expect(screen.getByText('Honey Garlic Chicken')).toBeInTheDocument()
  })

  it('renders custom meal name when no recipe', () => {
    const props = {
      ...defaultProps,
      meal: { ...mockMeal, recipe_id: null, custom_meal_name: 'Takeout Pizza' },
      recipe: null,
    }
    render(<MealCard {...props} />)

    expect(screen.getByText('Takeout Pizza')).toBeInTheDocument()
  })

  it('displays category badge', () => {
    render(<MealCard {...defaultProps} />)

    expect(screen.getByText('DINNER')).toBeInTheDocument()
  })

  it('shows cook time when available', () => {
    render(<MealCard {...defaultProps} />)

    expect(screen.getByText('30 min')).toBeInTheDocument()
  })

  it('shows favorite badge for favorite recipes', () => {
    render(<MealCard {...defaultProps} />)

    expect(screen.getByText('Favorite')).toBeInTheDocument()
  })

  it('does not show favorite badge for non-favorite recipes', () => {
    const props = {
      ...defaultProps,
      recipe: { ...mockRecipe, is_favorite: false },
    }
    render(<MealCard {...props} />)

    expect(screen.queryByText('Favorite')).not.toBeInTheDocument()
  })

  it('displays notes when present', () => {
    const props = {
      ...defaultProps,
      meal: { ...mockMeal, notes: 'Double the garlic' },
    }
    render(<MealCard {...props} />)

    expect(screen.getByText('Double the garlic')).toBeInTheDocument()
  })

  it('calls onToggleCooked when clicking cooked button', async () => {
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} />)

    await user.click(screen.getByTitle('Mark as cooked'))
    expect(defaultProps.onToggleCooked).toHaveBeenCalledTimes(1)
  })

  it('calls onDelete when clicking delete button', async () => {
    const user = userEvent.setup()
    render(<MealCard {...defaultProps} />)

    await user.click(screen.getByTitle('Remove meal'))
    expect(defaultProps.onDelete).toHaveBeenCalledTimes(1)
  })

  it('shows different style when meal is cooked', () => {
    const props = {
      ...defaultProps,
      meal: { ...mockMeal, was_cooked: true },
    }
    render(<MealCard {...props} />)

    expect(screen.getByTitle('Mark as not cooked')).toBeInTheDocument()
  })
})
