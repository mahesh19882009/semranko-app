function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled,
  loading,
  type = 'button',
  ...props
}) {
  const variantStyles = {
    primary: 'bg-brand-600 text-white hover:bg-brand-700 focus:ring-brand-200',
    secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200 focus:ring-slate-200',
    danger: 'bg-danger text-white hover:bg-red-600 focus:ring-red-200',
    ghost: 'bg-transparent text-slate-700 hover:bg-slate-100 focus:ring-slate-200',
    outline: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus:ring-slate-200',
  };

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  const base = [
    'inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition focus:outline-none focus:ring-4 focus:ring-offset-0',
    sizeStyles[size],
    variantStyles[variant],
    disabled || loading ? 'opacity-60 cursor-not-allowed' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button type={type} className={base} disabled={disabled || loading} {...props}>
      {loading && (
        <span className="inline-flex items-center gap-2">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current/30 border-t-current" />
          {children}
        </span>
      )}
      {!loading && children}
    </button>
  );
}

export default Button;
