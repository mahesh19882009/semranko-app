'use client'
import { forwardRef, useId } from 'react';

function getDescriptionIds(inputId, error, hint, describedBy) {
  return [
    describedBy,
    error ? `${inputId}-error` : null,
    hint && !error ? `${inputId}-hint` : null,
  ].filter(Boolean).join(' ') || undefined;
}

function FieldLabel({ label, inputId, required }) {
  if (!label) return null;
  return (
    <label htmlFor={inputId} className="text-sm font-medium leading-label text-text-secondary">
      {label}{required ? <span className="ml-1 text-danger" aria-hidden="true">*</span> : null}
    </label>
  );
}

function FieldMessage({ inputId, error, hint }) {
  if (error) return <p id={`${inputId}-error`} className="text-support text-danger" role="alert">{error}</p>;
  if (hint) return <p id={`${inputId}-hint`} className="text-support text-text-muted">{hint}</p>;
  return null;
}

const sharedInputClasses = (error, disabled) => [
  'w-full rounded-xl border px-4 py-3 text-sm outline-none transition',
  'bg-surface placeholder:text-slate-400',
  error
    ? 'border-danger focus:border-danger focus:ring-danger/20'
    : 'border-border focus:border-brand-600 focus:ring-brand-200',
  disabled ? 'cursor-not-allowed bg-surface-muted text-text-muted' : '',
].filter(Boolean).join(' ');

const Input = forwardRef(function Input({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  className = '',
  id,
  ...props
}, ref) {
  const generatedId = useId();
  const inputId = id || props.name || `input-${generatedId}`;
  const describedBy = getDescriptionIds(inputId, error, hint, props['aria-describedby']);

  return (
    <div className={`flex flex-col gap-1.5 ${className}`.trim()}>
      <FieldLabel label={label} inputId={inputId} required={props.required} />
      <div className="relative">
        {leftIcon ? <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">{leftIcon}</span> : null}
        <input
          {...props}
          id={inputId}
          ref={ref}
          className={sharedInputClasses(error, props.disabled)}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={describedBy}
        />
        {rightIcon ? <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">{rightIcon}</span> : null}
      </div>
      <FieldMessage inputId={inputId} error={error} hint={hint} />
    </div>
  );
});

const Textarea = forwardRef(function Textarea({ label, error, hint, className = '', id, rows = 4, ...props }, ref) {
  const generatedId = useId();
  const inputId = id || props.name || `textarea-${generatedId}`;
  const describedBy = getDescriptionIds(inputId, error, hint, props['aria-describedby']);

  return (
    <div className={`flex flex-col gap-1.5 ${className}`.trim()}>
      <FieldLabel label={label} inputId={inputId} required={props.required} />
      <textarea
        {...props}
        id={inputId}
        ref={ref}
        rows={rows}
        className={`${sharedInputClasses(error, props.disabled)} resize-y`}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={describedBy}
      />
      <FieldMessage inputId={inputId} error={error} hint={hint} />
    </div>
  );
});

const Select = forwardRef(function Select({ label, error, hint, className = '', id, children, ...props }, ref) {
  const generatedId = useId();
  const inputId = id || props.name || `select-${generatedId}`;
  const describedBy = getDescriptionIds(inputId, error, hint, props['aria-describedby']);

  return (
    <div className={`flex flex-col gap-1.5 ${className}`.trim()}>
      <FieldLabel label={label} inputId={inputId} required={props.required} />
      <div className="relative">
        <select
          {...props}
          id={inputId}
          ref={ref}
          className={`${sharedInputClasses(error, props.disabled)} appearance-none`}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={describedBy}
        >
          {children}
        </select>
        <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </span>
      </div>
      <FieldMessage inputId={inputId} error={error} hint={hint} />
    </div>
  );
});

Input.Textarea = Textarea;
Input.Select = Select;

export default Input;
