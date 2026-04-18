/**
 * Tests for the paste-detect auto-switch on the recipe form's name field.
 *
 * When a user pastes a URL into the recipe name input, ItemFormModal should:
 *   1. Switch the active tab to the URL-import view.
 *   2. Pre-fill the URL into the import input.
 *   3. Fire an info toast (hence the ToastProvider wrap).
 *
 * Edit mode suppresses the whole flow (tab switcher is hidden; paste-detect
 * early-returns) since re-importing over an existing recipe isn't supported.
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

import ItemFormModal from '../../src/components/mealboard/ItemFormModal'
import { ToastProvider } from '../../src/components/shared/ToastProvider'

// EmojiPicker (loaded indirectly through the food-item branch) and any other
// dark-mode-dependent leaf would complain without this. Recipe branch doesn't
// use it, but keeping the mock matches the existing ItemFormModal test suite.
vi.mock('../../src/contexts/DarkModeContext', () => ({
  useDarkMode: () => ({ isDark: false }),
}))

function renderModal(props = {}) {
  return render(
    <ToastProvider>
      <ItemFormModal
        type="recipe"
        isOpen
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        {...props}
      />
    </ToastProvider>
  )
}

describe('RecipeFormBody paste detection', () => {
  it('pasting a URL into the name field switches to the URL import tab', async () => {
    renderModal()

    // Recipe name input — the modal renders it with a placeholder matching
    // "e.g., Honey Garlic Chicken"
    const nameInput = screen.getByPlaceholderText(/Honey Garlic Chicken/i)

    // Fire a paste event with a URL payload. The component calls
    // e.clipboardData.getData('text') and e.preventDefault().
    fireEvent.paste(nameInput, {
      clipboardData: {
        getData: (fmt) => (fmt === 'text' ? 'https://example.com/recipe' : ''),
      },
    })

    // Tab switch is synchronous, but the import view mounts a child hook
    // (useRecipeImport) — wrap assertions in waitFor to be safe.
    await waitFor(() => {
      // URL import view copy is visible
      expect(screen.getByText(/Paste a recipe URL/i)).toBeInTheDocument()
    })

    // The import input is pre-filled with the pasted URL
    const urlInput = screen.getByRole('textbox', { name: /Paste a recipe URL/i })
    expect(urlInput).toHaveValue('https://example.com/recipe')
  })

  it('pasting plain text (non-URL) does NOT switch tabs', () => {
    renderModal()

    const nameInput = screen.getByPlaceholderText(/Honey Garlic Chicken/i)

    fireEvent.paste(nameInput, {
      clipboardData: {
        getData: (fmt) => (fmt === 'text' ? 'Just a recipe name' : ''),
      },
    })

    // Manual form stays visible — ingredients / instructions labels still
    // render. The URL-import view copy should NOT be present.
    expect(screen.getByText(/Ingredients/)).toBeInTheDocument()
    expect(screen.queryByText(/Paste a recipe URL/i)).not.toBeInTheDocument()
  })

  it('in edit mode: tab switcher is hidden and URL paste does not switch tabs', () => {
    const initialItem = {
      id: 42,
      name: 'Existing Recipe',
      item_type: 'recipe',
      is_favorite: false,
      tags: [],
      recipe_detail: {
        description: 'An existing one',
        ingredients: [{ name: 'salt', quantity: 1, unit: 'tsp', category: 'Pantry' }],
        instructions: 'mix',
        prep_time_minutes: 5,
        cook_time_minutes: 10,
        servings: 2,
        image_url: '',
      },
    }

    renderModal({ initialItem })

    // Tab switcher is hidden entirely when editing
    expect(
      screen.queryByRole('tablist', { name: 'Recipe creation mode' })
    ).not.toBeInTheDocument()

    // Paste a URL into the name field — handler early-returns on isEditing
    const nameInput = screen.getByDisplayValue('Existing Recipe')
    fireEvent.paste(nameInput, {
      clipboardData: {
        getData: (fmt) => (fmt === 'text' ? 'https://example.com/recipe' : ''),
      },
    })

    // URL-import view must NOT appear
    expect(screen.queryByText(/Paste a recipe URL/i)).not.toBeInTheDocument()
    // Manual form still visible (Ingredients label)
    expect(screen.getByText(/Ingredients/)).toBeInTheDocument()
  })
})
