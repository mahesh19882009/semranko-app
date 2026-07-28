import { AlertCircle, CheckCircle2, Info, TriangleAlert, X } from 'lucide-react';

/**
 * Alert Component
 * 
 * A notification component for displaying important messages.
 * Supports multiple variants, optional dismissal, and custom actions.
 * 
 * @param {string} variant - Alert type: 'warning' | 'error' | 'success' | 'info' | 'plain'
 * @param {string} title - Optional alert title
 * @param {string} message - Alert message content
 * @param {React.ReactNode} children - Custom content
 * @param {React.ReactNode} action - Optional action button or content
 * @param {boolean} dismissible - Whether alert can be dismissed
 * @param {Function} onDismiss - Callback when alert is dismissed
 * @param {string} className - Additional CSS classes
 */
const VARIANT_STYLES = {
  warning: {
    wrapper: 'border-amber-200 bg-amber-50 text-amber-800',
    icon: 'text-amber-600',
  },
  error: {
    wrapper: 'border-red-200 bg-red-50 text-red-700',
    icon: 'text-red-600',
  },
  success: {
    wrapper: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    icon: 'text-emerald-600',
  },
  info: {
    wrapper: 'border-sky-200 bg-sky-50 text-sky-700',
    icon: 'text-sky-600',
  },
  plain: {
    wrapper: 'border-slate-200 bg-white text-slate-500',
    icon: 'text-slate-600',
  },
};

const VARIANT_ICONS = {
  warning: TriangleAlert,
  error: AlertCircle,
  success: CheckCircle2,
  info: Info,
  plain: Info,
};

function Alert({
  variant = 'info',
  title,
  message,
  children,
  action,
  dismissible = false,
  onDismiss,
  className = '',
}) {
  const styles = VARIANT_STYLES[variant] || VARIANT_STYLES.info;
  const Icon = VARIANT_ICONS[variant] || VARIANT_ICONS.info;

  return (
    <div
      className={`rounded-2xl border px-4 py-3 text-sm ${styles.wrapper} ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${styles.icon}`} aria-hidden="true" />

        <div className="min-w-0 flex-1">
          {title ? (
            <p className="font-semibold">
              {title}
            </p>
          ) : null}

          {message ? (
            <p className={title ? 'mt-1' : ''}>
              {message}
            </p>
          ) : null}

          {children ? (
            <div className={title || message ? 'mt-1' : ''}>
              {children}
            </div>
          ) : null}

          {action ? (
            <div className="mt-3">
              {action}
            </div>
          ) : null}
        </div>

        {dismissible && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 text-slate-400 hover:text-slate-600 transition-colors"
            aria-label="Dismiss alert"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

export default Alert;