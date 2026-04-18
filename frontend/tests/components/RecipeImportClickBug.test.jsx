/**
 * Regression test — clicking "Import" on the URL tab must NOT submit the
 * outer recipe-form OR close the modal.
 *
 * Bug (2026-04-17): The RecipeUrlImport component rendered its own
 * `<form>` containing a `<button type="submit">`. That inner form lives
 * inside the outer `<form>` that wraps the whole RecipeFormBody (Manual
 * tab fields + modal chrome). Nested <form> elements are invalid HTML,
 * but React's createElement renders them literally — and a submit event
 * on a nested form bubbles up to the outer form's onSubmit listener.
 * The result: clicking Import fired BOTH the inner form's onSubmit
 * (starting the import) AND the outer form's handleSubmit (trying to
 * POST /items with an empty name, which closed/errored the modal).
 *
 * Fix: remove the inner <form> tag; call importFromUrl via button onClick
 * and Enter-key handler on the URL input.
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import ItemFormModal from '../../src/components/mealboard/ItemFormModal'
import { ToastProvider } from '../../src/components/shared/ToastProvider'
import { server } from '../mocks/server'

vi.mock('../../src/contexts/DarkModeContext', () => ({
  useDarkMode: () => ({ isDark: false }),
}))

const API_BASE = 'http://localhost:8000'

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

describe('Clicking Import on the URL tab', () => {
  it('does NOT submit the outer recipe form (onSubmit prop not called)', async () => {
    // Mock the import endpoint so useRecipeImport can move to pending
    // cleanly. Without this, axios would hit a real localhost endpoint.
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'test-task-1' })
      ),
      http.get(`${API_BASE}/items/import-status/test-task-1`, () =>
        HttpResponse.json({ status: 'progress', step: 'fetching_page' })
      )
    )

    const onSubmitMock = vi.fn()
    const onCloseMock = vi.fn()
    renderModal({ onSubmit: onSubmitMock, onClose: onCloseMock })

    // Switch to the "From URL" tab
    fireEvent.click(screen.getByRole('tab', { name: /From URL/i }))

    // Type a valid URL into the import field
    const urlInput = await screen.findByPlaceholderText(/allrecipes\.com/i)
    fireEvent.change(urlInput, { target: { value: 'https://example.com/recipe' } })

    // Click Import
    const importBtn = screen.getByRole('button', { name: /^Import$/i })
    fireEvent.click(importBtn)

    // Wait for the loading state to be reflected — the step indicator
    // should appear ("Fetching page…") once the submit fires.
    await waitFor(() => {
      expect(screen.getByText(/Fetching page|Queued/i)).toBeInTheDocument()
    })

    // The outer recipe form MUST NOT have been submitted. This is the
    // regression assertion — with the nested-form bug it fires.
    expect(onSubmitMock).not.toHaveBeenCalled()
    // And the modal must remain open.
    expect(onCloseMock).not.toHaveBeenCalled()
  })

  it('pressing Enter in the URL input also triggers import without submitting the outer form', async () => {
    server.use(
      http.post(`${API_BASE}/items/import-from-url`, () =>
        HttpResponse.json({ task_id: 'test-task-2' })
      ),
      http.get(`${API_BASE}/items/import-status/test-task-2`, () =>
        HttpResponse.json({ status: 'progress', step: 'fetching_page' })
      )
    )

    const onSubmitMock = vi.fn()
    const onCloseMock = vi.fn()
    renderModal({ onSubmit: onSubmitMock, onClose: onCloseMock })

    fireEvent.click(screen.getByRole('tab', { name: /From URL/i }))
    const urlInput = await screen.findByPlaceholderText(/allrecipes\.com/i)
    fireEvent.change(urlInput, { target: { value: 'https://example.com/recipe' } })

    // Pressing Enter in the URL input should start the import, NOT submit
    // the outer form.
    fireEvent.keyDown(urlInput, { key: 'Enter', code: 'Enter' })

    await waitFor(() => {
      expect(screen.getByText(/Fetching page|Queued/i)).toBeInTheDocument()
    })
    expect(onSubmitMock).not.toHaveBeenCalled()
    expect(onCloseMock).not.toHaveBeenCalled()
  })
})
