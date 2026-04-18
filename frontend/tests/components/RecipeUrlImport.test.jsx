/**
 * Tests for RecipeUrlImport — the URL-import view that lives inside the
 * recipe modal. Covers the four visual states (input / loading / preview /
 * error), prop wiring, and the broken-image fallback.
 *
 * Network via MSW (per-test overrides), NOT vi.mock('axios').
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { server } from '../mocks/server'
import RecipeUrlImport from '../../src/components/mealboard/RecipeUrlImport'

const API_BASE = 'http://localhost:8000'

function sampleRecipe(overrides = {}) {
  return {
    name: 'Honey Garlic Chicken',
    tags: ['quick', 'chicken'],
    source_url: 'https://example.com/recipe',
    recipe_detail: {
      description: 'Sweet and savory',
      ingredients: [
        { name: 'Chicken', quantity: 1, unit: 'lb', category: 'Protein' },
        { name: 'Honey', quantity: 3, unit: 'tbsp', category: 'Pantry' },
        { name: 'Garlic', quantity: 4, unit: 'cloves', category: 'Produce' },
      ],
      instructions: '1. Cook.',
      prep_time_minutes: 15,
      cook_time_minutes: 30,
      servings: 4,
      image_url: null,
      source_url: 'https://example.com/recipe',
      ...overrides,
    },
  }
}

describe('RecipeUrlImport', () => {
  it('initial state: renders URL input with disabled Import button', () => {
    render(<RecipeUrlImport />)
    expect(screen.getByText('Paste a recipe URL')).toBeInTheDocument()
    const importBtn = screen.getByRole('button', { name: 'Import' })
    expect(importBtn).toBeDisabled()
  })

  it('typing a valid URL enables the Import button', async () => {
    const user = userEvent.setup()
    render(<RecipeUrlImport />)
    const input = screen.getByRole('textbox', { name: /Paste a recipe URL/i })
    await user.type(input, 'https://example.com/recipe')
    expect(screen.getByRole('button', { name: 'Import' })).toBeEnabled()
  })

  it('clicking Import transitions to the loading state (step indicator + skeleton)', async () => {
    // Never-resolving submit so we stay in the loading/pending state.
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'slow' })
      ),
      http.get(`${API_BASE}/items/import-status/slow`, () =>
        HttpResponse.json({ status: 'pending', step: 'queued' })
      )
    )

    const user = userEvent.setup()
    render(<RecipeUrlImport />)
    await user.type(
      screen.getByRole('textbox', { name: /Paste a recipe URL/i }),
      'https://example.com/recipe'
    )
    await user.click(screen.getByRole('button', { name: 'Import' }))

    // Loading-state container has aria-busy
    await waitFor(() =>
      expect(document.querySelector('[aria-busy="true"]')).toBeInTheDocument()
    )
    // Step label (aria-live polite) shows a "…" indicator from STEP_LABELS
    // ("Queued…" or "Fetching page…" — both are valid, but one must render)
    const label = document.querySelector('[aria-live="polite"]')
    expect(label).toBeInTheDocument()
    expect(label.textContent).toMatch(/…/)
  })

  it('full happy path: preview card shows name + ingredient count + Use This Recipe', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'ok' })
      ),
      http.get(`${API_BASE}/items/import-status/ok`, () =>
        HttpResponse.json({ status: 'complete', recipe: sampleRecipe() })
      )
    )

    const user = userEvent.setup()
    render(<RecipeUrlImport />)
    await user.type(
      screen.getByRole('textbox', { name: /Paste a recipe URL/i }),
      'https://example.com/recipe'
    )
    await user.click(screen.getByRole('button', { name: 'Import' }))

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: 'Honey Garlic Chicken' })
      ).toBeInTheDocument()
    )
    // 3 ingredients per the sample recipe
    expect(screen.getByText(/3 ingredients/)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Use This Recipe' })
    ).toBeInTheDocument()
  })

  it('clicking Use This Recipe calls onUseRecipe with the recipe payload', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'ok' })
      ),
      http.get(`${API_BASE}/items/import-status/ok`, () =>
        HttpResponse.json({ status: 'complete', recipe: sampleRecipe() })
      )
    )

    const onUseRecipe = vi.fn()
    const user = userEvent.setup()
    render(<RecipeUrlImport onUseRecipe={onUseRecipe} />)
    await user.type(
      screen.getByRole('textbox', { name: /Paste a recipe URL/i }),
      'https://example.com/recipe'
    )
    await user.click(screen.getByRole('button', { name: 'Import' }))

    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'Use This Recipe' })
      ).toBeInTheDocument()
    )
    await user.click(screen.getByRole('button', { name: 'Use This Recipe' }))
    expect(onUseRecipe).toHaveBeenCalledTimes(1)
    expect(onUseRecipe.mock.calls[0][0].name).toBe('Honey Garlic Chicken')
  })

  it('retryable error (fetch_failed): Try Again + Enter Manually; Try Again is primary', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'err' })
      ),
      http.get(`${API_BASE}/items/import-status/err`, () =>
        HttpResponse.json({ status: 'failed', error_code: 'fetch_failed' })
      )
    )

    const user = userEvent.setup()
    render(<RecipeUrlImport />)
    await user.type(
      screen.getByRole('textbox', { name: /Paste a recipe URL/i }),
      'https://example.com/recipe'
    )
    await user.click(screen.getByRole('button', { name: 'Import' }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toBeInTheDocument()
    )
    const tryAgain = screen.getByRole('button', { name: 'Try Again' })
    const enterManually = screen.getByRole('button', { name: 'Enter Manually' })
    expect(tryAgain).toBeInTheDocument()
    expect(enterManually).toBeInTheDocument()

    // Retryable: Try Again is primary (terracotta bg-* class).
    expect(tryAgain.className).toMatch(/bg-terracotta-500/)
    expect(enterManually.className).not.toMatch(/bg-terracotta-500/)
  })

  it('non-retryable error (not_recipe): Enter Manually is primary', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'err' })
      ),
      http.get(`${API_BASE}/items/import-status/err`, () =>
        HttpResponse.json({ status: 'failed', error_code: 'not_recipe' })
      )
    )

    const user = userEvent.setup()
    render(<RecipeUrlImport />)
    await user.type(
      screen.getByRole('textbox', { name: /Paste a recipe URL/i }),
      'https://example.com/recipe'
    )
    await user.click(screen.getByRole('button', { name: 'Import' }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toBeInTheDocument()
    )
    const tryAgain = screen.getByRole('button', { name: 'Try Again' })
    const enterManually = screen.getByRole('button', { name: 'Enter Manually' })

    // Non-retryable: Enter Manually is primary (terracotta), Try Again is secondary.
    expect(enterManually.className).toMatch(/bg-terracotta-500/)
    expect(tryAgain.className).not.toMatch(/bg-terracotta-500/)
  })

  it('clicking Enter Manually calls onEnterManually prop', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'err' })
      ),
      http.get(`${API_BASE}/items/import-status/err`, () =>
        HttpResponse.json({ status: 'failed', error_code: 'not_recipe' })
      )
    )

    const onEnterManually = vi.fn()
    const user = userEvent.setup()
    render(<RecipeUrlImport onEnterManually={onEnterManually} />)
    await user.type(
      screen.getByRole('textbox', { name: /Paste a recipe URL/i }),
      'https://example.com/recipe'
    )
    await user.click(screen.getByRole('button', { name: 'Import' }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toBeInTheDocument()
    )
    await user.click(screen.getByRole('button', { name: 'Enter Manually' }))
    expect(onEnterManually).toHaveBeenCalledTimes(1)
  })

  it('broken image: firing img onError swaps to emoji fallback', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'ok' })
      ),
      http.get(`${API_BASE}/items/import-status/ok`, () =>
        HttpResponse.json({
          status: 'complete',
          recipe: sampleRecipe({ image_url: 'https://bad/image.jpg' }),
        })
      )
    )

    const user = userEvent.setup()
    const { container } = render(<RecipeUrlImport />)
    await user.type(
      screen.getByRole('textbox', { name: /Paste a recipe URL/i }),
      'https://example.com/recipe'
    )
    await user.click(screen.getByRole('button', { name: 'Import' }))

    // Wait for the preview card (has the <img> with the bad URL)
    const img = await waitFor(() => {
      const found = container.querySelector('img[src="https://bad/image.jpg"]')
      expect(found).toBeTruthy()
      return found
    })

    // Trigger onError; the component swaps to the emoji fallback.
    fireEvent.error(img)

    await waitFor(() => {
      expect(
        container.querySelector('img[src="https://bad/image.jpg"]')
      ).toBeNull()
    })
    // 🍽️ emoji rendered in the fallback div
    expect(screen.getByText('🍽️')).toBeInTheDocument()
  })

  it('initialUrl prop pre-fills the input', () => {
    render(<RecipeUrlImport initialUrl="https://example.com/prefill" />)
    const input = screen.getByRole('textbox', { name: /Paste a recipe URL/i })
    expect(input).toHaveValue('https://example.com/prefill')
    // With a valid URL pre-filled, Import should be enabled immediately.
    expect(screen.getByRole('button', { name: 'Import' })).toBeEnabled()
  })
})
