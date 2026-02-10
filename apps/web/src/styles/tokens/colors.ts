/**
 * CelesteOS Maritime Color System
 * Source: BRANDING_V3
 *
 * "Colour is a signal of state, not personality."
 * Maritime authority through restraint — not cheap blue saturation.
 */

// =============================================================================
// NEUTRAL FOUNDATION (80-90% of interface)
// =============================================================================

export const whites = {
  pure: '#EFEFF1',      // Primary light background
  soft: '#F5F5F7',      // Elevated light surfaces
  muted: '#E8E8EA',     // Secondary surfaces
  dim: '#DCDCDE',       // Tertiary/borders
} as const;

export const blacks = {
  pure: '#0A0A0A',      // Primary dark background
  deep: '#0B0D0F',      // Title text on light
  base: '#1A1D1F',      // Body text on light
} as const;

// Dark mode surface grays (based on #0A0A0A foundation)
export const grays = {
  50: '#EFEFF1',        // Inverted for dark mode text
  100: '#DADDE0',       // Primary text dark mode
  200: '#C0C4C8',       //
  300: '#A0A4A8',       // Muted text
  400: '#8A9196',       // Secondary text (shared)
  500: '#6A6E72',       // Muted dark
  600: '#4A4E52',       // Disabled
  700: '#2A2A2A',       // Borders dark
  800: '#1A1A1A',       // Tertiary surface
  900: '#121212',       // Secondary surface
} as const;

// =============================================================================
// FUNCTIONAL ACCENT (Maritime Teal - NOT cheap blue)
// =============================================================================

export const accent = {
  primary: '#3A7C9D',     // Selection, focus, interactive
  hover: '#327189',       // Hover state
  soft: 'rgba(58, 124, 157, 0.15)',  // Soft backgrounds
} as const;

// Legacy blue export for compatibility (maps to new accent)
export const blue = {
  primary: '#3A7C9D',
  secondary: '#327189',
  soft: 'rgba(58, 124, 157, 0.15)',
} as const;

// =============================================================================
// BRAND GRADIENT (FORBIDDEN IN PRODUCT UI)
// =============================================================================

export const gradient = {
  from: '#3A7C9D',
  to: '#2A5C7D',
  // RESTRICTED TO: website hero, launch materials, physical collateral
  // FORBIDDEN IN: product UI backgrounds, buttons, cards, microactions
} as const;

// =============================================================================
// RESTRICTED COLORS (Use sparingly, specific contexts only)
// Muted, dignified tones — not screaming SaaS colors
// =============================================================================

export const restricted = {
  // WARNING/DESTRUCTIVE: Dignified muted red for irreversible actions
  red: '#9D3A3A',

  // ORANGE: Muted inspection warnings
  orange: '#9D6B3A',

  // YELLOW: Time-sensitive advisories
  yellow: '#9D8A3A',

  // GREEN: Confirmation of committed actions ONLY
  green: '#3A9D5C',
} as const;

// =============================================================================
// SEMANTIC ROLES
// =============================================================================

export const semantic = {
  // Selection & Focus
  selection: accent.primary,
  focus: accent.primary,

  // Text hierarchy - DARK MODE (primary)
  textTitle: '#EFEFF1',         // Titles, headings
  textPrimary: '#DADDE0',       // Primary content
  textSecondary: '#8A9196',     // Secondary content, placeholders
  textMuted: '#6A6E72',         // Tertiary, less important
  textDisabled: '#4A4E52',      // Disabled, records

  // Text hierarchy - LIGHT MODE
  textTitleLight: '#0B0D0F',
  textPrimaryLight: '#1A1D1F',
  textSecondaryLight: '#8A9196',
  textMutedLight: '#A0A4A8',
  textDisabledLight: '#C0C4C8',

  // Backgrounds - DARK MODE (primary)
  bgPrimary: '#0A0A0A',         // Main background
  bgSecondary: '#121212',       // Cards, elevated surfaces
  bgTertiary: '#1A1A1A',        // Hover states

  // Backgrounds - LIGHT MODE
  bgPrimaryLight: '#EFEFF1',
  bgSecondaryLight: '#E5E5E7',
  bgTertiaryLight: '#DCDCDE',

  // Borders
  border: '#2A2A2A',
  borderSubtle: 'rgba(255, 255, 255, 0.06)',
  borderLight: '#C8C8CA',
  borderSubtleLight: 'rgba(0, 0, 0, 0.06)',
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

  // MUTATE actions: Neutral, no accent, no red by default
  mutateAction: semantic.textDisabled,
  mutateActionHover: semantic.textSecondary,

  // Commitment: Neutral + dimming
  commitment: semantic.textPrimary,
  commitmentOverlay: 'rgba(0, 0, 0, 0.85)',

  // Records: Reduced contrast
  record: semantic.textDisabled,
} as const;

// =============================================================================
// BUTTON COLORS (per brand spec)
// =============================================================================

export const button = {
  default: {
    bg: 'transparent',
    text: semantic.textSecondary,
    border: semantic.border,
    hoverBg: 'rgba(255, 255, 255, 0.05)',
    hoverText: semantic.textPrimary,
  },
  accent: {
    bg: accent.primary,
    text: '#EFEFF1',
    border: accent.primary,
    hoverBg: accent.hover,
    hoverText: '#EFEFF1',
  },
  warning: {
    bg: 'transparent',
    text: restricted.red,
    border: restricted.red,
    hoverBg: 'rgba(157, 58, 58, 0.1)',
    hoverText: restricted.red,
  },
} as const;

// =============================================================================
// CSS CUSTOM PROPERTIES (for use in CSS/Tailwind)
// =============================================================================

export const cssVars = {
  // Whites
  '--color-white': whites.pure,
  '--color-white-soft': whites.soft,

  // Blacks
  '--color-black': blacks.pure,
  '--color-black-deep': blacks.deep,
  '--color-black-base': blacks.base,

  // Accent (maritime teal)
  '--color-accent': accent.primary,
  '--color-accent-hover': accent.hover,
  '--color-accent-soft': accent.soft,

  // Text
  '--color-text-title': semantic.textTitle,
  '--color-text-primary': semantic.textPrimary,
  '--color-text-secondary': semantic.textSecondary,
  '--color-text-muted': semantic.textMuted,
  '--color-text-disabled': semantic.textDisabled,

  // Backgrounds
  '--color-bg-primary': semantic.bgPrimary,
  '--color-bg-secondary': semantic.bgSecondary,
  '--color-bg-tertiary': semantic.bgTertiary,

  // Borders
  '--color-border': semantic.border,
  '--color-border-subtle': semantic.borderSubtle,

  // Interactive
  '--color-selection': semantic.selection,
  '--color-focus': semantic.focus,

  // Restricted
  '--color-warning': restricted.red,
  '--color-success': restricted.green,
} as const;
