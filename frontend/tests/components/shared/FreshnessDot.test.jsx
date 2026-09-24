import { render } from '@testing-library/react'
import FreshnessDot from '../../../src/components/shared/FreshnessDot'

describe('FreshnessDot', () => {
  it.each([
    ['ok', 'bg-sage-500'],
    ['bad', 'bg-red-500'],
    ['unknown', 'bg-text-muted'],
  ])('%s renders the %s dot, hidden from screen readers', (tone, cls) => {
    const { container } = render(<FreshnessDot tone={tone} />)
    const dot = container.firstChild
    expect(dot).toHaveClass(cls, 'w-1.5', 'h-1.5', 'rounded-full')
    expect(dot).toHaveAttribute('aria-hidden', 'true')
    expect(dot).toBeEmptyDOMElement()
  })

  it('falls back to the unknown tone', () => {
    const { container } = render(<FreshnessDot tone="bogus" />)
    expect(container.firstChild).toHaveClass('bg-text-muted')
  })

  it('accepts placement classes from the caller', () => {
    const { container } = render(<FreshnessDot tone="ok" className="mt-[7px]" />)
    expect(container.firstChild).toHaveClass('mt-[7px]', 'bg-sage-500')
  })
})
