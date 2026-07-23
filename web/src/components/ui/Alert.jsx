import { AlertCircle, CheckCircle2, Info, TriangleAlert } from 'lucide-react';

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
        <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${styles.icon}`} />

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
      </div>
    </div>
  );
}

export default Alert;