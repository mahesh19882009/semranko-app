'use client'
import { useState } from 'react';

/**
 * Switch Component
 * 
 * Toggle switch component for binary choices.
 * 
 * @param {boolean} checked - Whether switch is checked
 * @param {Function} onChange - Callback when switch changes
 * @param {boolean} disabled - Whether switch is disabled
 * @param {string} label - Optional label text
 * @param {string} size - Switch size: 'sm' | 'md' | 'lg'
 * @param {string} className - Additional CSS classes
 */
function Switch({ checked = false, onChange, disabled = false, label, size = 'md', className = '' }) {
  const [internalChecked, setInternalChecked] = useState(checked);
  const isChecked = onChange ? checked : internalChecked;

  const handleChange = () => {
    if (disabled) return;
    
    if (onChange) {
      onChange(!isChecked);
    } else {
      setInternalChecked(!isChecked);
    }
  };

  const sizeStyles = {
    sm: 'h-5 w-9',
    md: 'h-6 w-11',
    lg: 'h-7 w-13',
  };

  const thumbStyles = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  const thumbTranslate = {
    sm: isChecked ? 'translate-x-4' : 'translate-x-0.5',
    md: isChecked ? 'translate-x-5' : 'translate-x-0.5',
    lg: isChecked ? 'translate-x-6' : 'translate-x-0.5',
  };

  return (
    <label className={`inline-flex items-center gap-3 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>
      <button
        type="button"
        role="switch"
        aria-checked={isChecked}
        disabled={disabled}
        onClick={handleChange}
        className={`relative inline-flex flex-shrink-0 rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
          isChecked ? 'bg-brand-600' : 'bg-slate-200'
        } ${sizeStyles[size]}`}
      >
        <span
          className={`inline-block rounded-full bg-white shadow transition-transform duration-200 ease-in-out ${thumbStyles[size]} ${thumbTranslate[size]}`}
          aria-hidden="true"
        />
      </button>
      {label && (
        <span className="text-sm font-medium text-slate-700">{label}</span>
      )}
    </label>
  );
}

export default Switch;
