/**
 * CelesteOS Shadow & Elevation System
 * Source: branding/UX/visual-tokens.md
 *
 * Shadows serve hierarchy and depth, never decoration.
 * "Emphasis shadows" are explicitly forbidden.
 */

// =============================================================================
// ELEVATION LEVELS
// =============================================================================

export const shadow = {
  // No shadow - flat elements
  none: 'none',

  // Subtle - slight lift for cards
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',

  // Default - standard elevated surfaces
  md: '0 2px 4px rgba(0, 0, 0, 0.04), 0 4px 8px rgba(0, 0, 0, 0.06)',

  // Large - dropdowns, popovers
  lg: '0 4px 8px rgba(0, 0, 0, 0.04), 0 8px 16px rgba(0, 0, 0, 0.08)',

  // XL - modals, overlays
  xl: '0 8px 16px rgba(0, 0, 0, 0.08), 0 24px 48px rgba(0, 0, 0, 0.16)',

  // Spotlight panel - signature glass effect
  spotlight: `
    0 0 0 0.5px rgba(0, 0, 0, 0.06),
    0 2px 4px rgba(0, 0, 0, 0.04),
    0 8px 16px rgba(0, 0, 0, 0.08),
    0 24px 48px rgba(0, 0, 0, 0.16)
  `.replace(/\s+/g, ' ').trim(),
} as const;

// =============================================================================
// BACKDROP BLUR
// =============================================================================

export const blur = {
  none: 'blur(0)',
  sm: 'blur(4px)',
  md: 'blur(8px)',
  lg: 'blur(16px)',
  xl: 'blur(24px)',

  // Spotlight glass effect
  spotlight: 'blur(72px) saturate(210%)',

  // Modal backdrop
  modal: 'blur(8px)',
} as const;

// =============================================================================
// OVERLAY OPACITY
// =============================================================================

export const overlay = {
  // Light overlays (hover states)
  light: 'rgba(255, 255, 255, 0.05)',
  lightHover: 'rgba(255, 255, 255, 0.10)',

  // Dark overlays (modals, dimming)
  dark: 'rgba(0, 0, 0, 0.50)',
  darkStrong: 'rgba(0, 0, 0, 0.80)', // Commitment overlay per spec

  // Selection highlight
  selection: 'rgba(10, 132, 255, 0.10)',
} as const;

// =============================================================================
// GLASS EFFECTS
// =============================================================================

export const glass = {
  // Spotlight panel glass
  spotlight: {
    background: 'rgba(28, 28, 30, 0.85)',
    backdropFilter: blur.spotlight,
    border: '0.5px solid rgba(255, 255, 255, 0.1)',
  },

  // Dropdown glass
  dropdown: {
    background: 'rgba(44, 44, 46, 0.95)',
    backdropFilter: blur.lg,
    border: '1px solid rgba(61, 61, 63, 0.5)',
  },

  // Card glass (subtle)
  card: {
    background: 'rgba(44, 44, 46, 0.8)',
    backdropFilter: blur.md,
    border: '1px solid rgba(61, 61, 63, 0.3)',
  },
} as const;

// =============================================================================
// CSS CUSTOM PROPERTIES
// =============================================================================

export const cssVars = {
  '--shadow-none': shadow.none,
  '--shadow-sm': shadow.sm,
  '--shadow-md': shadow.md,
  '--shadow-lg': shadow.lg,
  '--shadow-xl': shadow.xl,
  '--shadow-spotlight': shadow.spotlight,

  '--blur-sm': blur.sm,
  '--blur-md': blur.md,
  '--blur-lg': blur.lg,
  '--blur-spotlight': blur.spotlight,

  '--overlay-light': overlay.light,
  '--overlay-dark': overlay.dark,
  '--overlay-commitment': overlay.darkStrong,
} as const;
