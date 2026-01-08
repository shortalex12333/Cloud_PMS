/**
 * CelesteOS Motion & Animation System
 * Source: branding/UX/visual-tokens.md, branding/Brand/Brand Guidelines.md
 *
 * Motion is allowed ONLY to show:
 * - Progress
 * - Transition
 * - Commitment
 *
 * NEVER for:
 * - Personality
 * - Delight
 * - "Smoothness" for its own sake
 *
 * Logo animation: only subtle fade-in
 * FORBIDDEN: pulse, spin, morph, loop effects
 */

// =============================================================================
// DURATIONS
// =============================================================================

export const duration = {
  // Instant - immediate feedback
  instant: '0ms',

  // Fast - micro-interactions, hover states
  fast: '100ms',

  // Normal - standard transitions
  normal: '200ms',

  // Slow - significant state changes
  slow: '300ms',

  // Deliberate - commitment actions (intentionally slow)
  deliberate: '400ms',

  // Placeholder rotation
  placeholder: '3000ms',
} as const;

// =============================================================================
// EASING FUNCTIONS
// =============================================================================

export const easing = {
  // Default - smooth deceleration
  default: 'cubic-bezier(0.25, 0.1, 0.25, 1)',

  // Ease out - elements coming to rest
  out: 'cubic-bezier(0, 0, 0.2, 1)',

  // Ease in - elements starting motion
  in: 'cubic-bezier(0.4, 0, 1, 1)',

  // Ease in-out - symmetric motion
  inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',

  // Linear - progress indicators only
  linear: 'linear',
} as const;

// =============================================================================
// TRANSITION PRESETS
// =============================================================================

export const transition = {
  // None - no transition
  none: 'none',

  // Colors - hover states
  colors: `color ${duration.fast} ${easing.default}, background-color ${duration.fast} ${easing.default}`,

  // Opacity - fade in/out
  opacity: `opacity ${duration.normal} ${easing.out}`,

  // Transform - position/scale changes
  transform: `transform ${duration.normal} ${easing.out}`,

  // All - general purpose (use sparingly)
  all: `all ${duration.normal} ${easing.default}`,

  // Placeholder slide - search bar animation
  placeholder: `all ${duration.deliberate} ${easing.out}`,
} as const;

// =============================================================================
// KEYFRAME ANIMATIONS (Minimal set)
// =============================================================================

export const keyframes = {
  // Fade in - for initial load, modals
  fadeIn: {
    from: { opacity: '0' },
    to: { opacity: '1' },
  },

  // Slide up fade - for placeholder text
  slideUpFade: {
    from: { opacity: '1', transform: 'translateY(0)' },
    to: { opacity: '0', transform: 'translateY(-12px)' },
  },

  // Spotlight entrance
  spotlightIn: {
    from: { opacity: '0', transform: 'scale(0.98)' },
    to: { opacity: '1', transform: 'scale(1)' },
  },
} as const;

// =============================================================================
// ANIMATION PRESETS
// =============================================================================

export const animation = {
  // None
  none: 'none',

  // Fade in
  fadeIn: `fadeIn ${duration.normal} ${easing.out} forwards`,

  // Spotlight panel entrance
  spotlightIn: `spotlightIn ${duration.slow} ${easing.out} forwards`,

  // Placeholder text rotation
  placeholderSlide: `slideUpFade ${duration.deliberate} ${easing.out}`,
} as const;

// =============================================================================
// FORBIDDEN ANIMATIONS (Reference for code review)
// =============================================================================

export const FORBIDDEN_ANIMATIONS = [
  'spin',
  'pulse',
  'bounce',
  'ping',
  'shake',
  'wiggle',
  'flash',
  'rubberBand',
  'jello',
  'heartBeat',
  'tada',
  'swing',
  'wobble',
  // Any loop animation
  // Any animation with infinite duration
  // Any "delightful" micro-animations
] as const;

// =============================================================================
// CSS CUSTOM PROPERTIES
// =============================================================================

export const cssVars = {
  '--duration-instant': duration.instant,
  '--duration-fast': duration.fast,
  '--duration-normal': duration.normal,
  '--duration-slow': duration.slow,
  '--duration-deliberate': duration.deliberate,

  '--ease-default': easing.default,
  '--ease-out': easing.out,
  '--ease-in': easing.in,
  '--ease-in-out': easing.inOut,

  '--transition-colors': transition.colors,
  '--transition-opacity': transition.opacity,
  '--transition-transform': transition.transform,
} as const;
