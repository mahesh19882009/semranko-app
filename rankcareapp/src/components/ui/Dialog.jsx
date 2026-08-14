'use client'
import { useEffect, useRef } from 'react';

const focusableSelector = [
  'a[href]', 'button:not([disabled])', 'textarea:not([disabled])',
  'input:not([disabled])', 'select:not([disabled])', '[tabindex]:not([tabindex="-1"])',
].join(',');

/**
 * Shared accessible dialog behavior. Presentation remains with Modal and
 * ConfirmModal so their current content and calling contracts stay intact.
 */
function Dialog({
  open,
  onClose,
  children,
  labelledBy,
  describedBy,
  initialFocusRef,
  closeOnEscape = true,
  closeOnBackdrop = true,
  className = '',
}) {
  const contentRef = useRef(null);
  const previouslyFocusedRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    previouslyFocusedRef.current = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const focusTimer = window.setTimeout(() => {
      const target = initialFocusRef?.current
        || contentRef.current?.querySelector('[data-dialog-initial-focus]')
        || contentRef.current?.querySelector(focusableSelector)
        || contentRef.current;
      target?.focus?.();
    }, 0);

    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && closeOnEscape) {
        event.preventDefault();
        onClose?.();
        return;
      }
      if (event.key !== 'Tab' || !contentRef.current) return;

      const focusable = Array.from(contentRef.current.querySelectorAll(focusableSelector));
      if (focusable.length === 0) {
        event.preventDefault();
        contentRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      if (previouslyFocusedRef.current?.isConnected) {
        previouslyFocusedRef.current.focus?.();
      }
    };
  }, [open, onClose, closeOnEscape, initialFocusRef]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div
        className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
        aria-hidden="true"
        onMouseDown={closeOnBackdrop ? onClose : undefined}
      />
      <div
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
        className={`relative z-10 ${className}`}
      >
        {children}
      </div>
    </div>
  );
}

export default Dialog;
