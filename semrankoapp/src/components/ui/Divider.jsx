'use client'
/**
 * Divider Component
 * 
 * Visual separator component for dividing content.
 * 
 * @param {string} orientation - Divider orientation: 'horizontal' | 'vertical'
 * @param {string} variant - Divider style: 'solid' | 'dashed'
 * @param {string} label - Optional label text
 * @param {string} className - Additional CSS classes
 */
function Divider({ orientation = 'horizontal', variant = 'solid', label, className = '' }) {
  const orientationStyles = {
    horizontal: 'w-full border-t',
    vertical: 'h-full border-l',
  };

  const variantStyles = {
    solid: 'border-solid',
    dashed: 'border-dashed',
  };

  if (label) {
    return (
      <div className={`relative flex items-center ${className}`}>
        <div className={`flex-grow ${orientationStyles.horizontal} ${variantStyles[variant]} border-slate-200`} />
        <span className="mx-4 flex-shrink-0 text-sm text-slate-500">{label}</span>
        <div className={`flex-grow ${orientationStyles.horizontal} ${variantStyles[variant]} border-slate-200`} />
      </div>
    );
  }

  return (
    <div
      className={`${orientationStyles[orientation]} ${variantStyles[variant]} border-slate-200 ${className}`}
      role="separator"
      aria-orientation={orientation}
    />
  );
}

export default Divider;
