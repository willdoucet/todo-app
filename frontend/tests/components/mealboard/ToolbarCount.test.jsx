import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ToolbarCount from '../../../src/components/mealboard/ToolbarCount'

describe('ToolbarCount', () => {
  it('renders count with plural label', () => {
    render(<ToolbarCount count={7} singular="recipe" plural="recipes" />)
    expect(screen.getByText('7 recipes')).toBeInTheDocument()
  })

  it('renders singular label at count=1', () => {
    render(<ToolbarCount count={1} singular="recipe" plural="recipes" />)
    expect(screen.getByText('1 recipe')).toBeInTheDocument()
  })

  it('renders plural label at count=0', () => {
    render(<ToolbarCount count={0} singular="recipe" plural="recipes" />)
    expect(screen.getByText('0 recipes')).toBeInTheDocument()
  })

  it('renders "X of Y" when totalCount is provided and differs', () => {
    render(<ToolbarCount count={3} totalCount={7} singular="recipe" plural="recipes" />)
    expect(screen.getByText('3 of 7')).toBeInTheDocument()
  })
})
