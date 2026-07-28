/**
 * White Label Utility
 * 
 * Utility functions for applying white-label branding to the application.
 * Handles CSS custom property updates for brand colors.
 */

/**
 * Apply white-label settings to the application
 * 
 * @param {Object} settings - White-label settings from API
 * @param {string} settings.primaryColor - Primary brand color (hex)
 * @param {string} settings.secondaryColor - Secondary brand color (hex)
 * @param {string} settings.companyName - Company name for title
 */
export function applyWhiteLabelSettings(settings) {
  if (!settings) return;

  const root = document.documentElement;

  // Apply primary color (affects brand colors throughout the app)
  if (settings.primaryColor) {
    root.style.setProperty('--color-brand-600', settings.primaryColor);
    
    // Generate color shades for the primary color
    const shades = generateColorShades(settings.primaryColor);
    Object.entries(shades).forEach(([shade, color]) => {
      root.style.setProperty(`--color-brand-${shade}`, color);
    });
  }

  // Apply secondary color (affects text colors on branded backgrounds)
  if (settings.secondaryColor) {
    root.style.setProperty('--color-brand-text', settings.secondaryColor);
  }

  // Update document title with company name
  if (settings.companyName) {
    document.title = `${settings.companyName} - RankCare`;
  }

  // Apply sidebar background color (darker version of primary or default)
  if (settings.primaryColor) {
    const sidebarBg = darkenColor(settings.primaryColor, 20);
    root.style.setProperty('--color-sidebar-bg', sidebarBg);
  }

  // Apply topbar background color
  if (settings.primaryColor) {
    const topbarBg = settings.primaryColor;
    root.style.setProperty('--color-topbar-bg', topbarBg);
  }

  // Apply sidebar active state color
  if (settings.primaryColor) {
    const sidebarActive = lightenColor(settings.primaryColor, 10);
    root.style.setProperty('--color-sidebar-active', sidebarActive);
  }

  // Apply sidebar text color
  if (settings.secondaryColor) {
    root.style.setProperty('--color-sidebar-text', settings.secondaryColor);
  }
}

/**
 * Remove white-label settings and revert to default theme
 */
export function removeWhiteLabelSettings() {
  const root = document.documentElement;

  // Remove custom properties
  const customProps = [
    '--color-brand-50',
    '--color-brand-100',
    '--color-brand-200',
    '--color-brand-300',
    '--color-brand-400',
    '--color-brand-500',
    '--color-brand-600',
    '--color-brand-700',
    '--color-brand-800',
    '--color-brand-900',
    '--color-brand-text',
    '--color-sidebar-bg',
    '--color-topbar-bg',
    '--color-sidebar-active',
    '--color-sidebar-text',
  ];

  customProps.forEach(prop => {
    root.style.removeProperty(prop);
  });

  // Reset document title
  document.title = 'RankCare';
}

/**
 * Generate color shades from a base color
 * 
 * @param {string} hexColor - Base color in hex format
 * @returns {Object} Object with color shades (50-900)
 */
function generateColorShades(hexColor) {
  const rgb = hexToRgb(hexColor);
  if (!rgb) return {};

  return {
    50: rgbToHex(lighten(rgb, 0.95)),
    100: rgbToHex(lighten(rgb, 0.9)),
    200: rgbToHex(lighten(rgb, 0.8)),
    300: rgbToHex(lighten(rgb, 0.6)),
    400: rgbToHex(lighten(rgb, 0.3)),
    500: rgbToHex(lighten(rgb, 0)),
    600: hexColor,
    700: rgbToHex(darken(rgb, 0.1)),
    800: rgbToHex(darken(rgb, 0.2)),
    900: rgbToHex(darken(rgb, 0.3)),
  };
}

/**
 * Convert hex color to RGB
 * 
 * @param {string} hex - Hex color string
 * @returns {Object|null} RGB object or null
 */
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

/**
 * Convert RGB to hex
 * 
 * @param {Object} rgb - RGB object
 * @returns {string} Hex color string
 */
function rgbToHex({ r, g, b }) {
  return `#${[r, g, b].map(x => {
    const hex = Math.round(x).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  }).join('')}`;
}

/**
 * Lighten a color by a percentage
 * 
 * @param {Object} rgb - RGB object
 * @param {number} amount - Amount to lighten (0-1)
 * @returns {Object} Lightened RGB object
 */
function lighten({ r, g, b }, amount) {
  return {
    r: r + (255 - r) * amount,
    g: g + (255 - g) * amount,
    b: b + (255 - b) * amount,
  };
}

/**
 * Darken a color by a percentage
 * 
 * @param {Object} rgb - RGB object
 * @param {number} amount - Amount to darken (0-1)
 * @returns {Object} Darkened RGB object
 */
function darken({ r, g, b }, amount) {
  return {
    r: r * (1 - amount),
    g: g * (1 - amount),
    b: b * (1 - amount),
  };
}

/**
 * Lighten a hex color by percentage
 * 
 * @param {string} hex - Hex color string
 * @param {number} percent - Percentage to lighten (0-100)
 * @returns {string} Lightened hex color
 */
function lightenColor(hex, percent) {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  const lightened = lighten(rgb, percent / 100);
  return rgbToHex(lightened);
}

/**
 * Darken a hex color by percentage
 * 
 * @param {string} hex - Hex color string
 * @param {number} percent - Percentage to darken (0-100)
 * @returns {string} Darkened hex color
 */
function darkenColor(hex, percent) {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  const darkened = darken(rgb, percent / 100);
  return rgbToHex(darkened);
}
