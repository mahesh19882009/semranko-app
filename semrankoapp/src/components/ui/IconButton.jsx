'use client'
import { forwardRef } from 'react';
import Button from './Button';

/** A labelled icon-only action for new shared UI. */
const IconButton = forwardRef(function IconButton({ label, children, className = '', size = 'md', ...props }, ref) {
  const sizeClasses = {
    sm: 'h-8 w-8 !p-0',
    md: 'h-10 w-10 !p-0',
    lg: 'h-12 w-12 !p-0',
  };

  return (
    <Button
      ref={ref}
      {...props}
      size={size}
      className={`${sizeClasses[size] || sizeClasses.md} ${className}`.trim()}
      aria-label={label}
      title={props.title || label}
    >
      <span aria-hidden="true" className="inline-flex">{children}</span>
    </Button>
  );
});

export default IconButton;
