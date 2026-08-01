'use client'
/**
 * Badge Component
 * 
 * A small label component for displaying status, categories, or tags.
 * Supports multiple tones, sizes, and optional icons.
 * 
 * @param {React.ReactNode} children - Badge content
 * @param {string} tone - Badge color tone: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info'
 * @param {string} size - Badge size: 'sm' | 'md' | 'lg'
 * @param {string} rounded - Border radius: 'rounded-full' | 'rounded-md' | 'rounded-lg'
 * @param {React.ReactNode} icon - Optional icon to display
 * @param {string} className - Additional CSS classes
 * @param {React.ElementType} as - HTML element to render
 */
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
  rounded = 'rounded-full',
  icon,
  className = '',
  as: Component = 'span',
  ...props
}) {
  const classes = [
    'inline-flex items-center gap-1.5 font-semibold border',
    rounded,
    sizeStyles[size],
    toneStyles[tone],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Component className={classes} {...props}>
      {icon && <span className="flex-shrink-0" aria-hidden="true">{icon}</span>}
      {children}
    </Component>
  );
}

export default Badge;
