/**
 * Progress Component
 * 
 * Progress bar component for showing loading states or completion percentages.
 * 
 * @param {number} value - Progress value (0-100)
 * @param {string} size - Progress bar size: 'sm' | 'md' | 'lg'
 * @param {string} variant - Color variant: 'primary' | 'success' | 'warning' | 'danger'
 * @param {boolean} showLabel - Whether to show percentage label
 * @param {string} className - Additional CSS classes
 */
function Progress({ value = 0, size = 'md', variant = 'primary', showLabel = false, className = '' }) {
  const sizeStyles = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  const variantStyles = {
    primary: 'bg-brand-600',
    success: 'bg-success',
    warning: 'bg-warning',
    danger: 'bg-danger',
  };

  const clampedValue = Math.min(100, Math.max(0, value));

  return (
    <div className={className}>
      {showLabel && (
        <div className="mb-2 flex justify-between text-sm">
          <span className="text-slate-600">Progress</span>
          <span className="font-medium text-slate-900">{Math.round(clampedValue)}%</span>
        </div>
      )}
      <div className={`w-full rounded-full bg-slate-200 ${sizeStyles[size]}`}>
        <div
          className={`h-full rounded-full transition-all duration-300 ease-out ${variantStyles[variant]}`}
          style={{ width: `${clampedValue}%` }}
          role="progressbar"
          aria-valuenow={clampedValue}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}

/**
 * Spinner Component
 * 
 * Loading spinner for indicating loading states.
 * 
 * @param {string} size - Spinner size: 'sm' | 'md' | 'lg'
 * @param {string} className - Additional CSS classes
 */
function Spinner({ size = 'md', className = '' }) {
  const sizeStyles = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  };

  return (
    <div
      className={`animate-spin rounded-full border-2 border-slate-200 border-t-brand-600 ${sizeStyles[size]} ${className}`}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}

Progress.Spinner = Spinner;

export default Progress;
