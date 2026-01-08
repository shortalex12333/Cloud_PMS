/**
 * CelesteOS Typography System
 * Source: branding/Brand/Brand Guidelines.md
 *
 * Approved typefaces:
 * - Eloquia Display (headlines only)
 * - Eloquia Text (body, UI, tables)
 *
 * Requirements:
 * - Modern but timeless
 * - Technical yet calm
 * - Readable under fatigue
 * - No playful fonts or "tech mono" aesthetics
 * - UI prioritizes legibility over style
 */

// =============================================================================
// FONT FAMILIES
// =============================================================================

export const fontFamily = {
  // Primary: Eloquia with system fallbacks
  // Note: If Eloquia not available, falls back to SF Pro (Apple) then system
  display: [
    'Eloquia Display',
    '-apple-system',
    'BlinkMacSystemFont',
    'SF Pro Display',
    'Segoe UI',
    'Roboto',
    'Helvetica Neue',
    'sans-serif',
  ].join(', '),

  body: [
    'Eloquia Text',
    '-apple-system',
    'BlinkMacSystemFont',
    'SF Pro Text',
    'Segoe UI',
    'Roboto',
    'Helvetica Neue',
    'sans-serif',
  ].join(', '),

  // Mono for diffs, code, technical data
  mono: [
    'SF Mono',
    'Monaco',
    'Consolas',
    'Liberation Mono',
    'Courier New',
    'monospace',
  ].join(', '),
} as const;

// =============================================================================
// FONT SIZES
// =============================================================================

export const fontSize = {
  // UI Scale (rem-based for accessibility)
  xs: '0.6875rem',    // 11px - Records, meta
  sm: '0.75rem',      // 12px - Entity lines, status
  base: '0.8125rem',  // 13px - Body text, actions
  md: '0.875rem',     // 14px - Card headers
  lg: '0.9375rem',    // 15px - Emphasis
  xl: '1.0625rem',    // 17px - Search input
  '2xl': '1.3125rem', // 21px - Page titles (rare)
} as const;

// =============================================================================
// FONT WEIGHTS
// =============================================================================

export const fontWeight = {
  normal: '400',
  medium: '500',
  semibold: '600',
  // Note: Bold (700) intentionally omitted - restraint in emphasis
} as const;

// =============================================================================
// LINE HEIGHTS
// =============================================================================

export const lineHeight = {
  tight: '1.2',
  snug: '1.35',
  normal: '1.5',
  relaxed: '1.625',
} as const;

// =============================================================================
// LETTER SPACING
// =============================================================================

export const letterSpacing = {
  tighter: '-0.02em',
  tight: '-0.01em',
  normal: '0',
  wide: '0.01em',
} as const;

// =============================================================================
// TEXT STYLES (Composite tokens)
// =============================================================================

export const textStyles = {
  // Headlines (Eloquia Display)
  headline: {
    fontFamily: fontFamily.display,
    fontSize: fontSize['2xl'],
    fontWeight: fontWeight.semibold,
    lineHeight: lineHeight.tight,
    letterSpacing: letterSpacing.tight,
  },

  // Card headers
  cardHeader: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.md,
    fontWeight: fontWeight.medium,
    lineHeight: lineHeight.tight,
    letterSpacing: letterSpacing.tight,
  },

  // Body text
  body: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.base,
    fontWeight: fontWeight.normal,
    lineHeight: lineHeight.relaxed,
    letterSpacing: letterSpacing.tight,
  },

  // Search input
  searchInput: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xl,
    fontWeight: fontWeight.normal,
    lineHeight: lineHeight.normal,
    letterSpacing: letterSpacing.tight,
  },

  // Actions (READ)
  action: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.base,
    fontWeight: fontWeight.normal,
    lineHeight: lineHeight.normal,
    letterSpacing: letterSpacing.normal,
  },

  // Status/Entity lines
  status: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: fontWeight.normal,
    lineHeight: lineHeight.normal,
    letterSpacing: letterSpacing.normal,
  },

  // Records/Meta
  record: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: fontWeight.normal,
    lineHeight: lineHeight.snug,
    letterSpacing: letterSpacing.normal,
  },

  // Diff/Technical
  diff: {
    fontFamily: fontFamily.mono,
    fontSize: fontSize.md,
    fontWeight: fontWeight.normal,
    lineHeight: lineHeight.normal,
    letterSpacing: letterSpacing.normal,
  },
} as const;

// =============================================================================
// CSS CUSTOM PROPERTIES
// =============================================================================

export const cssVars = {
  '--font-display': fontFamily.display,
  '--font-body': fontFamily.body,
  '--font-mono': fontFamily.mono,

  '--text-xs': fontSize.xs,
  '--text-sm': fontSize.sm,
  '--text-base': fontSize.base,
  '--text-md': fontSize.md,
  '--text-lg': fontSize.lg,
  '--text-xl': fontSize.xl,
  '--text-2xl': fontSize['2xl'],
} as const;
