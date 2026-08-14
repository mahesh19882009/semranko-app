/**
 * Compatibility adapter for JavaScript consumers.
 *
 * CSS custom properties in app/globals.css are the canonical token source.
 * Keep this tiny object so a future runtime consumer can use a token without
 * reintroducing a second set of literal colour values.
 */
export const cssVar = (name) => `var(--${name})`;

export const theme = Object.freeze({
  brand: Object.freeze({
    50: cssVar('color-brand-50'), 100: cssVar('color-brand-100'), 200: cssVar('color-brand-200'),
    300: cssVar('color-brand-300'), 400: cssVar('color-brand-400'), 500: cssVar('color-brand-500'),
    600: cssVar('color-brand-600'), 700: cssVar('color-brand-700'), 800: cssVar('color-brand-800'),
    900: cssVar('color-brand-900'), accent: cssVar('color-brand-accent'),
  }),
  colors: Object.freeze({
    success: cssVar('color-success'), warning: cssVar('color-warning'), danger: cssVar('color-danger'),
    info: cssVar('color-info'), active: cssVar('color-active'), inactive: cssVar('color-inactive'),
    deleted: cssVar('color-deleted'), locked: cssVar('color-locked'),
  }),
  text: Object.freeze({ primary: cssVar('color-text-primary'), secondary: cssVar('color-text-secondary'), muted: cssVar('color-text-muted') }),
  surface: Object.freeze({ default: cssVar('color-surface'), subtle: cssVar('color-surface-subtle'), muted: cssVar('color-surface-muted') }),
  border: Object.freeze({ default: cssVar('color-border'), strong: cssVar('color-border-strong') }),
  shadows: Object.freeze({ card: cssVar('shadow-card'), soft: cssVar('shadow-soft'), elevated: cssVar('shadow-elevated') }),
  font: Object.freeze({ sans: cssVar('font-sans'), mono: cssVar('font-mono') }),
});

export default theme;
