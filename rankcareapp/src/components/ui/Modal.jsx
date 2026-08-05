'use client'
import { useEffect } from 'react';
import { X } from 'lucide-react';

/**
 * Modal Component
 * 
 * A dialog component with header, body, footer, and backdrop.
 * Supports keyboard navigation (ESC to close) and click outside to close.
 * 
 * @param {boolean} open - Whether modal is open
 * @param {Function} onClose - Callback when modal is closed
 * @param {string} title - Modal title
 * @param {React.ReactNode} children - Modal content
 * @param {React.ReactNode} footer - Modal footer content
 * @param {string} size - Modal size: 'sm' | 'md' | 'lg' | 'xl' | 'full'
 * @param {boolean} showCloseButton - Whether to show close button in header
 * @param {string} className - Additional CSS classes
 */
function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  showCloseButton = true,
  className = '',
}) {
  const sizeStyles = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-6xl',
  };

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };

    if (open) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [open, onClose]);

  if (!open) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
    >
      <div
        className={`relative w-full ${sizeStyles[size]} rounded-xl bg-white shadow-2xl ${className}`}
        role="document"
      >
        {title && (
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
            <h2 id="modal-title" className="text-xl font-semibold text-slate-900">
              {title}
            </h2>
            {showCloseButton && (
              <button
                onClick={onClose}
                className="flex-shrink-0 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                aria-label="Close modal"
              >
                <X className="h-5 w-5" />
              </button>
            )}
          </div>
        )}

        <div className="px-6 py-6">
          {children}
        </div>

        {footer && (
          <div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ModalHeader Component
 * 
 * Header section of modal with title and close button.
 */
function ModalHeader({ title, onClose, showCloseButton = true, className = '' }) {
  return (
    <div className={`flex items-center justify-between border-b border-slate-200 px-6 py-5 ${className}`}>
      <h2 id="modal-title" className="text-xl font-semibold text-slate-900">
        {title}
      </h2>
      {showCloseButton && (
        <button
          onClick={onClose}
          className="flex-shrink-0 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          aria-label="Close modal"
        >
          <X className="h-5 w-5" />
        </button>
      )}
    </div>
  );
}

/**
 * ModalBody Component
 * 
 * Main content section of modal.
 */
function ModalBody({ children, className = '' }) {
  return (
    <div className={`px-6 py-6 ${className}`}>
      {children}
    </div>
  );
}

/**
 * ModalFooter Component
 * 
 * Footer section of modal for actions.
 */
function ModalFooter({ children, className = '' }) {
  return (
    <div className={`flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4 ${className}`}>
      {children}
    </div>
  );
}

Modal.Header = ModalHeader;
Modal.Body = ModalBody;
Modal.Footer = ModalFooter;

export default Modal;
