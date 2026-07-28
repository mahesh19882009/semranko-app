import { forwardRef } from 'react';

function Input({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  className = '',
  id,
  ...props
}) {
  const inputId = id || props.name;

  const wrapperClasses = [
    'flex flex-col gap-1.5',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const inputClasses = [
    'w-full rounded-xl border px-4 py-3 text-sm outline-none transition',
    'bg-white placeholder:text-slate-400',
    error
      ? 'border-danger focus:border-danger focus:ring-danger/20'
      : 'border-slate-200 focus:border-brand-600 focus:ring-brand-200',
    props.disabled && 'bg-slate-50 text-slate-500 cursor-not-allowed',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={wrapperClasses}>
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <div className="relative">
        {leftIcon && (
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
            {leftIcon}
          </span>
        )}
        <input id={inputId} className={inputClasses} {...props} />
        {rightIcon && (
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
            {rightIcon}
          </span>
        )}
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

const Textarea = forwardRef(function Textarea({
  label,
  error,
  hint,
  className = '',
  id,
  rows = 4,
  ...props
}, ref) {
  const inputId = id || props.name;

  const wrapperClasses = [
    'flex flex-col gap-1.5',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const textareaClasses = [
    'w-full rounded-xl border px-4 py-3 text-sm outline-none transition resize-y',
    'bg-white placeholder:text-slate-400',
    error
      ? 'border-danger focus:border-danger focus:ring-danger/20'
      : 'border-slate-200 focus:border-brand-600 focus:ring-brand-200',
    props.disabled && 'bg-slate-50 text-slate-500 cursor-not-allowed',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={wrapperClasses}>
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <textarea id={inputId} ref={ref} className={textareaClasses} rows={rows} {...props} />
      {error && <p className="text-xs text-danger">{error}</p>}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
});

const Select = forwardRef(function Select({
  label,
  error,
  hint,
  className = '',
  id,
  children,
  ...props
}, ref) {
  const inputId = id || props.name;

  const wrapperClasses = [
    'flex flex-col gap-1.5',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const selectClasses = [
    'w-full rounded-xl border px-4 py-3 text-sm outline-none transition appearance-none',
    'bg-white placeholder:text-slate-400',
    error
      ? 'border-danger focus:border-danger focus:ring-danger/20'
      : 'border-slate-200 focus:border-brand-600 focus:ring-brand-200',
    props.disabled && 'bg-slate-50 text-slate-500 cursor-not-allowed',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={wrapperClasses}>
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <div className="relative">
        <select id={inputId} ref={ref} className={selectClasses} {...props}>
          {children}
        </select>
        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
});

Input.Textarea = Textarea;
Input.Select = Select;

export default Input;
