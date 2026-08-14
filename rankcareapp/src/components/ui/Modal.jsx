'use client'
import { useId, useRef } from 'react';
import { X } from 'lucide-react';
import Dialog from './Dialog';
import IconButton from './IconButton';

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
  const titleId = useId();
  const closeButtonRef = useRef(null);
  const sizeStyles = {
    sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl', full: 'max-w-6xl',
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      labelledBy={title ? titleId : undefined}
      initialFocusRef={showCloseButton ? closeButtonRef : undefined}
      className={`flex max-h-[calc(100vh-2rem)] w-full flex-col overflow-hidden rounded-xl bg-surface shadow-elevated ${sizeStyles[size] || sizeStyles.md} ${className}`}
    >
      {title ? (
        <div className="flex shrink-0 items-center justify-between border-b border-border px-6 py-5">
          <h2 id={titleId} className="text-xl font-semibold text-text-primary">{title}</h2>
          {showCloseButton ? <IconButton ref={closeButtonRef} label="Close dialog" variant="ghost" size="sm" onClick={onClose}><X className="h-5 w-5" /></IconButton> : null}
        </div>
      ) : null}
      <div className="flex-1 overflow-y-auto px-6 py-6">{children}</div>
      {footer ? <div className="flex shrink-0 items-center justify-end gap-3 border-t border-border px-6 py-4">{footer}</div> : null}
    </Dialog>
  );
}

function ModalHeader({ title, onClose, showCloseButton = true, className = '' }) {
  return (
    <div className={`flex items-center justify-between border-b border-border px-6 py-5 ${className}`}>
      <h2 className="text-xl font-semibold text-text-primary">{title}</h2>
      {showCloseButton ? <IconButton label="Close dialog" variant="ghost" size="sm" onClick={onClose}><X className="h-5 w-5" /></IconButton> : null}
    </div>
  );
}

function ModalBody({ children, className = '' }) { return <div className={`px-6 py-6 ${className}`}>{children}</div>; }
function ModalFooter({ children, className = '' }) { return <div className={`flex items-center justify-end gap-3 border-t border-border px-6 py-4 ${className}`}>{children}</div>; }

Modal.Header = ModalHeader;
Modal.Body = ModalBody;
Modal.Footer = ModalFooter;

export default Modal;
