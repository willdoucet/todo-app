import { Fragment } from 'react'
import { Menu, MenuButton, MenuItem, MenuItems, Transition } from '@headlessui/react'
import { ChevronDownIcon, FunnelIcon } from '@heroicons/react/20/solid'

export default function FilterMenu({ currentFilter = 'all', onFilterChange }) {
  const filters = [
    { id: 'all', label: 'All Tasks' },
    { id: 'pending', label: 'Pending' },
    { id: 'completed', label: 'Completed' },
    { id: 'overdue', label: 'Overdue' },
    { id: 'today', label: 'Due Today' },
    { id: 'this-week', label: 'This Week' },
  ]

  const activeFilter = filters.find(f => f.id === currentFilter) || filters[0]

  return (
    <Menu as="div" className="relative inline-block text-left">
      <div>
        <MenuButton className="
          inline-flex items-center gap-x-1.5 rounded-lg 
          bg-white dark:bg-gray-800 px-3 py-2 sm:px-3.5 sm:py-2 text-xs sm:text-sm 
          font-medium text-gray-700 dark:text-gray-300
          shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600
          hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          dark:focus:ring-offset-gray-800 transition-all duration-200
        ">
          <FunnelIcon className="-ml-0.5 h-4 w-4 sm:h-5 sm:w-5 text-gray-400 dark:text-gray-500" aria-hidden="true" />
          <span className="hidden sm:inline">{activeFilter.label}</span>
          <span className="sm:hidden">Filter</span>
          <ChevronDownIcon className="-mr-1 h-4 w-4 sm:h-5 sm:w-5 text-gray-400 dark:text-gray-500" aria-hidden="true" />
        </MenuButton>
      </div>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <MenuItems className="
          absolute right-0 z-10 mt-2 w-56 sm:w-64 origin-top-right 
          rounded-xl bg-white dark:bg-gray-800 shadow-xl ring-1 ring-black/5 dark:ring-gray-700
          focus:outline-none divide-y divide-gray-100 dark:divide-gray-700
          max-h-[80vh] overflow-y-auto
        ">
          <div className="py-1.5">
            {filters.map((filter) => (
              <MenuItem key={filter.id}>
                {({ active }) => (
                  <button
                    type="button"
                    onClick={() => onFilterChange?.(filter.id)}
                    className={`
                      block w-full px-4 py-2.5 sm:py-3 text-left text-sm sm:text-base
                      transition-colors duration-150
                      ${active ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'}
                      ${currentFilter === filter.id ? 'font-semibold bg-blue-50/50 dark:bg-blue-900/20' : 'font-normal'}
                    `}
                  >
                    <span className="flex items-center justify-between">
                      {filter.label}
                      {currentFilter === filter.id && (
                        <span className="ml-2 text-blue-600 dark:text-blue-400 font-bold">✓</span>
                      )}
                    </span>
                  </button>
                )}
              </MenuItem>
            ))}
          </div>
        </MenuItems>
      </Transition>
    </Menu>
  )
}