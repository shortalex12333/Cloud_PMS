/**
 * CelesteOS Design Tokens
 * Maritime-inspired design system for professional UX
 * Source: BRANDING_V3
 *
 * Principles:
 * - Colour is a signal of state, not personality
 * - Precision over decoration
 * - Subtle over saturated
 * - Typography as primary hierarchy
 * - Night-first design for maritime operations
 */

// ============================================================================
// RADIUS - Consistent, precise corners (not "pill" everything)
// ============================================================================

export const radius = {
  /** Container/Cards - 12px */
  container: '12px',
  /** Cards, modals - 12px */
  card: '12px',
  /** Buttons - 8px */
  button: '8px',
  /** Inputs, selects - 8px */
  input: '8px',
  /** Badges, chips - 6px */
  badge: '6px',
  /** Small elements - 4px */
  small: '4px',
  /** Full circle (icons only) */
  full: '9999px',
} as const;

// ============================================================================
// SPACING - 8px grid system
// ============================================================================

export const spacing = {
  0: '0px',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
} as const;

// ============================================================================
// TYPOGRAPHY - SF Pro inspired sizing
// ============================================================================

export const typography = {
  // Display
  display: {
    size: '32px',
    lineHeight: '40px',
    weight: 700,
    letterSpacing: '-0.02em',
  },
  // Large title
  title1: {
    size: '28px',
    lineHeight: '34px',
    weight: 700,
    letterSpacing: '-0.015em',
  },
  // Title
  title2: {
    size: '22px',
    lineHeight: '28px',
    weight: 600,
    letterSpacing: '-0.01em',
  },
  // Section header
  title3: {
    size: '20px',
    lineHeight: '24px',
    weight: 600,
    letterSpacing: '-0.01em',
  },
  // Headline
  headline: {
    size: '17px',
    lineHeight: '22px',
    weight: 600,
    letterSpacing: '-0.005em',
  },
  // Body
  body: {
    size: '17px',
    lineHeight: '22px',
    weight: 400,
    letterSpacing: '0',
  },
  // Callout
  callout: {
    size: '16px',
    lineHeight: '21px',
    weight: 400,
    letterSpacing: '0',
  },
  // Subhead
  subhead: {
    size: '15px',
    lineHeight: '20px',
    weight: 400,
    letterSpacing: '0',
  },
  // Footnote
  footnote: {
    size: '13px',
    lineHeight: '18px',
    weight: 400,
    letterSpacing: '0',
  },
  // Caption 1
  caption1: {
    size: '12px',
    lineHeight: '16px',
    weight: 400,
    letterSpacing: '0',
  },
  // Caption 2
  caption2: {
    size: '11px',
    lineHeight: '13px',
    weight: 400,
    letterSpacing: '0.01em',
  },
} as const;

// ============================================================================
// COLORS - Maritime palette (muted, authoritative)
// Source: BRANDING_V3
// ============================================================================

export const colors = {
  // Brand backgrounds
  background: {
    dark: '#0A0A0A',
    light: '#EFEFF1',
  },
  // Text colors
  text: {
    title: { dark: '#EFEFF1', light: '#0B0D0F' },
    primary: { dark: '#DADDE0', light: '#1A1D1F' },
    secondary: '#8A9196',  // Shared
  },
  // Maritime accent (NOT cheap blue)
  accent: {
    DEFAULT: '#3A7C9D',
    hover: '#327189',
    soft: 'rgba(58, 124, 157, 0.15)',
  },
  // Restricted colors (muted, dignified)
  warning: {
    DEFAULT: '#9D3A3A',
    soft: 'rgba(157, 58, 58, 0.12)',
  },
  success: {
    DEFAULT: '#3A9D5C',
    soft: 'rgba(58, 157, 92, 0.12)',
  },
  caution: {
    DEFAULT: '#9D6B3A',
    soft: 'rgba(157, 107, 58, 0.12)',
  },
  info: {
    DEFAULT: '#9D8A3A',
    soft: 'rgba(157, 138, 58, 0.12)',
  },
  // Neutral grays (based on #0A0A0A foundation)
  gray: {
    50: '#EFEFF1',
    100: '#DADDE0',
    200: '#C0C4C8',
    300: '#A0A4A8',
    400: '#8A9196',
    500: '#6A6E72',
    600: '#4A4E52',
    700: '#2A2A2A',
    800: '#1A1A1A',
    900: '#121212',
    950: '#0A0A0A',
  },
} as const;

// ============================================================================
// SHADOWS - Subtle, multi-layer (Apple style)
// ============================================================================

export const shadows = {
  /** No shadow */
  none: 'none',
  /** Subtle elevation - buttons, inputs */
  xs: '0 1px 2px rgba(0, 0, 0, 0.05)',
  /** Low elevation - cards, dropdowns */
  sm: '0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04)',
  /** Medium elevation - floating cards, popovers */
  md: '0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
  /** High elevation - modals, spotlight */
  lg: '0 8px 24px rgba(0, 0, 0, 0.12), 0 4px 8px rgba(0, 0, 0, 0.06)',
  /** Highest elevation - active modals */
  xl: '0 16px 48px rgba(0, 0, 0, 0.16), 0 8px 16px rgba(0, 0, 0, 0.08)',
} as const;

// ============================================================================
// TRANSITIONS - Smooth, natural
// ============================================================================

export const transitions = {
  /** Fast micro-interactions */
  fast: '120ms ease-out',
  /** Standard UI transitions */
  normal: '200ms ease-out',
  /** Slower, more prominent */
  slow: '300ms ease-out',
  /** Spring-like feel */
  spring: '400ms cubic-bezier(0.34, 1.56, 0.64, 1)',
} as const;

// ============================================================================
// CSS VARIABLE MAPPING - For Tailwind integration
// ============================================================================

export const cssVariables = `
  /* CelesteOS Maritime Design Tokens */

  /* Radius */
  --radius-container: ${radius.container};
  --radius-card: ${radius.card};
  --radius-button: ${radius.button};
  --radius-input: ${radius.input};
  --radius-badge: ${radius.badge};
  --radius-small: ${radius.small};

  /* Brand Colors */
  --color-bg-dark: ${colors.background.dark};
  --color-bg-light: ${colors.background.light};
  --color-accent: ${colors.accent.DEFAULT};
  --color-accent-hover: ${colors.accent.hover};
  --color-warning: ${colors.warning.DEFAULT};
  --color-success: ${colors.success.DEFAULT};

  /* Text Colors */
  --color-text-secondary: ${colors.text.secondary};

  /* Shadows */
  --shadow-xs: ${shadows.xs};
  --shadow-sm: ${shadows.sm};
  --shadow-md: ${shadows.md};
  --shadow-lg: ${shadows.lg};
  --shadow-xl: ${shadows.xl};

  /* Transitions */
  --transition-fast: ${transitions.fast};
  --transition-normal: ${transitions.normal};
  --transition-slow: ${transitions.slow};
`;

// ============================================================================
// UTILITY CLASSES (Tailwind-compatible)
// ============================================================================

export const utilityClasses = {
  // Card styling - maritime palette
  card: 'bg-[#EFEFF1] dark:bg-[#121212] rounded-[12px] border border-[#C8C8CA] dark:border-[#2A2A2A] shadow-sm',

  // Button base
  buttonBase: 'inline-flex items-center justify-center rounded-[8px] font-medium transition-all duration-150',

  // Button accent - maritime teal
  buttonAccent: 'bg-[#3A7C9D] text-[#EFEFF1] hover:bg-[#327189]',

  // Button default - transparent
  buttonDefault: 'bg-transparent border border-[#2A2A2A] text-[#8A9196] hover:text-[#DADDE0] hover:bg-white/5',

  // Input base - maritime palette
  inputBase: 'w-full rounded-[8px] border border-[#C8C8CA] dark:border-[#2A2A2A] bg-[#EFEFF1] dark:bg-[#0A0A0A] px-3 py-2 text-[15px] transition-colors focus:outline-none focus:ring-2 focus:ring-[#3A7C9D]/30 focus:border-[#3A7C9D]',

  // Badge (NOT pill shaped)
  badge: 'inline-flex items-center px-2 py-0.5 rounded-[6px] text-[12px] font-medium',

  // Status indicator dot
  statusDot: 'w-2 h-2 rounded-full',
} as const;
