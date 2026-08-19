'use client'
import { forwardRef } from 'react';

/**
 * Shared action primitive. `danger` remains an alias for existing callers;
 * new code should use the semantic `destructive` name.
 */
const Button = forwardRef(function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled,
  loading,
  fullWidth = false,
  className = '',
  type = 'button',
  leftIcon,
  rightIcon,
  ...props
}, ref) {
  const variantStyles = {
    primary: 'bg-brand-600 text-white hover:bg-brand-700 focus:ring-brand-200',
    secondary: 'bg-surface-muted text-text-secondary hover:bg-slate-200 focus:ring-slate-200',
    danger: 'bg-danger text-white hover:bg-danger-dark focus:ring-danger-light',
    destructive: 'bg-danger text-white hover:bg-danger-dark focus:ring-danger-light',
    ghost: 'bg-transparent text-text-secondary hover:bg-surface-muted focus:ring-slate-200',
    outline: 'border border-border-strong bg-surface text-text-secondary hover:bg-surface-subtle focus:ring-brand-200',
  };

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  const base = [
    'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition focus:outline-none focus:ring-4 focus:ring-offset-0',
    sizeStyles[size] || sizeStyles.md,
    variantStyles[variant] || variantStyles.primary,
    fullWidth ? 'w-full' : '',
    disabled || loading ? 'cursor-not-allowed opacity-60' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button
      ref={ref}
      type={type}
      className={base}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? (
        <span className="inline-flex items-center gap-2">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current/30 border-t-current" aria-hidden="true" />
          <span className="sr-only">Loading</span>
          {children}
        </span>
      ) : (
        <>
          {leftIcon ? <span className="flex-shrink-0" aria-hidden="true">{leftIcon}</span> : null}
          {children}
          {rightIcon ? <span className="flex-shrink-0" aria-hidden="true">{rightIcon}</span> : null}
        </>
      )}
    </button>
  );
});

export default Button;
