'use client'
import React from 'react';

/**
 * Tabs Component
 * 
 * A tab navigation component with horizontal layout.
 * Supports controlled and uncontrolled state.
 * 
 * @param {string} defaultValue - Default active tab value
 * @param {string} value - Controlled active tab value
 * @param {Function} onValueChange - Callback when tab changes
 * @param {React.ReactNode} children - Tab list items
 * @param {string} className - Additional CSS classes
 */
function Tabs({ defaultValue, value, onValueChange, children, className = '' }) {
  const [internalValue, setInternalValue] = React.useState(defaultValue || '');
  const activeValue = value !== undefined ? value : internalValue;

  const handleTabChange = (tabValue) => {
    if (onValueChange) {
      onValueChange(tabValue);
    } else {
      setInternalValue(tabValue);
    }
  };

  return (
    <div className={className}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, {
            activeValue,
            onTabChange: handleTabChange,
          });
        }
        return child;
      })}
    </div>
  );
}

/**
 * TabsList Component
 * 
 * Container for tab items.
 */
function TabsList({ children, activeValue, onTabChange, className = '' }) {
  return (
    <div
      className={`flex gap-4 border-b border-slate-200 ${className}`}
      role="tablist"
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, {
            activeValue,
            onTabChange,
          });
        }
        return child;
      })}
    </div>
  );
}

/**
 * TabsTrigger Component
 * 
 * Individual tab button.
 */
function TabsTrigger({ value, children, activeValue, onTabChange, className = '' }) {
  const isActive = activeValue === value;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      className={`px-4 py-2 font-medium transition-colors border-b-2 -mb-px ${
        isActive
          ? 'text-brand-600 border-brand-600'
          : 'text-slate-600 border-transparent hover:text-slate-900 hover:border-slate-300'
      } ${className}`}
      onClick={() => onTabChange?.(value)}
    >
      {children}
    </button>
  );
}

/**
 * TabsContent Component
 * 
 * Content panel for a tab.
 */
function TabsContent({ value, children, activeValue, className = '' }) {
  const isActive = activeValue === value;

  if (!isActive) return null;

  return (
    <div
      role="tabpanel"
      className={`py-4 ${className}`}
    >
      {children}
    </div>
  );
}

Tabs.List = TabsList;
Tabs.Trigger = TabsTrigger;
Tabs.Content = TabsContent;

export default Tabs;
