/**
 * Theme Configuration
 * Centralized theme tokens for JavaScript usage
 * These values should match the CSS custom properties in index.css
 */

export const theme = {
  // Brand colors - can be overridden for white-label
  brand: {
    50: '#ecfeff',
    100: '#cffafe',
    200: '#a5f3fc',
    300: '#67e8f9',
    400: '#22d3ee',
    500: '#06b6d4',
    600: '#0891b2',
    700: '#0e7490',
    800: '#155e75',
    900: '#164e63',
  },

  // Semantic colors
  colors: {
    success: '#10b981',
    successLight: '#d1fae5',
    successDark: '#065f46',
    warning: '#f59e0b',
    warningLight: '#fef3c7',
    warningDark: '#92400e',
    danger: '#ef4444',
    dangerLight: '#fee2e2',
    dangerDark: '#991b1b',
    info: '#3b82f6',
    infoLight: '#dbeafe',
    infoDark: '#1e40af',
  },

  // Neutral colors
  slate: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
  },

  // Sidebar & TopBar colors
  sidebar: {
    bg: '#0f172a',
    text: '#f8fafc',
    hover: '#1e293b',
    active: '#0891b2',
  },
  topbar: {
    bg: '#ffffff',
  },

  // Shadows
  shadows: {
    soft: '0 10px 30px rgba(2, 8, 23, 0.08)',
    card: '0 1px 3px rgba(2, 8, 23, 0.08), 0 1px 2px rgba(2, 8, 23, 0.04)',
    elevated: '0 20px 40px rgba(2, 8, 23, 0.12)',
    sm: '0 1px 2px rgba(2, 8, 23, 0.05)',
    md: '0 4px 6px rgba(2, 8, 23, 0.07)',
    lg: '0 10px 15px rgba(2, 8, 23, 0.1)',
  },

  // Fonts
  fonts: {
    sans: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
  },

  // Border radius
  radius: {
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    '2xl': '2rem',
    '3xl': '2.5rem',
    full: '9999px',
  },

  // Spacing scale
  spacing: {
    0: 0,
    1: '0.25rem',
    2: '0.5rem',
    3: '0.75rem',
    4: '1rem',
    5: '1.25rem',
    6: '1.5rem',
    8: '2rem',
    10: '2.5rem',
    12: '3rem',
    16: '4rem',
    20: '5rem',
    24: '6rem',
  },

  // Typography scale
  fontSize: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
    '5xl': '3rem',
  },

  // Font weights
  fontWeight: {
    light: 300,
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  // Line heights
  lineHeight: {
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.625,
  },

  // Transitions
  transition: {
    fast: '150ms',
    normal: '200ms',
    slow: '300ms',
  },
  ease: {
    default: 'cubic-bezier(0.4, 0, 0.2, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },

  // Z-index scale
  zIndex: {
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modalBackdrop: 1040,
    modal: 1050,
    popover: 1060,
    tooltip: 1070,
  },
};

export default theme;
