/**
 * CelesteOS Design Tokens
 * Barrel export for all token modules
 *
 * Source: BRANDING_V3
 * These tokens implement the official maritime brand specification.
 * "Colour is a signal of state, not personality."
 */

// Color system
export {
  whites,
  blacks,
  grays,
  accent,
  blue,
  gradient,
  restricted,
  semantic,
  roleColors,
  button,
  cssVars as colorCssVars,
} from './colors';

// Typography system
export {
  fontFamily,
  fontSize,
  fontWeight,
  lineHeight,
  letterSpacing,
  textStyles,
  cssVars as typographyCssVars,
} from './typography';

// Spacing system
export {
  spacing,
  componentSpacing,
  layout,
  iconSize,
  radius,
  cssVars as spacingCssVars,
} from './spacing';

// Shadow & elevation system
export {
  shadow,
  blur,
  overlay,
  glass,
  cssVars as shadowCssVars,
} from './shadows';

// Motion & animation system
export {
  duration,
  easing,
  transition,
  keyframes,
  animation,
  FORBIDDEN_ANIMATIONS,
  cssVars as motionCssVars,
} from './motion';

// Forbidden elements (for code review reference)
export * from './forbidden';
export {
  FORBIDDEN_ELEMENTS,
  FORBIDDEN_PHRASES,
  FORBIDDEN_PATTERNS,
  FORBIDDEN_ICONS,
  FORBIDDEN_ANIMATIONS as FORBIDDEN_ANIMATION_NAMES,
  FORBIDDEN_COLOR_USAGE,
  isTextForbidden,
  containsForbiddenEmoji,
} from './forbidden';
