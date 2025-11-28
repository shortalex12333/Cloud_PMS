/**
 * CelesteOS Design System
 * Apple Spotlight + macOS Control Center Quality
 *
 * Version: 2.0
 * Last Updated: 2025-01-28
 */

// ============================================================================
// SPACING SYSTEM (8px base grid)
// ============================================================================

export const spacing = {
  px: '1px',
  0: '0',
  0.5: '2px',
  1: '4px',
  1.5: '6px',
  2: '8px',
  2.5: '10px',
  3: '12px',
  3.5: '14px',
  4: '16px',
  5: '20px',
  6: '24px',
  7: '28px',
  8: '32px',
  9: '36px',
  10: '40px',
  11: '44px',
  12: '48px',
  14: '56px',
  16: '64px',
  20: '80px',
  24: '96px',
} as const;

// ============================================================================
// BORDER RADIUS
// ============================================================================

export const radius = {
  none: '0',
  sm: '4px',
  DEFAULT: '8px',
  md: '12px',
  lg: '16px',
  xl: '20px',
  '2xl': '24px',
  '3xl': '32px',
  full: '9999px',
  // Spotlight-specific
  searchBar: '14px',
  resultCard: '12px',
  resultItem: '10px',
  microaction: '8px',
  badge: '6px',
  module: '20px',
} as const;

// ============================================================================
// SHADOWS (Apple-quality depth)
// ============================================================================

export const shadows = {
  // Spotlight search bar shadow
  spotlight: {
    default: '0 8px 32px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08)',
    hover: '0 12px 40px rgba(0, 0, 0, 0.16), 0 4px 12px rgba(0, 0, 0, 0.10)',
    active: '0 4px 16px rgba(0, 0, 0, 0.10), 0 1px 4px rgba(0, 0, 0, 0.06)',
  },
  // Result cards
  card: {
    default: '0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
    hover: '0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
    selected: '0 0 0 2px rgba(59, 130, 246, 0.5), 0 4px 12px rgba(0, 0, 0, 0.08)',
  },
  // Dashboard modules
  module: {
    default: '0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)',
    hover: '0 8px 24px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04)',
    expanded: '0 12px 32px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.06)',
  },
  // Microaction buttons
  microaction: {
    default: '0 1px 2px rgba(0, 0, 0, 0.05)',
    hover: '0 2px 6px rgba(0, 0, 0, 0.10)',
    active: 'inset 0 1px 2px rgba(0, 0, 0, 0.08)',
  },
  // Elevated elements
  elevated: '0 16px 48px rgba(0, 0, 0, 0.12), 0 4px 16px rgba(0, 0, 0, 0.08)',
  // Inner shadows
  inner: 'inset 0 1px 2px rgba(0, 0, 0, 0.06)',
  innerLight: 'inset 0 1px 0 rgba(255, 255, 255, 0.08)',
} as const;

// ============================================================================
// BLUR EFFECTS (Glassmorphism)
// ============================================================================

export const blur = {
  none: '0',
  sm: '4px',
  DEFAULT: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
  '2xl': '40px',
  '3xl': '64px',
  // Spotlight-specific
  spotlight: '20px',
  module: '16px',
  overlay: '8px',
} as const;

// ============================================================================
// TYPOGRAPHY SCALE
// ============================================================================

export const typography = {
  // Font families
  fontFamily: {
    sans: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    display: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    mono: '"SF Mono", SFMono-Regular, ui-monospace, Menlo, Monaco, "Cascadia Code", monospace',
  },
  // Font sizes with line heights
  size: {
    xs: { fontSize: '11px', lineHeight: '14px' },
    sm: { fontSize: '13px', lineHeight: '18px' },
    base: { fontSize: '15px', lineHeight: '22px' },
    lg: { fontSize: '17px', lineHeight: '24px' },
    xl: { fontSize: '20px', lineHeight: '28px' },
    '2xl': { fontSize: '24px', lineHeight: '32px' },
    '3xl': { fontSize: '28px', lineHeight: '36px' },
    '4xl': { fontSize: '34px', lineHeight: '42px' },
  },
  // Font weights
  weight: {
    regular: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  // Letter spacing
  tracking: {
    tighter: '-0.02em',
    tight: '-0.01em',
    normal: '0',
    wide: '0.01em',
    wider: '0.02em',
    widest: '0.04em',
  },
} as const;

// ============================================================================
// COLOR SYSTEM
// ============================================================================

export const colors = {
  // Semantic colors
  text: {
    primary: 'var(--foreground)',
    secondary: 'hsl(var(--muted-foreground))',
    tertiary: 'hsl(var(--muted-foreground) / 0.7)',
    inverse: 'var(--background)',
  },
  background: {
    primary: 'hsl(var(--background))',
    secondary: 'hsl(var(--muted))',
    elevated: 'hsl(var(--card))',
    overlay: 'hsl(var(--background) / 0.8)',
  },
  // Status colors (yacht operations)
  status: {
    critical: {
      bg: 'rgba(239, 68, 68, 0.12)',
      border: 'rgba(239, 68, 68, 0.3)',
      text: '#DC2626',
      icon: '#EF4444',
    },
    warning: {
      bg: 'rgba(245, 158, 11, 0.12)',
      border: 'rgba(245, 158, 11, 0.3)',
      text: '#D97706',
      icon: '#F59E0B',
    },
    success: {
      bg: 'rgba(34, 197, 94, 0.12)',
      border: 'rgba(34, 197, 94, 0.3)',
      text: '#16A34A',
      icon: '#22C55E',
    },
    info: {
      bg: 'rgba(59, 130, 246, 0.12)',
      border: 'rgba(59, 130, 246, 0.3)',
      text: '#2563EB',
      icon: '#3B82F6',
    },
    neutral: {
      bg: 'rgba(107, 114, 128, 0.12)',
      border: 'rgba(107, 114, 128, 0.3)',
      text: '#4B5563',
      icon: '#6B7280',
    },
  },
  // Card type accent colors
  cardType: {
    fault: '#EF4444',
    work_order: '#3B82F6',
    equipment: '#8B5CF6',
    part: '#10B981',
    handover: '#F59E0B',
    document: '#6366F1',
    hor_table: '#EC4899',
    purchase: '#14B8A6',
    checklist: '#84CC16',
    worklist: '#F97316',
    fleet_summary: '#06B6D4',
    smart_summary: '#A855F7',
  },
  // Confidence bar colors
  confidence: {
    high: '#22C55E',    // 80-100%
    medium: '#F59E0B',  // 50-79%
    low: '#EF4444',     // 0-49%
    gradient: 'linear-gradient(90deg, #22C55E 0%, #84CC16 25%, #F59E0B 50%, #F97316 75%, #EF4444 100%)',
  },
} as const;

// ============================================================================
// ANIMATION SPECIFICATIONS
// ============================================================================

export const animation = {
  // Durations
  duration: {
    instant: '50ms',
    fast: '100ms',
    normal: '200ms',
    slow: '300ms',
    slower: '400ms',
    slowest: '500ms',
  },
  // Easing curves (Apple-style)
  easing: {
    default: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    // Apple-specific
    appleDefault: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
    appleSpring: 'cubic-bezier(0.23, 1, 0.32, 1)',
  },
  // Keyframe definitions
  keyframes: {
    fadeIn: {
      from: { opacity: 0 },
      to: { opacity: 1 },
    },
    fadeOut: {
      from: { opacity: 1 },
      to: { opacity: 0 },
    },
    slideUp: {
      from: { opacity: 0, transform: 'translateY(8px)' },
      to: { opacity: 1, transform: 'translateY(0)' },
    },
    slideDown: {
      from: { opacity: 0, transform: 'translateY(-8px)' },
      to: { opacity: 1, transform: 'translateY(0)' },
    },
    scaleIn: {
      from: { opacity: 0, transform: 'scale(0.95)' },
      to: { opacity: 1, transform: 'scale(1)' },
    },
    shimmer: {
      '0%': { backgroundPosition: '-200% 0' },
      '100%': { backgroundPosition: '200% 0' },
    },
    pulse: {
      '0%, 100%': { opacity: 1 },
      '50%': { opacity: 0.5 },
    },
    spin: {
      from: { transform: 'rotate(0deg)' },
      to: { transform: 'rotate(360deg)' },
    },
    progressBar: {
      '0%': { width: '0%', opacity: 0.3 },
      '50%': { width: '70%', opacity: 1 },
      '100%': { width: '100%', opacity: 0.3 },
    },
  },
} as const;

// ============================================================================
// COMPONENT SPECIFICATIONS
// ============================================================================

export const components = {
  // Spotlight Search Bar
  searchBar: {
    container: {
      width: '680px',
      maxWidth: '90vw',
      padding: '0',
    },
    input: {
      height: '56px',
      padding: '16px 48px 16px 52px',
      fontSize: '17px',
      fontWeight: '400',
      borderRadius: '14px',
      border: '1px solid hsl(var(--border))',
      background: 'hsl(var(--card) / 0.95)',
      backdropFilter: 'blur(20px)',
    },
    icon: {
      size: '20px',
      left: '18px',
      color: 'hsl(var(--muted-foreground))',
    },
    clearButton: {
      size: '28px',
      right: '14px',
      borderRadius: '6px',
    },
  },
  // Result list
  resultList: {
    container: {
      marginTop: '8px',
      maxHeight: '480px',
      borderRadius: '14px',
      overflow: 'hidden',
      background: 'hsl(var(--card) / 0.98)',
      backdropFilter: 'blur(20px)',
      border: '1px solid hsl(var(--border))',
    },
    header: {
      padding: '10px 16px 6px',
      fontSize: '11px',
      fontWeight: '600',
      textTransform: 'uppercase' as const,
      letterSpacing: '0.04em',
      color: 'hsl(var(--muted-foreground))',
    },
    divider: {
      height: '1px',
      margin: '4px 16px',
      background: 'hsl(var(--border))',
    },
  },
  // Result row
  resultRow: {
    container: {
      padding: '10px 16px',
      minHeight: '52px',
      gap: '12px',
    },
    icon: {
      size: '32px',
      borderRadius: '8px',
    },
    title: {
      fontSize: '15px',
      fontWeight: '500',
      lineHeight: '20px',
    },
    subtitle: {
      fontSize: '13px',
      fontWeight: '400',
      lineHeight: '18px',
      color: 'hsl(var(--muted-foreground))',
    },
    confidenceBar: {
      width: '40px',
      height: '4px',
      borderRadius: '2px',
    },
    microactions: {
      gap: '4px',
      maxVisible: 3,
    },
  },
  // Microaction button
  microaction: {
    size: {
      sm: { height: '24px', padding: '0 8px', fontSize: '11px', iconSize: '12px' },
      md: { height: '28px', padding: '0 10px', fontSize: '12px', iconSize: '14px' },
      lg: { height: '32px', padding: '0 12px', fontSize: '13px', iconSize: '16px' },
    },
    borderRadius: '6px',
    gap: '4px',
  },
  // Dashboard module
  module: {
    container: {
      borderRadius: '20px',
      padding: '16px',
      background: 'hsl(var(--card) / 0.95)',
      backdropFilter: 'blur(16px)',
      border: '1px solid hsl(var(--border))',
    },
    header: {
      marginBottom: '12px',
      fontSize: '13px',
      fontWeight: '600',
    },
    collapsed: {
      height: '64px',
    },
    expanded: {
      minHeight: '200px',
    },
  },
} as const;

// ============================================================================
// Z-INDEX LAYERS
// ============================================================================

export const zIndex = {
  base: 0,
  dropdown: 100,
  sticky: 200,
  fixed: 300,
  modalBackdrop: 400,
  modal: 500,
  popover: 600,
  tooltip: 700,
  spotlight: 800,
  toast: 900,
  max: 9999,
} as const;

// ============================================================================
// BREAKPOINTS
// ============================================================================

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// Export complete design system
export const designSystem = {
  spacing,
  radius,
  shadows,
  blur,
  typography,
  colors,
  animation,
  components,
  zIndex,
  breakpoints,
} as const;

export default designSystem;
