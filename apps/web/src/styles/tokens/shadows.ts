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
  lightHover: 'rgba(255, 255, 255, 0.08)',

  // Dark overlays (modals, dimming)
  dark: 'rgba(10, 10, 10, 0.50)',      // #0A0A0A based
  darkStrong: 'rgba(10, 10, 10, 0.85)', // Commitment overlay per spec

  // Selection highlight - maritime teal
  selection: 'rgba(58, 124, 157, 0.12)',  // #3A7C9D
} as const;

// =============================================================================
// GLASS EFFECTS
// =============================================================================

export const glass = {
  // Spotlight panel glass - dark mode (primary)
  spotlight: {
    background: 'rgba(10, 10, 10, 0.94)',  // #0A0A0A
    backdropFilter: blur.spotlight,
    border: '0.5px solid rgba(255, 255, 255, 0.06)',
  },

  // Spotlight panel glass - light mode
  spotlightLight: {
    background: 'rgba(239, 239, 241, 0.92)',  // #EFEFF1
    backdropFilter: blur.spotlight,
    border: '0.5px solid rgba(0, 0, 0, 0.06)',
  },

  // Dropdown glass
  dropdown: {
    background: 'rgba(18, 18, 18, 0.95)',  // #121212
    backdropFilter: blur.lg,
    border: '1px solid rgba(42, 42, 42, 0.5)',  // #2A2A2A
  },

  // Card glass (subtle)
  card: {
    background: 'rgba(18, 18, 18, 0.8)',  // #121212
    backdropFilter: blur.md,
    border: '1px solid rgba(42, 42, 42, 0.3)',  // #2A2A2A
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
