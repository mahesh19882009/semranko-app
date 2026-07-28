import React, { forwardRef } from 'react';

/**
 * Radio Component
 * 
 * Custom radio button component with label support.
 * 
 * @param {boolean} checked - Whether radio is checked
 * @param {Function} onChange - Callback when radio changes
 * @param {boolean} disabled - Whether radio is disabled
 * @param {string} label - Optional label text
 * @param {string} error - Error message to display
 * @param {string} value - Radio button value
 * @param {string} name - Radio button group name
 * @param {string} className - Additional CSS classes
 */
const Radio = forwardRef(function Radio(
  { checked = false, onChange, disabled = false, label, error, value, name, className = '', ...props },
  ref
) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label className={`inline-flex items-center gap-3 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
        <div className="relative">
          <input
            ref={ref}
            type="radio"
            checked={checked}
            onChange={(e) => onChange?.(e.target.checked)}
            disabled={disabled}
            value={value}
            name={name}
            className="sr-only"
            aria-invalid={!!error}
            {...props}
          />
          <div
            className={`h-5 w-5 rounded-full border-2 transition-colors ${
              checked
                ? 'border-brand-600'
                : 'border-slate-300 hover:border-brand-400'
            } ${disabled ? 'border-slate-200' : ''}`}
          >
            {checked && (
              <div className="flex h-full w-full items-center justify-center">
                <div className="h-2.5 w-2.5 rounded-full bg-brand-600" />
              </div>
            )}
          </div>
        </div>
        {label && <span className="text-sm font-medium text-slate-700">{label}</span>}
      </label>
      {error && <p className="text-xs text-danger" role="alert">{error}</p>}
    </div>
  );
});

/**
 * RadioGroup Component
 * 
 * Group of radio buttons with shared state.
 */
function RadioGroup({ name, value, onChange, children, className = '' }) {
  return (
    <div className={`flex flex-col gap-3 ${className}`} role="radiogroup">
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, {
            name,
            checked: child.props.value === value,
            onChange: (checked) => {
              if (checked) {
                onChange?.(child.props.value);
              }
            },
          });
        }
        return child;
      })}
    </div>
  );
}

Radio.Group = RadioGroup;

export default Radio;
