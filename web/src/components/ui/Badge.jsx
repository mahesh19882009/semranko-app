const toneStyles = {
  primary: 'bg-brand-50 text-brand-700 border-brand-200',
  secondary: 'bg-slate-100 text-slate-700 border-slate-200',
  success: 'bg-success-light text-success-dark border-emerald-200',
  warning: 'bg-warning-light text-warning-dark border-amber-200',
  danger: 'bg-danger-light text-danger-dark border-red-200',
  info: 'bg-info-light text-info-dark border-blue-200',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

function Badge({
  children,
  tone = 'secondary',
  size = 'md',
  className = '',
  rounded = 'rounded-full',
  as: Component = 'span',
  ...props
}) {
  const classes = [
    'inline-flex items-center font-semibold border',
    rounded,
    sizeStyles[size],
    toneStyles[tone],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Component className={classes} {...props}>
      {children}
    </Component>
  );
}

export default Badge;
