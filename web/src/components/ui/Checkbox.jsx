import { forwardRef } from 'react';

/**
 * Checkbox Component
 * 
 * Custom checkbox component with label support.
 * 
 * @param {boolean} checked - Whether checkbox is checked
 * @param {Function} onChange - Callback when checkbox changes
 * @param {boolean} disabled - Whether checkbox is disabled
 * @param {string} label - Optional label text
 * @param {string} error - Error message to display
 * @param {string} className - Additional CSS classes
 */
const Checkbox = forwardRef(function Checkbox(
  { checked = false, onChange, disabled = false, label, error, className = '', ...props },
  ref
) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label className={`inline-flex items-center gap-3 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
        <div className="relative">
          <input
            ref={ref}
            type="checkbox"
            checked={checked}
            onChange={(e) => onChange?.(e.target.checked)}
            disabled={disabled}
            className="sr-only"
            aria-invalid={!!error}
            {...props}
          />
          <div
            className={`h-5 w-5 rounded border-2 transition-colors ${
              checked
                ? 'bg-brand-600 border-brand-600'
                : 'bg-white border-slate-300 hover:border-brand-400'
            } ${disabled ? 'bg-slate-100 border-slate-200' : ''}`}
          >
            {checked && (
              <svg className="h-3 w-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </div>
        </div>
        {label && <span className="text-sm font-medium text-slate-700">{label}</span>}
      </label>
      {error && <p className="text-xs text-danger" role="alert">{error}</p>}
    </div>
  );
});

export default Checkbox;
