import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecipeFormModal from '../../../src/components/mealboard/RecipeFormModal'

describe('RecipeFormModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSubmit: vi.fn().mockResolvedValue({}),
    recipe: null,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('create mode', () => {
    it('renders with "Add New Recipe" title', () => {
      render(<RecipeFormModal {...defaultProps} />)

      expect(screen.getByText('Add New Recipe')).toBeInTheDocument()
    })

    it('renders required fields', () => {
      render(<RecipeFormModal {...defaultProps} />)

      expect(screen.getByPlaceholderText(/honey garlic chicken/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/step-by-step cooking instructions/i)).toBeInTheDocument()
    })

    it('renders optional fields', () => {
      render(<RecipeFormModal {...defaultProps} />)

      expect(screen.getByPlaceholderText(/brief description/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText('15')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('30')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('4')).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/example.com\/image/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/quick, chicken, dinner/i)).toBeInTheDocument()
    })

    it('submits form with entered data', async () => {
      const user = userEvent.setup()
      render(<RecipeFormModal {...defaultProps} />)

      await user.type(screen.getByPlaceholderText(/honey garlic chicken/i), 'Test Recipe')
      await user.type(screen.getByPlaceholderText(/step-by-step cooking instructions/i), 'Test instructions')
      await user.click(screen.getByText('Add Recipe'))

      await waitFor(() => {
        expect(defaultProps.onSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Recipe',
            instructions: 'Test instructions',
          })
        )
      })
    })

    it('calls onClose when clicking Cancel', async () => {
      const user = userEvent.setup()
      render(<RecipeFormModal {...defaultProps} />)

      await user.click(screen.getByText('Cancel'))
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('edit mode', () => {
    const editRecipe = {
      id: 1,
      name: 'Existing Recipe',
      description: 'Existing description',
      ingredients: [
        { name: 'Ingredient 1', quantity: 2, unit: 'cups', category: 'Pantry' },
      ],
      instructions: 'Existing instructions',
      prep_time_minutes: 10,
      cook_time_minutes: 20,
      servings: 4,
      image_url: 'https://example.com/image.jpg',
      is_favorite: true,
      tags: ['tag1', 'tag2'],
    }

    it('renders with "Edit Recipe" title', () => {
      render(<RecipeFormModal {...defaultProps} recipe={editRecipe} />)

      expect(screen.getByText('Edit Recipe')).toBeInTheDocument()
    })

    it('pre-fills form with existing recipe data', () => {
      render(<RecipeFormModal {...defaultProps} recipe={editRecipe} />)

      expect(screen.getByPlaceholderText(/honey garlic chicken/i)).toHaveValue('Existing Recipe')
      expect(screen.getByPlaceholderText(/brief description/i)).toHaveValue('Existing description')
      expect(screen.getByPlaceholderText(/step-by-step cooking instructions/i)).toHaveValue('Existing instructions')
    })

    it('shows "Update Recipe" button text', () => {
      render(<RecipeFormModal {...defaultProps} recipe={editRecipe} />)

      expect(screen.getByText('Update Recipe')).toBeInTheDocument()
    })
  })

  describe('ingredients', () => {
    it('starts with one empty ingredient row', () => {
      render(<RecipeFormModal {...defaultProps} />)

      const ingredientInputs = screen.getAllByPlaceholderText('Ingredient')
      expect(ingredientInputs).toHaveLength(1)
    })

    it('adds new ingredient row when clicking add button', async () => {
      const user = userEvent.setup()
      render(<RecipeFormModal {...defaultProps} />)

      await user.click(screen.getByText('+ Add Ingredient'))

      const ingredientInputs = screen.getAllByPlaceholderText('Ingredient')
      expect(ingredientInputs).toHaveLength(2)
    })

    it('removes ingredient row when clicking remove button', async () => {
      const user = userEvent.setup()
      render(<RecipeFormModal {...defaultProps} />)

      await user.click(screen.getByText('+ Add Ingredient'))

      const removeButtons = document.querySelectorAll('button[type="button"]')
      const removeButton = Array.from(removeButtons).find(btn =>
        btn.querySelector('svg path[d*="M6 18L18 6"]')
      )

      if (removeButton) {
        await user.click(removeButton)
      }

      const ingredientInputs = screen.getAllByPlaceholderText('Ingredient')
      expect(ingredientInputs).toHaveLength(1)
    })
  })

  describe('favorite toggle', () => {
    it('toggles favorite state', async () => {
      const user = userEvent.setup()
      render(<RecipeFormModal {...defaultProps} />)

      const favoriteToggle = screen.getByText('Mark as favorite').previousElementSibling
      await user.click(favoriteToggle)
    })
  })

  describe('validation', () => {
    it('requires name field', async () => {
      render(<RecipeFormModal {...defaultProps} />)

      const nameInput = screen.getByPlaceholderText(/honey garlic chicken/i)
      expect(nameInput).toBeRequired()
    })

    it('requires instructions field', async () => {
      render(<RecipeFormModal {...defaultProps} />)

      const instructionsInput = screen.getByPlaceholderText(/step-by-step cooking instructions/i)
      expect(instructionsInput).toBeRequired()
    })
  })
})
