import React from 'react';

/**
 * Avatar Component
 * 
 * User avatar component with fallback initials.
 * 
 * @param {string} src - Image source URL
 * @param {string} alt - Alt text for image
 * @param {string} name - User name for initials fallback
 * @param {string} size - Avatar size: 'sm' | 'md' | 'lg' | 'xl'
 * @param {string} className - Additional CSS classes
 */
function Avatar({ src, alt, name, size = 'md', className = '' }) {
  const sizeStyles = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-12 w-12 text-base',
    xl: 'h-16 w-16 text-lg',
  };

  const getInitials = (name) => {
    if (!name) return '';
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const initials = getInitials(name);

  if (src) {
    return (
      <img
        src={src}
        alt={alt || name || 'Avatar'}
        className={`rounded-full object-cover ${sizeStyles[size]} ${className}`}
      />
    );
  }

  return (
    <div
      className={`flex items-center justify-center rounded-full bg-brand-100 text-brand-700 font-semibold ${sizeStyles[size]} ${className}`}
      aria-label={name || 'Avatar'}
    >
      {initials}
    </div>
  );
}

/**
 * AvatarGroup Component
 * 
 * Group of avatars with overlap effect.
 */
function AvatarGroup({ children, max = 3, className = '' }) {
  const avatars = React.Children.toArray(children);
  const visibleAvatars = avatars.slice(0, max);
  const remainingCount = avatars.length - max;

  return (
    <div className={`flex -space-x-2 ${className}`}>
      {visibleAvatars.map((avatar, index) => (
        <div key={index} className="ring-2 ring-white rounded-full">
          {avatar}
        </div>
      ))}
      {remainingCount > 0 && (
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-sm font-medium text-slate-600 ring-2 ring-white">
          +{remainingCount}
        </div>
      )}
    </div>
  );
}

Avatar.Group = AvatarGroup;

export default Avatar;
