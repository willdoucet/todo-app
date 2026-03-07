import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../mocks/server'
import FamilyMemberManager from '../../../src/components/family-members/FamilyMemberManager'

const API_BASE = 'http://localhost:8000'

describe('FamilyMemberManager', () => {
  it('auto-selects first unused color on mount', async () => {
    render(<FamilyMemberManager />)

    // Wait for members to load
    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument()
    })

    // Alice uses #5A80B0 (Steel Blue), Bob uses #D4915A (Apricot)
    // System member Everyone uses #D4695A but system colors don't count
    // First unused = #D4695A (Soft Red)
    await waitFor(() => {
      const form = screen.getByPlaceholderText('Add family member...').closest('form')
      const softRedButton = form.querySelector('[aria-label="Soft Red"]')
      expect(softRedButton).toHaveAttribute('aria-pressed', 'true')
    })
  })

  it('sends color in POST body on create', async () => {
    const user = userEvent.setup()
    let capturedBody = null

    server.use(
      http.post(`${API_BASE}/family-members`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({
          id: 10,
          name: capturedBody.name,
          color: capturedBody.color,
          photo_url: null,
          is_system: false,
        }, { status: 201 })
      })
    )

    render(<FamilyMemberManager />)

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText('Add family member...')
    await user.type(input, 'Charlie')
    await user.click(screen.getByRole('button', { name: 'Add' }))

    await waitFor(() => {
      expect(capturedBody).not.toBeNull()
      expect(capturedBody.color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(capturedBody.name).toBe('Charlie')
    })
  })

  it('shows ColorPicker in edit mode with member current color', async () => {
    const user = userEvent.setup()
    render(<FamilyMemberManager />)

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument()
    })

    // Click edit on Alice
    const editButtons = screen.getAllByText('Edit')
    await user.click(editButtons[0])

    // Alice has color #5A80B0 (Steel Blue) — should be selected
    await waitFor(() => {
      const steelBlueButton = screen.getAllByLabelText('Steel Blue').find(
        btn => btn.getAttribute('aria-pressed') === 'true'
      )
      expect(steelBlueButton).toBeTruthy()
    })
  })

  it('sends color in PATCH body on update', async () => {
    const user = userEvent.setup()
    let capturedBody = null

    server.use(
      http.patch(`${API_BASE}/family-members/:id`, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({
          id: 2,
          name: capturedBody.name || 'Alice',
          color: capturedBody.color,
          photo_url: null,
          is_system: false,
        })
      })
    )

    render(<FamilyMemberManager />)

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument()
    })

    // Enter edit mode
    const editButtons = screen.getAllByText('Edit')
    await user.click(editButtons[0])

    // Click a different color (Sage)
    await waitFor(() => {
      expect(screen.getAllByLabelText('Sage').length).toBeGreaterThan(0)
    })
    const sageButtons = screen.getAllByLabelText('Sage')
    // Pick the one in the edit form (second occurrence since create form also has one)
    await user.click(sageButtons[sageButtons.length - 1])

    // Save
    await user.click(screen.getByText('Save'))

    await waitFor(() => {
      expect(capturedBody).not.toBeNull()
      expect(capturedBody.color).toBe('#5E9E6B')
    })
  })

  it('disables used colors in the create form color picker', async () => {
    render(<FamilyMemberManager />)

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument()
    })

    // Alice uses #5A80B0 (Steel Blue), Bob uses #D4915A (Apricot)
    // These should be disabled in the create form
    const form = screen.getByPlaceholderText('Add family member...').closest('form')
    const steelBlue = form.querySelector('[aria-label="Steel Blue"]')
    const apricot = form.querySelector('[aria-label="Apricot"]')

    expect(steelBlue).toBeDisabled()
    expect(apricot).toBeDisabled()

    // Soft Red should NOT be disabled (only used by system member Everyone)
    const softRed = form.querySelector('[aria-label="Soft Red"]')
    expect(softRed).not.toBeDisabled()
  })
})
