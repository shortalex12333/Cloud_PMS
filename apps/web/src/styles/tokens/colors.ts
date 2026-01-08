/**
 * CelesteOS Color System
 * Source: branding/Brand/colour-system.md
 *
 * "Colour is a signal of state, not personality."
 * Color serves functional instrumentation, never emotion.
 */

// =============================================================================
// NEUTRAL FOUNDATION (80-90% of interface)
// =============================================================================

export const whites = {
  pure: '#FFFFFF',
  soft: '#FAFAFA',
  muted: '#F8F8F0',
  dim: '#F4F4F4',
} as const;

export const blacks = {
  pure: '#020202',
  deep: '#181818',
  base: '#242424',
} as const;

// Dark mode grays (for current dark UI)
export const grays = {
  50: '#FAFAFA',
  100: '#F4F4F4',
  200: '#E5E5E5',
  300: '#D4D4D4',
  400: '#A3A3A3',
  500: '#737373',
  600: '#525252',
  700: '#404040',
  800: '#262626',
  900: '#171717',
} as const;

// =============================================================================
// FUNCTIONAL ACCENT (Blue only)
// =============================================================================

export const blue = {
  primary: '#0070FF',    // Selection, focus
  secondary: '#00A4FF',  // Secondary focus states
  soft: '#BADDE9',       // Soft state indicators
} as const;

// =============================================================================
// BRAND GRADIENT (FORBIDDEN IN PRODUCT UI)
// =============================================================================

export const gradient = {
  from: '#BADDE9',
  to: '#2FB9E8',
  // RESTRICTED TO: website hero, launch materials, physical collateral
  // FORBIDDEN IN: product UI backgrounds, buttons, cards, microactions
} as const;

// =============================================================================
// RESTRICTED COLORS (Use sparingly, specific contexts only)
// =============================================================================

export const restricted = {
  // RED: Irreversible destructive actions, safety-critical alerts ONLY
  red: '#FF3B30',

  // ORANGE: Inspection warnings, time-sensitive advisories ONLY
  orange: '#FF9500',

  // YELLOW: Time-sensitive advisories ONLY
  yellow: '#FFCC00',

  // GREEN: Confirmation of committed actions ONLY
  green: '#34C759',
} as const;

// =============================================================================
// SEMANTIC ROLES
// =============================================================================

export const semantic = {
  // Selection & Focus
  selection: blue.primary,
  focus: blue.primary,

  // Text hierarchy
  textPrimary: '#F5F5F7',      // Primary content
  textSecondary: '#98989F',    // Secondary content, placeholders
  textMuted: '#86868B',        // Tertiary, less important
  textDisabled: '#636366',     // Disabled, records

  // Backgrounds (dark mode)
  bgPrimary: '#1C1C1E',        // Main background
  bgSecondary: '#2C2C2E',      // Cards, elevated surfaces
  bgTertiary: '#3D3D3F',       // Hover states, borders

  // Borders
  border: '#3D3D3F',
  borderSubtle: 'rgba(61, 61, 63, 0.3)',
} as const;

// =============================================================================
// USAGE RULES BY ROLE
// =============================================================================

export const roleColors = {
  // State display: Neutral only
  state: semantic.textSecondary,

  // READ actions: Body text color (neutral)
  readAction: semantic.textMuted,
  readActionHover: semantic.textPrimary,

  // MUTATE actions: Neutral, no blue, no red by default
  mutateAction: semantic.textDisabled,
  mutateActionHover: semantic.textSecondary,

  // Commitment: Neutral + dimming
  commitment: semantic.textPrimary,
  commitmentOverlay: 'rgba(0, 0, 0, 0.8)',

  // Records: Reduced contrast
  record: semantic.textDisabled,
} as const;

// =============================================================================
// CSS CUSTOM PROPERTIES (for use in CSS/Tailwind)
// =============================================================================

export const cssVars = {
  '--color-white': whites.pure,
  '--color-white-soft': whites.soft,
  '--color-black': blacks.pure,
  '--color-black-deep': blacks.deep,
  '--color-black-base': blacks.base,

  '--color-blue-primary': blue.primary,
  '--color-blue-secondary': blue.secondary,
  '--color-blue-soft': blue.soft,

  '--color-text-primary': semantic.textPrimary,
  '--color-text-secondary': semantic.textSecondary,
  '--color-text-muted': semantic.textMuted,
  '--color-text-disabled': semantic.textDisabled,

  '--color-bg-primary': semantic.bgPrimary,
  '--color-bg-secondary': semantic.bgSecondary,
  '--color-bg-tertiary': semantic.bgTertiary,

  '--color-border': semantic.border,
  '--color-border-subtle': semantic.borderSubtle,

  '--color-selection': semantic.selection,
  '--color-focus': semantic.focus,
} as const;
