import { Dialog, Transition } from '@headlessui/react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'

export default function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  variant = 'danger', // 'danger' | 'warning' | 'info'
}) {
  const variantStyles = {
    danger: {
      icon: 'bg-red-100 dark:bg-red-900/30',
      iconColor: 'text-red-600 dark:text-red-400',
      button: 'bg-red-600 hover:bg-red-700 focus:ring-red-500',
    },
    warning: {
      icon: 'bg-amber-100 dark:bg-amber-900/30',
      iconColor: 'text-amber-600 dark:text-amber-400',
      button: 'bg-amber-600 hover:bg-amber-700 focus:ring-amber-500',
    },
    info: {
      icon: 'bg-terracotta-100 dark:bg-blue-900/30',
      iconColor: 'text-terracotta-600 dark:text-blue-400',
      button: 'bg-terracotta-500 hover:bg-terracotta-600 focus:ring-terracotta-500',
    },
  }

  const styles = variantStyles[variant] || variantStyles.danger

  return (
    <Transition show={isOpen} as="div">
      <Dialog onClose={onClose} className="relative z-50">
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
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="w-full max-w-sm transform overflow-hidden rounded-2xl bg-card-bg dark:bg-gray-800 p-6 text-left align-middle shadow-2xl transition-all">
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className={`flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-full ${styles.icon}`}>
                  <ExclamationTriangleIcon className={`w-6 h-6 ${styles.iconColor}`} />
                </div>

                {/* Content */}
                <div className="flex-1">
                  <Dialog.Title className="text-lg font-semibold text-text-primary dark:text-gray-100">
                    {title}
                  </Dialog.Title>
                  <p className="mt-2 text-sm text-text-secondary dark:text-gray-400">
                    {message}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="
                    px-4 py-2 text-sm font-medium text-text-secondary dark:text-gray-300
                    hover:bg-warm-beige dark:hover:bg-gray-700 rounded-lg
                    transition-colors duration-200
                    focus:outline-none focus:ring-2 focus:ring-terracotta-500 focus:ring-offset-2
                    dark:focus:ring-offset-gray-800
                  "
                >
                  {cancelLabel}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onConfirm()
                    onClose()
                  }}
                  className={`
                    px-4 py-2 text-sm font-medium text-white rounded-lg
                    transition-colors duration-200
                    focus:outline-none focus:ring-2 focus:ring-offset-2
                    dark:focus:ring-offset-gray-800
                    ${styles.button}
                  `}
                >
                  {confirmLabel}
                </button>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  )
}
