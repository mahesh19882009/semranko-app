'use client'
import { createElement, isValidElement, useId, useMemo, useRef } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { CheckCircle2, Info, Trash2, TriangleAlert } from 'lucide-react';
import Dialog from './ui/Dialog';
import Button from './ui/Button';

const toneConfig = {
  danger: { Icon: Trash2, iconBg: 'bg-danger-light', iconText: 'text-danger-dark' },
  warning: { Icon: TriangleAlert, iconBg: 'bg-warning-light', iconText: 'text-warning-dark' },
  success: { Icon: CheckCircle2, iconBg: 'bg-success-light', iconText: 'text-success-dark' },
  info: { Icon: Info, iconBg: 'bg-info-light', iconText: 'text-info-dark' },
};

function ConfirmModal({
  open,
  isOpen,
  title = 'Confirm action',
  message = 'Are you sure you want to continue?',
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  tone = 'danger',
  icon,
  loading = false,
  onConfirm,
  onClose,
}) {
  const titleId = useId();
  const descriptionId = useId();
  const cancelButtonRef = useRef(null);
  const resolvedOpen = isOpen ?? open;
  const currentTone = useMemo(() => toneConfig[tone] || toneConfig.danger, [tone]);
  const iconContent = icon
    ? (isValidElement(icon)
      ? icon
      : typeof icon === 'function'
        ? createElement(icon, { className: 'h-5 w-5', 'aria-hidden': true })
        : <FontAwesomeIcon icon={icon} aria-hidden="true" />)
    : <currentTone.Icon className="h-5 w-5" aria-hidden="true" />;
  const safeClose = () => { if (!loading) onClose?.(); };

  return (
    <Dialog
      open={resolvedOpen}
      onClose={safeClose}
      labelledBy={titleId}
      describedBy={descriptionId}
      initialFocusRef={cancelButtonRef}
      closeOnEscape={!loading}
      closeOnBackdrop={!loading}
      className="w-full max-w-md overflow-hidden rounded-[28px] border border-border bg-surface shadow-elevated"
    >
      <div className="p-6 sm:p-7">
        <div className="flex items-start gap-4">
          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${currentTone.iconBg} ${currentTone.iconText}`}>
            {iconContent}
          </div>
          <div className="min-w-0 flex-1">
            <h3 id={titleId} className="text-lg font-semibold tracking-tight text-text-primary">{title}</h3>
            <div id={descriptionId} className="mt-2 space-y-2">
              <p className="text-sm leading-6 text-text-muted">{message}</p>
              {description ? <div className="text-sm leading-6 text-text-muted">{description}</div> : null}
            </div>
          </div>
        </div>
        <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button ref={cancelButtonRef} type="button" onClick={safeClose} disabled={loading} variant="outline">{cancelText}</Button>
          <Button type="button" onClick={onConfirm} disabled={loading} loading={loading} variant="primary">{confirmText}</Button>
        </div>
      </div>
    </Dialog>
  );
}

export default ConfirmModal;
