import { useEffect, useId, useMemo, useRef } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faCircleCheck,
  faCircleInfo,
  faTriangleExclamation,
  faTrashCan,
} from '@fortawesome/free-solid-svg-icons';
import Button from './ui/Button';

const toneConfig = {
  danger: {
    icon: faTrashCan,
    iconBg: 'bg-rose-50',
    iconText: 'text-rose-600',
    confirmBtn: 'bg-rose-600 hover:bg-rose-700 focus:ring-rose-200',
  },
  warning: {
    icon: faTriangleExclamation,
    iconBg: 'bg-amber-50',
    iconText: 'text-amber-600',
    confirmBtn: 'bg-amber-500 hover:bg-amber-600 focus:ring-amber-200',
  },
  success: {
    icon: faCircleCheck,
    iconBg: 'bg-emerald-50',
    iconText: 'text-emerald-600',
    confirmBtn: 'bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-200',
  },
  info: {
    icon: faCircleInfo,
    iconBg: 'bg-sky-50',
    iconText: 'text-sky-600',
    confirmBtn: 'bg-sky-600 hover:bg-sky-700 focus:ring-sky-200',
  },
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
  const previouslyFocusedRef = useRef(null);

  const resolvedOpen = isOpen ?? open;

  const currentTone = useMemo(() => {
    return toneConfig[tone] || toneConfig.danger;
  }, [tone]);

  const resolvedIcon = icon || currentTone.icon;

  useEffect(() => {
    if (!resolvedOpen) return;

    previouslyFocusedRef.current = document.activeElement;
    document.body.style.overflow = 'hidden';

    const timer = setTimeout(() => {
      cancelButtonRef.current?.focus();
    }, 0);

    const handleEscape = (event) => {
      if (event.key === 'Escape' && !loading) {
        onClose?.();
      }
    };

    document.addEventListener('keydown', handleEscape);

    return () => {
      clearTimeout(timer);
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
      previouslyFocusedRef.current?.focus?.();
    };
  }, [resolvedOpen, loading, onClose]);

  if (!resolvedOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center px-4 py-6 sm:px-6">
      <button
        type="button"
        aria-label="Close confirmation modal"
        onClick={() => {
          if (!loading) onClose?.();
        }}
        className="absolute inset-0 bg-slate-900/45 backdrop-blur-[2px] transition"/>

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="relative z-10 w-full max-w-md overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.18)]"
      >
        <div className="p-6 sm:p-7">
          <div className="flex items-start gap-4">
            <div
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${currentTone.iconBg} ${currentTone.iconText}`}
            >
              <FontAwesomeIcon icon={resolvedIcon} className="text-lg" />
            </div>

            <div className="min-w-0 flex-1">
              <h3 id={titleId} className="text-lg font-semibold tracking-tight text-slate-900">
                {title}
              </h3>

              <div id={descriptionId} className="mt-2 space-y-2">
                <p className="text-sm leading-6 text-slate-500">{message}</p>
                {description ? (
                  <div className="text-sm leading-6 text-slate-500">{description}</div>
                ) : null}
              </div>
            </div>
          </div>

          <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button
              ref={cancelButtonRef}
              type="button"
              onClick={onClose}
              disabled={loading}
              variant="outline">
              {cancelText}
            </Button>

            <Button
              type="button"
              onClick={onConfirm}
              disabled={loading}
              variant="primary"
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Please wait...
                </span>
              ) : (
                confirmText
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ConfirmModal;