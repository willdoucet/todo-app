import { useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import axios from 'axios'
import TodoItem from '../components/TodoItem'
import TodoForm from '../components/TodoForm'
import FilterMenu from '../components/FilterMenu'
import AddButton from '../components/AddButton'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function TodoPage() {
 
  const [todos, setTodos] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isOpen, setIsOpen] = useState(false)
  const [editingTodo, setEditingTodo] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
 
  useEffect(() => {
    const loadTodos = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await axios.get(`${API_BASE}/todos`);
        setTodos(response.data);
      } catch (err) {
        console.error('Error loading todos:', err);
        setError(
          err.response?.data?.detail || 'Failed to load todos, is the backend running?'
        )
      } finally {
        setIsLoading(false);
      }
    };
    loadTodos();
  }, []);

  const fetchTodos = async () => {
    const response = await fetch(`${API_BASE}/todos`);
    const data = await response.json();
    console.log(data);
    setTodos(data);
  }



  const addTodo = async (newTodo) => {
    setIsSubmitting(true);
    setError(null);
    console.log('Adding todo:', newTodo);
    try {
      const response = await axios.post(`${API_BASE}/todos`, newTodo);
      setTodos([...todos, response.data]);
      setIsOpen(false);
    } catch (err) {
      console.error('Error adding todo:', err);
      setError(err.response?.data?.detail || 'Failed to add todo');
    } finally {
      setIsSubmitting(false);
    }
  }

  const updateTodo = (updated) => {
    setTodos(todos.map(t => t.id === updated.id ? updated : t))
    setEditingTodo(null)
    setIsOpen(false)
  }

  const deleteTodo = (id) => {
    setTodos(todos.filter(t => t.id !== id))
  }

  const toggleComplete = (id) => {
    setTodos(todos.map(t =>
      t.id === id ? { ...t, completed: !t.completed } : t
    ))
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 pb-24 sm:pb-20">
      <Sidebar />
      <Header />

      {/* Todo list */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Title and Filter */}
        <div className="flex justify-between items-center mb-6 sm:mb-8">
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 dark:text-gray-100 tracking-tight">
            My Tasks
          </h1>
          <FilterMenu />
        </div>

        <div className="space-y-3 sm:space-y-4">
          {todos.map(todo => (
            <TodoItem
              key={todo.id}
              todo={todo}
              onToggle={toggleComplete}
              onEdit={() => {
                setEditingTodo(todo)
                setIsOpen(true)
              }}
              onDelete={deleteTodo}
            />
          ))}

          {todos.length === 0 && (
            <div className="text-center py-16 sm:py-20">
              <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-gray-100 dark:bg-gray-800 mb-4">
                <svg className="w-8 h-8 sm:w-10 sm:h-10 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <p className="text-base sm:text-lg text-gray-500 dark:text-gray-400 font-medium">No tasks yet</p>
              <p className="text-sm sm:text-base text-gray-400 dark:text-gray-500 mt-1">Add your first task to get started!</p>
            </div>
          )}
        </div>
      </main>

      {/* Floating Action Button */}
      <AddButton onClick={() => {
        setEditingTodo(null)
        setIsOpen(true)
      }} />

      {/* Create / Edit Modal */}
      <Transition show={isOpen} as="div">
        <Dialog onClose={() => setIsOpen(false)} className="relative z-50">
          {/* Backdrop */}
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/30 dark:bg-black/50" />
          </Transition.Child>

          {/* Panel */}
          <div className="fixed inset-0 flex items-center justify-center p-4 sm:p-6">
            <Transition.Child
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="
                w-full max-w-md transform overflow-hidden rounded-2xl 
                bg-white dark:bg-gray-800 p-5 sm:p-6 text-left align-middle shadow-2xl 
                transition-all max-h-[90vh] overflow-y-auto
              ">
                <div className="flex justify-between items-center mb-5 sm:mb-6">
                  <Dialog.Title className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100">
                    {editingTodo ? 'Edit Task' : 'New Task'}
                  </Dialog.Title>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                    aria-label="Close dialog"
                  >
                    <XMarkIcon className="h-5 w-5 sm:h-6 sm:w-6" />
                  </button>
                </div>

                <TodoForm
                  initial={editingTodo}
                  onSubmit={editingTodo ? updateTodo : addTodo}
                  onCancel={() => setIsOpen(false)}
                />
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>
    </div>
  )
}
