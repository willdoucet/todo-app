import { useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'

export default function ListPanel({
  lists,
  selectedListId,
  onSelectList,
  onCreateList,
  onUpdateList,
  onDeleteList,
  isLoading,
  taskCounts = {},
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingList, setEditingList] = useState(null)
  const [formName, setFormName] = useState('')
  const [formColor, setFormColor] = useState('#6B7280')

  const colors = [
    '#6B7280', // Gray
    '#3B82F6', // Blue
    '#10B981', // Green
    '#F59E0B', // Amber
    '#EF4444', // Red
    '#8B5CF6', // Purple
    '#EC4899', // Pink
    '#06B6D4', // Cyan
  ]

  const openCreateForm = () => {
    setEditingList(null)
    setFormName('')
    setFormColor('#6B7280')
    setIsFormOpen(true)
  }

  const openEditForm = (list) => {
    setEditingList(list)
    setFormName(list.name)
    setFormColor(list.color || '#6B7280')
    setIsFormOpen(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formName.trim()) return

    if (editingList) {
      await onUpdateList(editingList.id, { name: formName, color: formColor })
    } else {
      await onCreateList({ name: formName, color: formColor })
    }
    setIsFormOpen(false)
  }

  const handleDelete = async (listId) => {
    if (window.confirm('Delete this list and all its tasks?')) {
      await onDeleteList(listId)
    }
  }

  const selectedList = lists.find(l => l.id === selectedListId)

  // List item component (reused in both mobile and desktop views)
  const ListItem = ({ list, showActions = true, isMobile = false }) => {
    const isSelected = list.id === selectedListId
    const taskCount = taskCounts[list.id] || 0

    return (
      <div
        className={`
          group flex items-center gap-3 rounded-lg cursor-pointer transition-colors duration-150
          ${isMobile ? 'px-4 py-3.5' : 'px-3 py-2.5'}
          ${isSelected
            ? 'bg-gray-100 dark:bg-gray-800'
            : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'
          }
        `}
        onClick={() => {
          onSelectList(list.id)
          setIsOpen(false)
        }}
      >
        {/* Color indicator */}
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: list.color || '#6B7280' }}
        />

        {/* List name */}
        <span className={`
          flex-1 min-w-0 text-sm truncate transition-colors
          ${isSelected
            ? 'text-gray-900 dark:text-gray-100 font-medium'
            : 'text-gray-600 dark:text-gray-300'
          }
        `}>
          {list.name}
        </span>

        {/* Task count */}
        <span className={`
          text-xs tabular-nums
          ${isSelected
            ? 'text-gray-500 dark:text-gray-400'
            : 'text-gray-400 dark:text-gray-500'
          }
        `}>
          {taskCount}
        </span>

        {/* Edit/Delete buttons (desktop only) */}
        {showActions && (
          <div className="hidden sm:flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
            <button
              onClick={(e) => {
                e.stopPropagation()
                openEditForm(list)
              }}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="Edit list"
            >
              <PencilIcon className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleDelete(list.id)
              }}
              className="p-1.5 text-gray-400 hover:text-red-500 dark:hover:text-red-400 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="Delete list"
            >
              <TrashIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      {/* Mobile: Drawer trigger button */}
      <div className="sm:hidden flex items-center gap-2 mb-4">
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2.5 px-3 py-2.5 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 active:scale-[0.98] transition-transform"
        >
          <div
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: selectedList?.color || '#6B7280' }}
          />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
            {selectedList?.name || 'Select List'}
          </span>
          <ChevronRightIcon className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* Mobile: Slide-in drawer */}
      <Transition show={isOpen} as="div">
        <Dialog onClose={() => setIsOpen(false)} className="relative z-50 sm:hidden">
          <Transition.Child
            enter="ease-out duration-200"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/20 dark:bg-black/40 backdrop-blur-sm" />
          </Transition.Child>

          <div className="fixed inset-0 flex">
            <Transition.Child
              enter="ease-out duration-250"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="ease-in duration-200"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <Dialog.Panel className="relative w-72 max-w-[85vw] bg-white dark:bg-gray-900 h-full shadow-2xl flex flex-col">
                {/* Drawer header */}
                <div className="flex items-center justify-between px-4 py-4 border-b border-gray-100 dark:border-gray-800">
                  <Dialog.Title className="text-base font-semibold text-gray-900 dark:text-gray-100">
                    Lists
                  </Dialog.Title>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-2 -mr-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                {/* List items */}
                <div className="flex-1 overflow-y-auto py-2">
                  {isLoading ? (
                    <div className="flex justify-center py-12">
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-gray-300 dark:border-gray-600 border-t-gray-600 dark:border-t-gray-300" />
                    </div>
                  ) : lists.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8 px-4">
                      No lists yet
                    </p>
                  ) : (
                    lists.map(list => <ListItem key={list.id} list={list} showActions={false} isMobile={true} />)
                  )}
                </div>

                {/* Create button */}
                <div className="p-4 border-t border-gray-100 dark:border-gray-800">
                  <button
                    onClick={() => {
                      setIsOpen(false)
                      openCreateForm()
                    }}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 active:scale-[0.98] transition-all"
                  >
                    <PlusIcon className="w-4 h-4" />
                    New List
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>

      {/* Desktop: Fixed side panel */}
      <aside className="hidden sm:flex fixed left-[5.5rem] top-[5.5rem] bottom-3 w-52 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl flex-col z-10">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Lists</h2>
        </div>

        {/* List items */}
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-gray-300 dark:border-gray-600 border-t-gray-600 dark:border-t-gray-300" />
            </div>
          ) : lists.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6 px-2">
              No lists yet
            </p>
          ) : (
            lists.map(list => <ListItem key={list.id} list={list} />)
          )}
        </div>

        {/* Create button */}
        <div className="p-3 border-t border-gray-100 dark:border-gray-800">
          <button
            onClick={openCreateForm}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            New List
          </button>
        </div>
      </aside>

      {/* Create/Edit List Modal */}
      <Transition show={isFormOpen} as="div">
        <Dialog onClose={() => setIsFormOpen(false)} className="relative z-50">
          <Transition.Child
            enter="ease-out duration-200"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/20 dark:bg-black/40 backdrop-blur-sm" />
          </Transition.Child>

          <div className="fixed inset-0 flex items-center justify-center p-4">
            <Transition.Child
              enter="ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-sm bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-6">
                <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-5">
                  {editingList ? 'Edit List' : 'New List'}
                </Dialog.Title>

                <form onSubmit={handleSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Name
                    </label>
                    <input
                      type="text"
                      value={formName}
                      onChange={(e) => setFormName(e.target.value)}
                      placeholder="List name"
                      required
                      autoFocus
                      className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:ring-2 focus:ring-gray-900/10 dark:focus:ring-gray-100/10 focus:border-gray-300 dark:focus:border-gray-600 outline-none transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Color
                    </label>
                    <div className="flex gap-2.5 flex-wrap">
                      {colors.map(color => (
                        <button
                          key={color}
                          type="button"
                          onClick={() => setFormColor(color)}
                          className={`
                            w-7 h-7 rounded-full transition-all
                            ${formColor === color
                              ? 'ring-2 ring-offset-2 ring-gray-400 dark:ring-gray-500 dark:ring-offset-gray-900'
                              : 'hover:scale-110'
                            }
                          `}
                          style={{ backgroundColor: color }}
                          aria-label={`Select color`}
                        />
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setIsFormOpen(false)}
                      className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 text-sm font-medium text-white bg-gray-900 dark:bg-gray-100 dark:text-gray-900 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
                    >
                      {editingList ? 'Save' : 'Create'}
                    </button>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>
    </>
  )
}
