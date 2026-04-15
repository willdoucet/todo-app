import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ItemFormModal from '../../../src/components/mealboard/ItemFormModal'

describe('ItemFormModal', () => {
  let onSubmit
  let onClose

  beforeEach(() => {
    onSubmit = vi.fn().mockResolvedValue({})
    onClose = vi.fn()
  })

  describe('recipe variant', () => {
    it('shows recipe-specific fields, not food-item fields', () => {
      render(
        <ItemFormModal isOpen type="recipe" onSubmit={onSubmit} onClose={onClose} initialItem={null} />
      )
      // Recipe form exposes the full ingredients table, time inputs, tags, image upload
      expect(screen.getByText(/Ingredients/)).toBeInTheDocument()
      expect(screen.getByText(/Instructions/)).toBeInTheDocument()
      expect(screen.getByText(/Prep Time/)).toBeInTheDocument()
      expect(screen.getByText(/Cook Time/)).toBeInTheDocument()
      expect(screen.getByText(/Tags/)).toBeInTheDocument()
      // Food-item-specific controls should NOT render in recipe mode
      expect(screen.queryByRole('tablist', { name: 'Icon source' })).not.toBeInTheDocument()
    })

    it('pre-populates form from initialItem in edit mode', () => {
      const initialItem = {
        id: 99,
        name: 'Editable Recipe',
        item_type: 'recipe',
        is_favorite: true,
        tags: ['quick'],
        recipe_detail: {
          description: 'desc',
          instructions: 'do it',
          ingredients: [{ name: 'salt', quantity: 1, unit: 'tsp', category: 'Pantry' }],
          prep_time_minutes: 5,
          cook_time_minutes: 10,
          servings: 2,
          image_url: '',
        },
      }
      render(
        <ItemFormModal isOpen type="recipe" onSubmit={onSubmit} onClose={onClose} initialItem={initialItem} />
      )
      expect(screen.getByDisplayValue('Editable Recipe')).toBeInTheDocument()
      expect(screen.getByDisplayValue('desc')).toBeInTheDocument()
      expect(screen.getByDisplayValue('do it')).toBeInTheDocument()
      expect(screen.getByDisplayValue('salt')).toBeInTheDocument()
    })
  })

  describe('food_item variant (mockup emoji-icon-xor-option-d)', () => {
    it('shows food-item fields (icon tab switcher, category), not recipe fields', () => {
      render(
        <ItemFormModal isOpen type="food_item" onSubmit={onSubmit} onClose={onClose} initialItem={null} />
      )
      // Icon tab switcher is present
      expect(screen.getByRole('tablist', { name: 'Icon source' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /Emoji/ })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /Custom/ })).toBeInTheDocument()
      expect(screen.getByText(/Category/)).toBeInTheDocument()
      // Recipe-specific fields should NOT render
      expect(screen.queryByText(/Ingredients/)).not.toBeInTheDocument()
      expect(screen.queryByText(/Prep Time/)).not.toBeInTheDocument()
    })

    it('Emoji tab is active by default; Custom tab reveals the URL input on switch', async () => {
      const user = userEvent.setup()
      render(
        <ItemFormModal isOpen type="food_item" onSubmit={onSubmit} onClose={onClose} initialItem={null} />
      )
      // URL input is hidden in emoji mode
      expect(screen.queryByPlaceholderText(/paste an image URL/i)).not.toBeInTheDocument()

      // Click Custom tab
      await user.click(screen.getByRole('tab', { name: /Custom/ }))

      // URL input now appears
      expect(screen.getByPlaceholderText(/paste an image URL/i)).toBeInTheDocument()
    })

    it('Custom → Emoji tab switch clears the URL and restores emoji mode', async () => {
      const user = userEvent.setup()
      render(
        <ItemFormModal isOpen type="food_item" onSubmit={onSubmit} onClose={onClose} initialItem={null} />
      )
      // Start in emoji mode (default), switch to custom, type a URL
      await user.click(screen.getByRole('tab', { name: /Custom/ }))
      const urlInput = screen.getByPlaceholderText(/paste an image URL/i)
      await user.type(urlInput, 'http://example.com/banana.png')
      expect(urlInput).toHaveValue('http://example.com/banana.png')

      // Switch back to Emoji
      await user.click(screen.getByRole('tab', { name: /Emoji/ }))
      // URL input is hidden again
      expect(screen.queryByPlaceholderText(/paste an image URL/i)).not.toBeInTheDocument()
    })

    it('submits the nested ItemCreate payload with food_item_detail', async () => {
      const user = userEvent.setup()
      render(
        <ItemFormModal isOpen type="food_item" onSubmit={onSubmit} onClose={onClose} initialItem={null} />
      )

      await user.type(screen.getByPlaceholderText(/e\.g\. Banana/), 'Apple')
      await user.click(screen.getByRole('button', { name: /Create/ }))

      expect(onSubmit).toHaveBeenCalledTimes(1)
      const payload = onSubmit.mock.calls[0][0]
      expect(payload.name).toBe('Apple')
      expect(payload.item_type).toBe('food_item')
      expect(payload.food_item_detail).toBeDefined()
      expect(payload.recipe_detail).toBeUndefined()
    })

    it('pre-populates from initialItem in edit mode', () => {
      const initialItem = {
        id: 5,
        name: 'Whole Milk',
        item_type: 'food_item',
        icon_emoji: '🥛',
        icon_url: null,
        is_favorite: false,
        tags: [],
        food_item_detail: { category: 'dairy', shopping_quantity: 1, shopping_unit: 'each' },
      }
      render(
        <ItemFormModal isOpen type="food_item" onSubmit={onSubmit} onClose={onClose} initialItem={initialItem} />
      )
      expect(screen.getByDisplayValue('Whole Milk')).toBeInTheDocument()
      // The category select is populated
      const select = screen.getByRole('combobox')
      expect(select.value).toBe('dairy')
    })
  })
})
