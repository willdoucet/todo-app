import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecipeCard from '../../../src/components/mealboard/RecipeCard'

describe('RecipeCard', () => {
  const mockRecipe = {
    id: 1,
    name: 'Honey Garlic Chicken',
    description: 'Sweet and savory chicken stir fry',
    prep_time_minutes: 15,
    cook_time_minutes: 30,
    servings: 4,
    image_url: null,
    is_favorite: false,
    tags: ['quick', 'chicken', 'dinner'],
  }

  const defaultProps = {
    recipe: mockRecipe,
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onToggleFavorite: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders recipe name', () => {
    render(<RecipeCard {...defaultProps} />)

    expect(screen.getByText('Honey Garlic Chicken')).toBeInTheDocument()
  })

  it('renders description', () => {
    render(<RecipeCard {...defaultProps} />)

    expect(screen.getByText('Sweet and savory chicken stir fry')).toBeInTheDocument()
  })

  it('shows total time (prep + cook)', () => {
    render(<RecipeCard {...defaultProps} />)

    expect(screen.getByText('45 min')).toBeInTheDocument()
  })

  it('shows servings', () => {
    render(<RecipeCard {...defaultProps} />)

    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('displays tags', () => {
    render(<RecipeCard {...defaultProps} />)

    expect(screen.getByText('quick')).toBeInTheDocument()
    expect(screen.getByText('chicken')).toBeInTheDocument()
    expect(screen.getByText('dinner')).toBeInTheDocument()
  })

  it('shows +N for extra tags', () => {
    const props = {
      ...defaultProps,
      recipe: {
        ...mockRecipe,
        tags: ['quick', 'chicken', 'dinner', 'healthy', 'low-carb'],
      },
    }
    render(<RecipeCard {...props} />)

    expect(screen.getByText('+2')).toBeInTheDocument()
  })

  it('calls onEdit when clicking edit button', async () => {
    const user = userEvent.setup()
    render(<RecipeCard {...defaultProps} />)

    await user.click(screen.getByText('Edit'))
    expect(defaultProps.onEdit).toHaveBeenCalledTimes(1)
  })

  it('calls onDelete when clicking delete button', async () => {
    const user = userEvent.setup()
    render(<RecipeCard {...defaultProps} />)

    await user.click(screen.getByText('Delete'))
    expect(defaultProps.onDelete).toHaveBeenCalledTimes(1)
  })

  it('calls onToggleFavorite when clicking favorite button', async () => {
    const user = userEvent.setup()
    render(<RecipeCard {...defaultProps} />)

    const buttons = screen.getAllByRole('button')
    const heartButton = buttons.find(btn => btn.querySelector('svg path[d*="4.318 6.318"]'))
    await user.click(heartButton)
    expect(defaultProps.onToggleFavorite).toHaveBeenCalledTimes(1)
  })

  it('shows filled heart for favorite recipes', () => {
    const props = {
      ...defaultProps,
      recipe: { ...mockRecipe, is_favorite: true },
    }
    render(<RecipeCard {...props} />)

    const heartIcon = document.querySelector('.fill-red-500')
    expect(heartIcon).toBeInTheDocument()
  })

  it('shows placeholder when no image', () => {
    render(<RecipeCard {...defaultProps} />)

    const placeholder = document.querySelector('.aspect-video svg')
    expect(placeholder).toBeInTheDocument()
  })
})
