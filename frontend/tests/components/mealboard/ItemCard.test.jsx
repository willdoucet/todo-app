import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ItemCard from '../../../src/components/mealboard/ItemCard'

describe('ItemCard', () => {
  const recipeItem = {
    id: 1,
    name: 'Honey Garlic Chicken',
    item_type: 'recipe',
    icon_emoji: null,
    icon_url: null,
    tags: ['dinner'],
    is_favorite: true,
    recipe_detail: {
      description: 'Quick dinner',
      ingredients: [{ name: 'chicken' }],
      instructions: 'Cook it',
      prep_time_minutes: 10,
      cook_time_minutes: 30,
      servings: 4,
      image_url: null,
    },
    food_item_detail: null,
  }

  const foodItem = {
    id: 2,
    name: 'Banana',
    item_type: 'food_item',
    icon_emoji: '🍌',
    icon_url: null,
    tags: [],
    is_favorite: false,
    recipe_detail: null,
    food_item_detail: { category: 'fruit', shopping_quantity: 1, shopping_unit: 'each' },
  }

  describe('recipe variant', () => {
    it('renders the recipe tile with name and metadata from recipe_detail', () => {
      render(<ItemCard item={recipeItem} />)
      expect(screen.getByText('Honey Garlic Chicken')).toBeInTheDocument()
      // prep + cook = 40m, 4 servings
      expect(screen.getByText(/40m/)).toBeInTheDocument()
      expect(screen.getByText(/4 servings/)).toBeInTheDocument()
    })

    it('renders a filled favorite heart when is_favorite is true', () => {
      render(<ItemCard item={recipeItem} />)
      expect(screen.getByLabelText('Remove from favorites')).toBeInTheDocument()
    })

    it('fires onEdit when the edit button is clicked (stopping propagation)', async () => {
      const onEdit = vi.fn()
      const onClick = vi.fn()
      const user = userEvent.setup()
      render(<ItemCard item={recipeItem} onEdit={onEdit} onClick={onClick} />)
      await user.click(screen.getByLabelText('Edit Honey Garlic Chicken'))
      expect(onEdit).toHaveBeenCalled()
      expect(onClick).not.toHaveBeenCalled()
    })

    it('fires onDelete when the delete button is clicked', async () => {
      const onDelete = vi.fn()
      const user = userEvent.setup()
      render(<ItemCard item={recipeItem} onDelete={onDelete} />)
      await user.click(screen.getByLabelText('Delete Honey Garlic Chicken'))
      expect(onDelete).toHaveBeenCalled()
    })
  })

  describe('food_item variant (pill layout, mockup food-items-pill-option-a)', () => {
    it('renders as a horizontal pill with emoji and name', () => {
      render(<ItemCard item={foodItem} />)
      expect(screen.getByText('Banana')).toBeInTheDocument()
      // The emoji 🍌 is rendered as text inside a span
      expect(screen.getByText('🍌')).toBeInTheDocument()
    })

    it('the whole pill is a click target (click = edit)', async () => {
      const onClick = vi.fn()
      const user = userEvent.setup()
      render(<ItemCard item={foodItem} onClick={onClick} />)
      await user.click(screen.getByLabelText('Edit Banana'))
      expect(onClick).toHaveBeenCalled()
    })

    it('falls back to onEdit when no onClick is provided', async () => {
      const onEdit = vi.fn()
      const user = userEvent.setup()
      render(<ItemCard item={foodItem} onEdit={onEdit} />)
      await user.click(screen.getByLabelText('Edit Banana'))
      expect(onEdit).toHaveBeenCalled()
    })

    it('nested favorite heart toggles without propagating to the pill click', async () => {
      const onClick = vi.fn()
      const onToggleFavorite = vi.fn()
      const user = userEvent.setup()
      render(<ItemCard item={foodItem} onClick={onClick} onToggleFavorite={onToggleFavorite} />)
      await user.click(screen.getByLabelText('Add to favorites'))
      expect(onToggleFavorite).toHaveBeenCalled()
      expect(onClick).not.toHaveBeenCalled()
    })

    it('renders a category dot for the pill variant', () => {
      const { container } = render(<ItemCard item={foodItem} />)
      // Category dot is an aria-hidden span with a bg-* class
      const dot = container.querySelector('[title="fruit"]')
      expect(dot).toBeInTheDocument()
    })

    it('renders with a placeholder emoji when icon_emoji is missing', () => {
      const noIconItem = { ...foodItem, icon_emoji: null }
      render(<ItemCard item={noIconItem} />)
      expect(screen.getByText('🍽')).toBeInTheDocument()
    })
  })
})
