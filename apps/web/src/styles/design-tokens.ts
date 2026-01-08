/**
 * CelesteOS Design Tokens
 * Apple-inspired design system for premium UX
 *
 * Principles:
 * - Precision over decoration
 * - Subtle over saturated
 * - Consistency over variety
 * - Typography as primary hierarchy
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
// COLORS - Apple-inspired palette (muted, sophisticated)
// ============================================================================

export const colors = {
  // System colors (less saturated than default Tailwind)
  blue: {
    DEFAULT: '#007AFF',
    light: '#E8F4FF',
    dark: '#0A84FF',
  },
  green: {
    DEFAULT: '#34C759',
    light: '#E8FAF0',
    dark: '#30D158',
  },
  orange: {
    DEFAULT: '#FF9500',
    light: '#FFF4E5',
    dark: '#FF9F0A',
  },
  red: {
    DEFAULT: '#FF3B30',
    light: '#FFF0EF',
    dark: '#FF453A',
  },
  yellow: {
    DEFAULT: '#FFCC00',
    light: '#FFFBE5',
    dark: '#FFD60A',
  },
  gray: {
    50: '#F9FAFB',
    100: '#F2F2F7',
    200: '#E5E5EA',
    300: '#D1D1D6',
    400: '#AEAEB2',
    500: '#8E8E93',
    600: '#636366',
    700: '#48484A',
    800: '#3A3A3C',
    900: '#1C1C1E',
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
  /* Apple-inspired CelesteOS Design Tokens */

  /* Radius */
  --radius-container: ${radius.container};
  --radius-card: ${radius.card};
  --radius-button: ${radius.button};
  --radius-input: ${radius.input};
  --radius-badge: ${radius.badge};
  --radius-small: ${radius.small};

  /* System Colors */
  --color-blue: ${colors.blue.DEFAULT};
  --color-blue-light: ${colors.blue.light};
  --color-green: ${colors.green.DEFAULT};
  --color-green-light: ${colors.green.light};
  --color-orange: ${colors.orange.DEFAULT};
  --color-orange-light: ${colors.orange.light};
  --color-red: ${colors.red.DEFAULT};
  --color-red-light: ${colors.red.light};

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
  // Card styling
  card: 'bg-white dark:bg-gray-900 rounded-[12px] border border-gray-200/60 dark:border-gray-700/60 shadow-sm',

  // Button base
  buttonBase: 'inline-flex items-center justify-center rounded-[8px] font-medium transition-all duration-150',

  // Input base
  inputBase: 'w-full rounded-[8px] border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-[15px] transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500',

  // Badge (NOT pill shaped)
  badge: 'inline-flex items-center px-2 py-0.5 rounded-[6px] text-[12px] font-medium',

  // Status indicator dot
  statusDot: 'w-2 h-2 rounded-full',
} as const;
