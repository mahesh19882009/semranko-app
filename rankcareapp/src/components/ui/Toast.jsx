'use client'
import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { CheckCircle2, Info, TriangleAlert, X, XCircle } from 'lucide-react';

const ToastContext = createContext(null);

const TOAST_LIMIT = 3;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, variant = 'info', duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => {
      const next = [...prev, { id, message, variant, duration }];
      if (next.length > TOAST_LIMIT) {
        return next.slice(next.length - TOAST_LIMIT);
      }
      return next;
    });
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={() => removeToast(toast.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}

const VARIANT_STYLES = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  error: 'border-red-200 bg-red-50 text-red-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  info: 'border-sky-200 bg-sky-50 text-sky-800',
};

const VARIANT_ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: TriangleAlert,
  info: Info,
};

function ToastItem({ toast, onDismiss }) {
  const { message, variant } = toast;
  const style = VARIANT_STYLES[variant] || VARIANT_STYLES.info;
  const Icon = VARIANT_ICONS[variant] || VARIANT_ICONS.info;

  return (
    <div
      className={`pointer-events-auto flex items-center gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg ${style}`}
      role="status"
      aria-live="polite"
    >
      <span className="flex h-5 w-5 shrink-0 items-center justify-center" aria-hidden="true">
        <Icon className="h-4 w-4" strokeWidth={2.25} />
      </span>
      <p className="flex-1 min-w-0">{message}</p>
      <button
        onClick={onDismiss}
        className="flex-shrink-0 rounded-lg p-1 opacity-70 hover:opacity-100 transition-opacity"
        aria-label="Dismiss notification"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
