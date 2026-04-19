import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import UndoMealCard from '../../../src/components/mealboard/UndoMealCard'

describe('UndoMealCard', () => {
  const expiresIn = (ms) => new Date(Date.now() + ms)

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'setInterval', 'clearInterval', 'clearTimeout', 'Date'] })
    vi.setSystemTime(new Date('2026-04-18T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders as a native <button> with a descriptive aria-label', () => {
    render(<UndoMealCard mealName="Pasta" expiresAt={expiresIn(5000)} onUndo={() => {}} />)
    const btn = screen.getByRole('button', { name: /Undo deletion of Pasta/ })
    expect(btn.tagName).toBe('BUTTON')
    expect(btn.getAttribute('aria-label')).toMatch(/Undo deletion of Pasta, \d+ seconds remaining/)
  })

  it('auto-focuses on mount so screen-reader users hear the undo affordance', () => {
    render(<UndoMealCard mealName="Pasta" expiresAt={expiresIn(5000)} onUndo={() => {}} />)
    const btn = screen.getByRole('button', { name: /Undo deletion of/ })
    expect(document.activeElement).toBe(btn)
  })

  it('renders the struck-through meal name + "Tap to undo" action line', () => {
    render(<UndoMealCard mealName="Pasta" expiresAt={expiresIn(5000)} onUndo={() => {}} />)
    expect(screen.getByText('Pasta').className).toMatch(/line-through/)
    expect(screen.getByText('Tap to undo')).toBeInTheDocument()
  })

  it('calls onUndo exactly once on click and disables further clicks', async () => {
    const onUndo = vi.fn()
    render(<UndoMealCard mealName="Pasta" expiresAt={expiresIn(5000)} onUndo={onUndo} />)
    const btn = screen.getByRole('button', { name: /Undo deletion of/ })

    // Synthetic clicks (fake timers + userEvent can fight; raw dispatch is fine here).
    await act(async () => {
      btn.click()
      btn.click()
      btn.click()
    })
    expect(onUndo).toHaveBeenCalledTimes(1)
  })

  it('updates the seconds-remaining suffix each second (for reduced-motion users)', async () => {
    render(<UndoMealCard mealName="Pasta" expiresAt={expiresIn(5000)} onUndo={() => {}} />)
    const btn = screen.getByRole('button', { name: /Undo deletion of/ })
    expect(btn.getAttribute('aria-label')).toContain('5 seconds remaining')

    await act(async () => {
      vi.advanceTimersByTime(1100)
    })
    expect(btn.getAttribute('aria-label')).toContain('4 seconds remaining')

    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    expect(btn.getAttribute('aria-label')).toContain('2 seconds remaining')
  })

  it('hides the animated bar under motion-reduce:hidden and shows the text fallback', () => {
    render(<UndoMealCard mealName="Pasta" expiresAt={expiresIn(5000)} onUndo={() => {}} />)
    // The countdown bar carries the motion-reduce:hidden class and is aria-hidden
    const bar = document.querySelector('[aria-hidden="true"].motion-reduce\\:hidden')
    expect(bar).toBeInTheDocument()
    // The "· Ns" text fallback carries motion-reduce:inline + is hidden by default
    const fallback = document.querySelector('.motion-reduce\\:inline.hidden')
    expect(fallback).toBeInTheDocument()
    expect(fallback.textContent).toMatch(/·\s+\d+s/)
  })

  it('clears its setInterval on unmount (no setState-on-unmounted warnings)', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const { unmount } = render(
      <UndoMealCard mealName="Pasta" expiresAt={expiresIn(5000)} onUndo={() => {}} />
    )
    unmount()
    // Advance past the point a leaked interval would have fired
    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(warn).not.toHaveBeenCalled()
    warn.mockRestore()
  })
})
