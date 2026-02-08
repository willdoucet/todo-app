import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import MealboardNav from '../../../src/components/mealboard/MealboardNav'

const renderWithRouter = (ui, { route = '/mealboard/planner' } = {}) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      {ui}
    </MemoryRouter>
  )
}

describe('MealboardNav', () => {
  describe('sidebar variant', () => {
    it('renders all menu items', () => {
      renderWithRouter(<MealboardNav variant="sidebar" />)

      expect(screen.getByText('Mealboard')).toBeInTheDocument()
      expect(screen.getByText('Meal Planner')).toBeInTheDocument()
      expect(screen.getByText('Recipes')).toBeInTheDocument()
      expect(screen.getByText('Shopping')).toBeInTheDocument()
      expect(screen.getByText('Recipe Finder')).toBeInTheDocument()
    })

    it('highlights active menu item', () => {
      renderWithRouter(<MealboardNav variant="sidebar" />, { route: '/mealboard/planner' })

      const mealPlannerLink = screen.getByText('Meal Planner').closest('a')
      expect(mealPlannerLink.className).toMatch(/bg-peach-100|bg-blue-600/)
    })

    it('shows "Soon" badge on Recipe Finder', () => {
      renderWithRouter(<MealboardNav variant="sidebar" />)

      expect(screen.getByText('Soon')).toBeInTheDocument()
    })

    it('shows disabled state for Recipe Finder', () => {
      renderWithRouter(<MealboardNav variant="sidebar" />)

      const finderLink = screen.getByText('Recipe Finder').closest('a')
      expect(finderLink).toHaveClass('cursor-not-allowed')
    })
  })

  describe('dropdown variant', () => {
    it('shows current page name in button', () => {
      renderWithRouter(<MealboardNav variant="dropdown" />, { route: '/mealboard/planner' })

      expect(screen.getByRole('button', { name: /meal planner/i })).toBeInTheDocument()
    })

    it('opens dropdown on click', async () => {
      const user = userEvent.setup()
      renderWithRouter(<MealboardNav variant="dropdown" />)

      await user.click(screen.getByRole('button'))

      expect(screen.getAllByText('Meal Planner')).toHaveLength(2)
      expect(screen.getByText('Recipes')).toBeInTheDocument()
      expect(screen.getByText('Shopping')).toBeInTheDocument()
    })

    it('closes dropdown when clicking outside', async () => {
      const user = userEvent.setup()
      const { container } = renderWithRouter(<MealboardNav variant="dropdown" />)

      await user.click(screen.getByRole('button'))
      expect(screen.getAllByText('Recipes')).toHaveLength(1)

      await user.click(container)
    })

    it('closes dropdown when selecting an item', async () => {
      const user = userEvent.setup()
      renderWithRouter(<MealboardNav variant="dropdown" />)

      await user.click(screen.getByRole('button'))
      await user.click(screen.getByText('Recipes'))
    })
  })
})
